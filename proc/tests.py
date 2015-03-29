# Automated tests for the `proc' package.
#
# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: March 29, 2015
# URL: https://py2deb.readthedocs.org

"""
The :py:mod:`py2deb.tests` module contains the automated tests for `py2deb`.

The makefile in the py2deb git repository uses pytest_ to run the test suite
because of pytest's great error reporting. Nevertheless the test suite is
written to be compatible with the :py:mod:`unittest` module (part of Python's
standard library) so that the test suite can be run without additional external
dependencies.

.. _pytest: http://pytest.org/latest/goodpractises.html
"""

# Standard library modules.
import logging
import multiprocessing
import os
import random
import subprocess
import time
import unittest

# External dependencies.
import coloredlogs

# Modules included in our package.
from executor import which
from humanfriendly import parse_size, Timer
from pprint import pformat
from proc.core import find_processes, num_race_conditions, Process
from proc.cron import cron_graceful, wait_for_processes
from proc.tree import get_process_tree

# Initialize a logger.
logger = logging.getLogger(__name__)


def setUpModule():
    """
    Prepare the test suite.

    Sets up verbose logging to the terminal. When a test fails the logging
    output can help to perform a post-mortem analysis of the failure in
    question (even when its hard to reproduce locally). This is especially
    useful when debugging remote test failures, whether they happened on Travis
    CI or a user's local system.
    """
    # Initialize verbose logging to the terminal.
    coloredlogs.install()
    coloredlogs.increase_verbosity()


