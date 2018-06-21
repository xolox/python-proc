# proc: Simple interface to Linux process information.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 21, 2018
# URL: https://proc.readthedocs.io

"""
The :mod:`proc.gpg` module provides a smart wrapper for `gpg-agent --daemon`_.

.. contents::
   :local:

Introduction to gpg-agent
=========================

The gpg-agent is used to keep secret keys unlocked in between multiple
invocations of the gpg_ command to avoid retyping the same password. It's
usually started from a script that initializes your graphical session, ensuring
that all processes from that point onward inherit the environment variable
``$GPG_AGENT_INFO``. This variable together with the command line option ``gpg
--use-agent`` enable the use of the gpg-agent daemon.

.. note:: This applies to GnuPG versions before 2.1, refer to the `What's new
          in GnuPG 2.1 <https://www.gnupg.org/faq/whats-new-in-2.1.html#autostart>`_
          page for details. In GnuPG 2.1 the use of ``$GPG_AGENT_INFO`` was
          removed because it proved too cumbersome for users :-).

Problem statement
=================

Making sure that ``$GPG_AGENT_INFO`` is always set correctly can be a hassle.
For example I frequently use SSH_ to connect between my personal laptop and work
laptop and the interactive shells spawned by the SSH daemon have no relation to
any graphical session so they don't have ``$GPG_AGENT_INFO`` set.

Of course I can just execute ``eval $(gpg-agent --daemon)`` in an interactive
session to spawn a gpg-agent on the spot, but that will remain running in the
background indefinitely after I close the interactive session, without any
simple means of reconnecting.

Initial solution
================

Somewhere in 2016 I developed a Python script that used :mod:`proc.core` to
search for ``$GPG_AGENT_INFO`` values in ``/proc`` so I could easily reconnect
to previously spawned gpg-agents. It mostly worked but it could pick the wrong
``$GPG_AGENT_INFO`` when references remained to a crashed or killed agent, so
eventually I added checks that ensured the UNIX socket and agent process still
existed.

After using this for a while I discovered that when I started a new gpg-agent
from an interactive shell spawned by the SSH daemon, I would lose all means of
connecting to the agent as soon as I logged out of the interactive shell, even
though the agent remained running :-).

Revised solution
================

After taking a step back I realized that the problem could be approached from a
completely different angle: Why not search for an existing ``gpg-agent``
process and infer the required ``$GPG_AGENT_INFO`` value by inspecting the
process using lsof_?

The revised solution has worked quite well for me and so I'm now publishing it
as the :mod:`proc.gpg` module which implements the command line program
``with-gpg-agent``.

Internal documentation of :mod:`proc.gpg`
=========================================

.. _gpg-agent --daemon: https://manpages.debian.org/cgi-bin/man.cgi?query=gpg-agent
.. _gpg: https://manpages.debian.org/cgi-bin/man.cgi?query=gpg
.. _lsof: https://manpages.debian.org/cgi-bin/man.cgi?query=lsof
.. _SSH: https://manpages.debian.org/cgi-bin/man.cgi?query=ssh
"""

# Standard library modules.
import functools
import getopt
import os
import stat
import sys

# External dependencies.
import coloredlogs
from executor import ExternalCommandFailed, execute, which
from humanfriendly import Spinner, Timer, parse_path
from humanfriendly.terminal import usage, warning
from verboselogs import VerboseLogger

# Modules included in our package.
from proc.core import find_processes

LAUNCH_TIMEOUT = 30
"""
The timeout for a newly launched GPG agent daemon to come online (a number).

This gives the maximum number of seconds to wait for a newly launched GPG agent
daemon to come online.
"""

NEW_STYLE_SOCKET = '~/.gnupg/S.gpg-agent'
"""The location of the GPG agent socket for GnuPG 2.1 and newer (a string)."""

# Initialize a logger.
logger = VerboseLogger(__name__)

# Inject our logger into all execute() calls.
execute = functools.partial(execute, logger=logger)

USAGE_TEXT = """
Usage: with-gpg-agent [OPTIONS] COMMAND

Run the given COMMAND with the environment variable(s) required by gpg to
connect to a gpg-agent daemon. If no gpg-agent daemon is running yet a
new one will be spawned in the background.

Supported options:

  -v, --verbose

    Make more noise (increase verbosity).

  -q, --quiet

    Make less noise (decrease verbosity).

  -h, --help

    Show this message and exit.
"""


def main():
    """Wrapper for :func:`with_gpg_agent()` that feeds it :data:`sys.argv`."""
    coloredlogs.install(syslog=True)
    with_gpg_agent(sys.argv[1:])


