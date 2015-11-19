# proc: Simple interface to Linux process information.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: November 19, 2015
# URL: https://proc.readthedocs.org

"""
The :mod:`proc.notify` module implements a headless ``notify-send`` program.

The notify-send_ program can be used to send desktop notifications to the user
from the command line. It's great for use in otherwise non-interactive programs
to unobtrusively inform the user about something, for example I use it to show
a notification when a system backup is starting and when it has completed.

One problem is that notify-send needs access to a few environment variables
from the desktop session in order to deliver its message. The values of these
environment variables change every time a desktop session is started. This
complicates the use of notify-send from e.g. system daemons and `cron jobs`_
(say for an automated backup solution :-).

This module builds on top of the :mod:`proc.core` module as a trivial (but
already useful :-) example of how the `proc` package can be used to search
through the environments of all available processes. It looks for the variables
in :attr:`REQUIRED_VARIABLES` in the environments of all available processes
and uses the values it finds to run the notify-send program. Given super-user
privileges this should work fine out of the box on any Linux system with
notify-send installed, assuming only a single desktop session exists (multiple
concurrent desktop sessions are not supported).

.. _cron jobs: http://unix.stackexchange.com/q/111188
.. _notify-send: http://manpages.debian.org/cgi-bin/man.cgi?query=notify-send
"""

# Standard library modules.
import sys

# External dependencies.
import coloredlogs
from executor import execute

# Modules included in our package.
from proc.core import find_processes

REQUIRED_VARIABLES = 'DBUS_SESSION_BUS_ADDRESS', 'DISPLAY', 'XAUTHORITY'
"""The names of environment variables required by notify-send (a tuple of strings)."""


def main():
    """Command line interface for ``notify-send-headless``."""
    coloredlogs.install()
    execute('notify-send', *sys.argv[1:],
            environment=find_environment_variables(*REQUIRED_VARIABLES))


def find_environment_variables(*names):
    """
    Find the values of environment variables in use by other processes.

    :param names: The names of one or more environment variables (strings).
    :returns: A dictionary with environment variables that match the given
              names and have a nonempty value.
    """
    matches = {}
    for process in find_processes():
        for k, v in process.environ.items():
            if k in names and v:
                matches[k] = v
    return matches