class ProcTestCase(unittest.TestCase):

    """
    :py:mod:`unittest` compatible container for the test suite of `proc`.
    """

    def test_process_from_path(self):
        """Test the :py:func:`proc.core.Process.from_path()` constructor."""
        process = Process.from_path('/proc/self')
        # The following tests verify properties based on information available
        # from the Python standard library.
        assert process.pid == os.getpid(), "Unexpected process ID!"
        assert process.ppid == os.getppid(), "Unexpected parent process ID!"
        assert process.pgrp == os.getpgrp(), "Unexpected process group ID!"
        # The following tests are based on common sense, here's hoping they
        # don't bite me in the ass later on :-).
        assert which(process.comm), "Process executable name non available on $PATH?!"
        assert process.state == 'R', "Unexpected process state!"
        assert process.runtime < 600, "Test process running for >= 10 minutes?!"
        assert process.rss > parse_size('10 MB'), "Resident set size (RSS) less than 10 MB?!"
        assert process.vsize > process.rss, "Virtual memory usage less than its resident set size (RSS)?!"
        assert executable(process.cmdline[0]) or which(process.cmdline[0]), \
            "First token in process command line isn't executable?!"
        assert executable(process.exe), "Process executable pathname (based on /proc/[pid]/stat) invalid?!"
        assert executable(process.exe_path), "Process executable pathname (fall back option) invalid?!"
        assert which(process.exe_name), "Process executable base name (fall back option) not available on $PATH?!"
        assert process.is_alive, "The current process is not running?! :-P"
        # Python's standard library doesn't seem to expose process session IDs
        # so all I can test reliably is that the session ID is an integer...
        assert isinstance(process.session, int), "Process session ID not available!"

    def test_find_processes(self):
        """Test the :py:func:`proc.core.find_processes()` function."""
        processes = dict((p.pid, p) for p in find_processes())
        assert 1 in processes, "init process not found in output of find_processes()!"
        assert processes[1].comm == 'init', "init isn't called init?!"
        assert os.getpid() in processes, "Current process not found in output of find_processes()!"

    def test_is_alive(self):
        """Test the :py:func:`proc.core.Process.is_alive` property."""
        # Spawn a child that will live for a minute.
        child = subprocess.Popen(['sleep', '60'])
        try:
            # Construct a process object for the child.
            process = Process.from_pid(child.pid)
            # Make sure the process object agrees the child is alive.
            assert process.is_alive, "Child died before Process.is_alive was called?!"
        finally:
            # Kill the child process.
            child.terminate()
        # Give the process a moment to terminate (significantly less time then
        # the process is normally expected to run, otherwise there's no point
        # in the test below).
        wait_for_termination(process, timeout=10)
        # Make sure the process object agrees the child is dead.
        assert not process.is_alive, "Child is still alive even though we killed it?!"

    def test_signals(self):
        """Test the sending of ``SIGSTOP``, ``SIGCONT`` and ``SIGTERM`` signals."""
        # Spawn a child that will live for a minute.
        child = subprocess.Popen(['sleep', '60'])
        try:
            # Construct a process object for the child.
            process = Process.from_pid(child.pid)
            # Suspend the execution of the child process using SIGSTOP.
            process.stop()
            # Test that the child process doesn't respond to SIGTERM once suspended.
            process.terminate()
            assert process.is_alive, "Process responded to SIGTERM even though it was suspended?!"
            # Resume the execution of the child process using SIGCONT.
            process.cont()
            # Test that the child process responds to SIGTERM again after having been resumed.
            process.terminate()
            # Give the process a moment to terminate (significantly less time then
            # the process is normally expected to run, otherwise there's no point
            # in the test below).
            wait_for_termination(process, timeout=10)
            assert not process.is_alive, "Process didn't respond to SIGTERM even though it was resumed?!"
        finally:
            # Kill the child process.
            child.terminate()

    def test_killing(self):
        """Test the sending of ``SIGKILL`` signals."""
        # Spawn a child that will live for a minute.
        child = subprocess.Popen(['sleep', '60'])
        try:
            # Construct a process object for the child.
            process = Process.from_pid(child.pid)
            # Forcefully kill the child process using SIGKILL.
            process.kill()
            # Give the process a moment to terminate (significantly less time then
            # the process is normally expected to run, otherwise there's no point
            # in the test below).
            wait_for_termination(process, timeout=10)
            # Normally the `sleep 60' process would have been alive for +/- 60
            # seconds but due to our SIGKILL it should terminate much earlier.
            # If it's still running after the above loop of max +/- 10 seconds
            # then the SIGKILL is clearly not working as expected (or we're
            # running on a _really_ slow system).
            assert not process.is_alive, "Process still running despite SIGKILL?!"
        finally:
            # Kill the child process.
            child.terminate()

    def test_exe_path_fallback(self):
        """Test the fall back method of :py:attr:`proc.core.Process.exe_path`."""
        candidates = [p for p in find_processes() if p.exe_path and not p.exe]
        logger.debug("Candidates for Process.exe_path fall back test:\n%s", pformat(candidates))
        if not candidates:
            self.skipTest("No processes available on which Process.exe_path fall back can be tested!")
        else:
            assert executable(candidates[0].exe_path), \
                "Fall back method of Process.exe_path reported invalid executable pathname!"

    def test_exe_name_fallback(self):
        """Test the fall back method of :py:attr:`proc.core.Process.exe_name`."""
        candidates = [p for p in find_processes() if p.exe_name and not p.exe_path]
        logger.debug("Candidates for Process.exe_name fall back test:\n %s", pformat(candidates))
        if not candidates:
            self.skipTest("No processes available on which Process.exe_name fall back can be tested!")
        else:
            assert any(which(p.exe_name) for p in candidates), \
                "Fall back method of Process.exe_name reported executable base name not available on $PATH?!"

    def test_tree_construction(self):
        """Test the functionality of the :py:mod:`proc.tree` module."""
        # Spawn a child and grandchild (because of shell=True) that will live for a minute.
        child = subprocess.Popen(['sleep 60'], shell=True)
        try:
            # Construct a process tree.
            init = get_process_tree()
            # Locate our own process in the tree.
            self = init.find(pid=os.getpid(), recursive=True)
            # Verify that the child is visible in the process tree.
            assert child.pid in [c.pid for c in self.children], \
                "Child process not visible in process tree reported by get_process_tree()!"
            # Verify that the grandchild is visible in the process tree.
            assert any(gc.exe_name == 'sleep' for gc in self.grandchildren), \
                "Grandchild process not visible in process tree reported by get_process_tree()!"
        finally:
            # Make sure we always kill our child.
            child.terminate()

    def test_wait_for_processes(self):
        """Test the :py:func:`proc.cron.wait_for_processes()` function."""
        children = [subprocess.Popen(['sleep', str(int(5 + random.random() * 5))]) for i in range(5)]
        wait_for_processes([Process.from_pid(c.pid) for c in children])
        assert sum(c.poll() is None for c in children) == 0, \
            "wait_for_processes() returned before all processes ended!"

    def test_cron_graceful_dry_run(self):
        """Test a dry run of the ``cron-graceful`` program."""
        # Test that `cron-graceful -h' / `cron-graceful --help' works.
        self.assertRaises(SystemExit, cron_graceful, ['-h'])
        self.assertRaises(SystemExit, cron_graceful, ['--help'])
        # Test that invalid command line options raise an error.
        self.assertRaises(SystemExit, cron_graceful, ['--whatever'])
        # Test that the other command line options are accepted and test that a
        # dry run of cron-graceful runs successfully.
        cron_graceful(['-q', '--quiet', '-v', '--verbose', '-n', '--dry-run'])

    def test_race_conditions(self, timeout=60):
        """
        Test the handling of race conditions in :py:mod:`proc.core`.

        Scanning ``/proc`` is inherently vulnerable to race conditions, for
        example:

        1. A listing of available processes in ``/proc`` confirms a process
           exists, but by the time ``/proc/[pid]/stat`` is read the process has
           ended and ``/proc/[pid]`` no longer exists.

        2. A :py:class:`proc.core.Process` object is constructed from the
           information available in ``/proc/[pid]/stat``, but by the time
           ``/proc/[pid]/cmdline`` is read the process has ended and
           ``/proc/[pid]`` no longer exists.

        This test intentionally creates race conditions in the reading of
        ``/proc/[pid]/stat`` and ``/proc/[pid]/cmdline`` files, to verify that
        the :py:mod:`proc.core` module never breaks on a race condition.

        It works by using the :py:mod:`multiprocessing` module to quickly spawn
        and reclaim subprocesses while at the same time scanning through
        ``/proc`` continuously. The test times out after 60 seconds but in all
        of the runs I've tried so far it never needs more than 10 seconds to
        encounter a handful of race conditions
        """
        # Copy the race condition counters so we can verify all counters have
        # increased before we consider this test to have passed.
        logger.info("Testing handling of race conditions, please be patient :-) ..")
        timer = Timer()
        at_start = dict(num_race_conditions)
        shutdown_event = multiprocessing.Event()
        manager = multiprocessing.Process(target=race_condition_manager,
                                          args=(shutdown_event,))
        manager.start()
        try:
            while True:
                # Scan the process tree with the knowledge that subprocesses could
                # be disappearing any second now :-).
                for process in find_processes():
                    if process.ppid == manager.pid:
                        # Force a time window between when /proc/[pid]/stat was
                        # read and when /proc/[pid]/cmdline will be read.
                        time.sleep(0.1)
                        # Read /proc/[pid]/cmdline even though it may no longer exist.
                        assert isinstance(process.cmdline, list)
                # Check whether race conditions have been handled.
                if all(num_race_conditions[k] > at_start[k] for k in at_start):
                    # The test has passed: We were able to simulate at least
                    # one race condition of every type within the timeout.
                    logger.info("Successfully finished race condition test in %s.", timer)
                    return
                assert timer.elapsed_time < timeout, "Timeout elapsed before race conditions could be simulated!"
                # Don't burn CPU cycles too much.
                time.sleep(0.1)
        finally:
            shutdown_event.set()
            manager.join()