def with_gpg_agent(arguments):
    """Command line interface for the ``with-gpg-agent`` program."""
    command_line = parse_arguments(arguments)
    try:
        execute(*command_line, environment=get_gpg_variables())
    except ExternalCommandFailed as e:
        logger.error(e.error_message)
        sys.exit(1)


def parse_arguments(arguments):
    """
    Parse the command line arguments.

    :param arguments: A list of strings with command line options and/or arguments.
    :returns: A list of strings with the positional arguments.
    """
    try:
        options, arguments = getopt.gnu_getopt(arguments, 'vqh', [
            'verbose', 'quiet', 'help'
        ])
        for option, value in options:
            if option in ('-v', '--verbose'):
                coloredlogs.increase_verbosity()
            elif option in ('-q', '--quiet'):
                coloredlogs.decrease_verbosity()
            elif option in ('-h', '--help'):
                usage(USAGE_TEXT)
                sys.exit(0)
            else:
                assert False, "Unhandled option!"
        if not arguments:
            usage(USAGE_TEXT)
            sys.exit(0)
        return arguments
    except Exception as e:
        warning("Error: Failed to parse command line arguments! (%s)", e)
        sys.exit(1)


def enable_gpg_agent(**options):
    """
    Update :data:`os.environ` with the variables collected by :func:`get_gpg_variables()`.

    :param options: Optional keyword arguments for :func:`get_gpg_variables()`.
    """
    os.environ.update(get_gpg_variables(**options))


def get_gpg_variables(timeout=LAUNCH_TIMEOUT):
    """
    Prepare the environment variable(s) required by the gpg_ program.

    :param timeout: The timeout for a newly launched GPG agent daemon to
                    start (a number, defaults to :data:`LAUNCH_TIMEOUT`).
    :returns: A dictionary with environment variables.

    This function tries to figure out the correct values of two
    environment variables that are used by the gpg_ program:

    - ``$GPG_AGENT_INFO`` is generated using :func:`find_gpg_agent_info()`,
      spawning a new agent if :func:`find_gpg_agent_info()` initially returns
      :data:`None`.

    - ``$GPG_TTY`` is generated using `/usr/bin/tty`_.

    .. _/usr/bin/tty: https://manpages.debian.org/cgi-bin/man.cgi?query=tty
    """
    environment = {}
    # Try to figure out the correct value of $GPG_AGENT_INFO.
    logger.debug("Preparing $GPG_AGENT_INFO variable ..")
    if have_valid_agent_info():
        logger.debug("Using existing value of $GPG_AGENT_INFO ..")
        environment['GPG_AGENT_INFO'] = os.environ['GPG_AGENT_INFO']
    else:
        gpg_agent_info = find_gpg_agent_info()
        if not gpg_agent_info:
            # Start a new GPG agent daemon?
            if have_agent_program():
                logger.debug("No running GPG agent found, trying to spawn new one ..")
                gpg_agent_info = start_gpg_agent(timeout=timeout)
            else:
                logger.notice("Not using gpg-agent program (it's not installed).")
        if gpg_agent_info:
            environment['GPG_AGENT_INFO'] = gpg_agent_info
    # Try to figure out the correct value of $GPG_TTY.
    logger.debug("Preparing $GPG_TTY variable ..")
    gpg_tty = execute('tty', capture=True, check=False, shell=False, tty=True)
    if gpg_tty:
        environment['GPG_TTY'] = gpg_tty
    logger.debug("GPG environment: %s", environment)
    return environment


def find_gpg_agent_info():
    """
    Reconstruct ``$GPG_AGENT_INFO`` based on a running ``gpg-agent`` process.

    :returns: A string or :data:`None`.

    This function uses :func:`~proc.core.find_processes()` to search for
    ``gpg-agent`` processes and runs lsof_ to find out which UNIX socket is
    being used by the agent. Based on this information it reconstructs
    the expected value of ``$GPG_AGENT_INFO``.
    """
    logger.debug("Searching for running GPG agent ..")
    our_uid = os.getuid()
    for process in find_processes():
        if process.exe_name == 'gpg-agent':
            logger.debug("Found GPG agent with PID %i, checking user id .. ", process.pid)
            their_uid = process.user_ids.real if process.user_ids else 'unknown'
            if our_uid == their_uid:
                socket_file = None
                logger.debug("GPG agent user id matches ours! Looking for UNIX socket ..")
                fixed_socket = find_fixed_agent_socket()
                if validate_unix_socket(fixed_socket):
                    logger.debug("Found GnuPG >= 2.1 compatible socket: %s", fixed_socket)
                    socket_file = fixed_socket
                else:
                    logger.debug("Using `lsof' to find open UNIX sockets ..")
                    for filename in find_open_unix_sockets(process.pid):
                        logger.debug("UNIX domain socket reported by lsof: %s", filename)
                        if validate_unix_socket(filename):
                            socket_file = filename
                            break
                # We will now reconstruct $GPG_AGENT_INFO based on the
                # information that we've gathered. We should end up with
                # an expression like `/tmp/gpg-KE5ZZL/S.gpg-agent:2407:1'.
                if socket_file:
                    agent_info = ':'.join([socket_file, str(process.pid), '1'])
                    logger.debug("Reconstructed $GPG_AGENT_INFO: %s", agent_info)
                    return agent_info
            else:
                logger.debug("GPG agent user id (%s) doesn't match ours (%i), ignoring process %i.",
                             their_uid, our_uid, process.pid)