def executable(pathname):
    """Check whether a pathname is executable."""
    return pathname and os.access(pathname, os.X_OK)


def wait_for_termination(process, timeout):
    """
    Wait for a process to terminate or the timeout to expire.

    Several tests involve ``SIGTERM`` and/or ``SIGKILL`` signals and verify
    that the process terminates as expected, however process termination is
    never actually instantaneous. In order to create a robust test suite we
    need to wait for processes to terminate (with a timeout).
    """
    timer = Timer()
    while process.is_alive and timer.elapsed_time < timeout:
        time.sleep(0.1)


def race_condition_manager(shutdown_event):
    """Quickly spawn and reclaim subprocesses to cause race conditions."""
    num_spawned = 0
    subprocesses = []
    while not shutdown_event.is_set():
        # Spawn some new subprocesses.
        while len(subprocesses) < 25:
            helper = RaceConditionHelper()
            subprocesses.append(helper)
            helper.start()
            num_spawned += 1
        # Reclaim dead subprocesses.
        for helper in list(subprocesses):
            if not helper.is_alive():
                helper.join()
                subprocesses.remove(helper)
        # Don't burn unnecessary CPU cycles.
        time.sleep(0.1)
    logger.info("Shutdown event was set, terminating %i remaining helpers ..", len(subprocesses))
    for helper in subprocesses:
        helper.terminate()
        helper.join()
    logger.info("Spawned a total of %i subprocesses.", num_spawned)


class RaceConditionHelper(multiprocessing.Process):

    """Simple subprocess that helps to cause race conditions ..."""

    def run(self):
        """Sleep for a couple of seconds before terminating."""
        timeout = random.random() * 5
        logger.debug("Race condition helper %i sleeping for %.2f seconds ..", os.getpid(), timeout)
        time.sleep(timeout)
        logger.debug("Race condition helper %i terminating ..", os.getpid())