def find_fixed_agent_socket():
    """
    Search for a GPG agent UNIX socket in one of the "fixed locations".

    :returns: The pathname of the found socket file (a string) or :data:`None`.

    Two locations are searched, in the given order (the first that is found is
    returned):

    - Starting from GnuPG 2.1.13 the location ``/run/user/$UID/gnupg/S.gpg-agent``
      is used (only when the directory ``/run/user/$UID`` exists).

    - GnuPG 2.1 removed the ``$GPG_AGENT_INFO`` related code and switched to
      the fixed location ``~/.gnupg/S.gpg-agent``.
    """
    socket_on_tmpfs = '/run/user/%i/gnupg/S.gpg-agent' % os.getuid()
    for socket in (socket_on_tmpfs, parse_path(NEW_STYLE_SOCKET)):
        if os.path.exists(socket):
            return socket


def find_open_unix_sockets(pid):
    """
    Find the pathnames of any UNIX sockets held open by a process.

    :param pid: The process ID (a number).
    :returns: A generator of pathnames (strings).
    """
    # A quick lsof tutorial :-)
    #  -F enables output that is easy to parse,
    #  -p lists the open files of a specific PID,
    #  -a combines -p and -U using AND instead of OR,
    #  -U lists only UNIX domain socket files.
    output = execute('lsof', '-F', '-p', str(pid), '-a', '-U', capture=True, check=False, silent=True)
    for line in output.splitlines():
        if line and line[0] == 'n':
            filename = line[1:]
            if filename:
                yield filename


def have_agent_program():
    """
    Check whether the ``gpg-agent`` program is installed.

    :returns: :data:`True` when the ``gpg-agent`` program is available on the
               ``$PATH``, :data:`False` otherwise.
    """
    return bool(which('gpg-agent'))


def have_valid_agent_info():
    """
    Check if the existing ``$GPG_AGENT_INFO`` value is usable.

    :returns: :data:`True` if the existing ``$GPG_AGENT_INFO`` is valid,
              :data:`False` otherwise.

    This function parses the ``$GPG_AGENT_INFO`` environment
    variable and validates the resulting UNIX socket filename
    using :func:`validate_unix_socket()``.
    """
    components = os.environ.get('GPG_AGENT_INFO', '').split(':')
    return components and validate_unix_socket(components[0])


def validate_unix_socket(pathname):
    """
    Check whether a filename points to a writable UNIX socket.

    :param pathname: The pathname of the socket file (a string).
    :returns: :data:`True` if the socket exists and is writable,
              :data:`False` in all other cases.
    """
    try:
        metadata = os.stat(pathname)
        if stat.S_ISSOCK(metadata.st_mode):
            return os.access(pathname, os.W_OK)
    except Exception:
        pass
    return False


def start_gpg_agent(timeout=LAUNCH_TIMEOUT):
    """
    Start a new gpg-agent daemon in the background.

    :param timeout: The timeout for the newly launched GPG agent daemon to
                    start (a number, defaults to :data:`LAUNCH_TIMEOUT`).
    :returns: The return value of :func:`find_gpg_agent_info()`.
    """
    timer = Timer()
    logger.info("Starting a new GPG agent daemon ..")
    execute('gpg-agent', '--daemon', async=True, silent=True)
    with Spinner(timer=timer) as spinner:
        while timer.elapsed_time < LAUNCH_TIMEOUT:
            gpg_agent_info = find_gpg_agent_info()
            if gpg_agent_info:
                logger.debug("Waited %s for GPG agent daemon to start.", timer)
                return gpg_agent_info
            spinner.step(label="Waiting for GPG agent daemon")
            spinner.sleep()
    logger.warning("Failed to locate spawned GPG agent! (waited for %s)", timer)
