Changelog
=========

The purpose of this document is to list all of the notable changes to this
project. The format was inspired by `Keep a Changelog`_. This project adheres
to `semantic versioning`_.

.. contents::
   :local:

.. _Keep a Changelog: http://keepachangelog.com/
.. _semantic versioning: http://semver.org/

`Release 0.15`_ (2018-06-21)
----------------------------

- Changes related to the ``proc.gpg`` module and the ``with-gpg-agent`` program:

  - Use existing ``$GPG_AGENT_INFO`` values when available and validated.
  - Let the operator know when starting a new GPG agent daemon (through logging).
  - Check if ``gpg-agent`` is installed before trying to run ``gpg-agent --daemon``.
  - Added support for GPG agent sockets in ``/run/user/$UID`` (GnuPG >= 2.1.13).

    - This incompatibility came to light when I upgraded my laptop from Ubuntu
      16.04 to 18.04.

  - Fixed hanging Travis CI builds caused by ``gpg-agent --daemon`` not
    detaching properly when the standard error stream is redirected.

    - This incompatibility was exposed by Travis CI switching from Ubuntu 12.04
      to 14.04.

  - Fixed race condition in ``find_gpg_agent_info()`` raising ``AttributeError``.

- Changes related to the documentation:

  - Added this change log to the documentation (with a link in the readme).
  - Integrated the ``property_manager.sphinx`` module (to generate boilerplate
    documentation).
  - Fixed intersphinx mapping in documentation configuration.
  - Changed HTML theme from `default` to `nature` (a wide layout).
  - Include documentation in source distributions (``MANIFEST.in``).

- And then some miscellaneous changes:

  - Fixed Apache WSGI configuration on Travis CI.

    - This test suite incompatibility was exposed by Travis CI switching from
      Ubuntu 12.04 to 14.04.

  - Restored Python 2.6 compatibility in the test suite (concerning ``pytest`` version).
  - Added license=MIT key to ``setup.py`` script.
  - Bumped the copyright to 2018.

.. _Release 0.15: https://github.com/xolox/python-proc/compare/0.14...0.15

`Release 0.14`_ (2017-06-24)
----------------------------

Swallow exceptions in the ``notify_desktop()`` function.

This change is technically backwards incompatible but I consider it the more
sane behavior; I had just simply never seen ``notify-send`` fail until the
failure which prompted this release 😇.

.. _Release 0.14: https://github.com/xolox/python-proc/compare/0.13...0.14

`Release 0.13`_ (2017-06-24)
----------------------------

- Provide proper compatibility with GnuPG  >= 2.1 which uses the fixed
  location ``~/.gnupg/S.gpg-agent`` for the agent socket.
- Bug fix for systemd incompatibility in test suite.
- Moved test helpers to the ``humanfriendly.testing`` module.

.. _Release 0.13: https://github.com/xolox/python-proc/compare/0.12...0.13

`Release 0.12`_ (2017-02-14)
----------------------------

Improved robustness of Apache master process selection.

.. _Release 0.12: https://github.com/xolox/python-proc/compare/0.11...0.12

`Release 0.11`_ (2017-01-24)
----------------------------

Added ``with-gpg-agent`` program: A smart wrapper for the ``gpg-agent
--daemon`` functionality that makes sure the environment variable
``$GPG_AGENT_INFO`` is always set correctly.

.. _Release 0.11: https://github.com/xolox/python-proc/compare/0.10.1...0.11

`Release 0.10.1`_ (2016-11-13)
------------------------------

Fixed broken reStructuredText syntax in README (which breaks the rich text
rendering on the Python Package Index).

.. _Release 0.10.1: https://github.com/xolox/python-proc/compare/0.10...0.10.1

`Release 0.10`_ (2016-11-12)
----------------------------

- Several improvements to ``cron-graceful``:

  - Improved cron daemon termination.
  - Improved user friendliness of output.
  - Avoid useless log output noise.

- Start publishing wheel distributions.
- Explicitly signal skipped tests (when possible).
- Refactored internal project infrastructure such as the makefile, setup script
  and Travis CI build configuration.

.. _Release 0.10: https://github.com/xolox/python-proc/compare/0.9.1...0.10

`Release 0.9.1`_ (2016-06-13)
-----------------------------

Silenced another race condition (``ESRCH`` instead of ``ENOENT``).

This is one of those things that you only observe after running a package like
`proc` from a periodic task (cron job) that runs every minute on a dozen
servers for a couple of weeks :-). The error condition was -correctly- being
swallowed already, but it was more noisy than it needed to be.

.. _Release 0.9.1: https://github.com/xolox/python-proc/compare/0.9...0.9.1

`Release 0.9`_ (2016-06-01)
---------------------------

Refactored the separation of concerns between the executor_ and proc_ packages.

Please refer to the commit message of the other side of this refactoring
(`executor#b484912bb33`_) for details about the how and why of this fairly
involved refactoring :-).

.. _Release 0.9: https://github.com/xolox/python-proc/compare/0.8.5...0.9
.. _executor#b484912bb33: https://github.com/xolox/python-executor/commit/b484912bb33

`Release 0.8.5`_ (2016-05-27)
-----------------------------

- Demote race condition log messages from WARNING to DEBUG level.

  Reasoning: Race condition log messages are so frequent that they become
  noise, drowning out other more important log messages, so I decided to make
  them less noisy :-).

- Fixed a confusing typo in the API docs, left over from a sentence that was
  (half) reformulated.

- Noted a future improvement in the documentation: Generalized
  ``notify-send-headless`` functionality.

.. _Release 0.8.5: https://github.com/xolox/python-proc/compare/0.8.4...0.8.5

`Release 0.8.4`_ (2016-04-22)
-----------------------------

- Improved ``notify-send-headless`` documentation.
- Improved test coverage by mocking external dependencies.

.. _Release 0.8.4: https://github.com/xolox/python-proc/compare/0.8.3...0.8.4

`Release 0.8.3`_ (2016-04-21)
-----------------------------

- Increase ``cron-graceful[-additions]`` test coverage.
- Avoid duplicate builds on Travis CI.
- Test suite bug fix.

.. _Release 0.8.3: https://github.com/xolox/python-proc/compare/0.8.2...0.8.3

`Release 0.8.2`_ (2016-04-21)
-----------------------------

Increase test coverage (somewhat of a cop-out :-).

.. _Release 0.8.2: https://github.com/xolox/python-proc/compare/0.8.1...0.8.2

`Release 0.8.1`_ (2016-04-21)
-----------------------------

Now including an upstream bug fix to make the previous release work :-(.

.. _Release 0.8.1: https://github.com/xolox/python-proc/compare/0.8...0.8.1

`Release 0.8`_ (2016-04-21)
---------------------------

- Try to make ``notify-send-headless`` foolproof.
- Document supported Python implementations in ``setup.py``.
- Enabled Python 3.5 tests on Travis CI, documented Python 3.5 support.

.. _Release 0.8: https://github.com/xolox/python-proc/compare/0.7...0.8

`Release 0.7`_ (2016-01-29)
---------------------------

Expose the real user/group names of processes.

.. _Release 0.7: https://github.com/xolox/python-proc/compare/0.6...0.7

`Release 0.6`_ (2016-01-28)
---------------------------

- Expose ``/proc/[pid]/status`` (UID/GID information considered useful :-).
- Changed ``Process.from_pid()`` to use ``Process.from_path()``.
- Re-ordered fields of ``Process`` class alphabetically.
- Switched to flake8 for code style checks, fixed code style warnings pointed out by flake8.
- Updated ``tox.ini`` to include ``py35`` and pytest / flake8 options.
- Improved test coverage.
- Refactored the makefile.

.. _Release 0.6: https://github.com/xolox/python-proc/compare/0.5.1...0.6

`Release 0.5.1`_ (2015-11-19)
-----------------------------

Bug fix: Restored Python 2.6 compatibility (regarding the ``__exit__()``
calling convention).

.. _Release 0.5.1: https://github.com/xolox/python-proc/compare/0.5...0.5.1

`Release 0.5`_ (2015-11-19)
---------------------------

- Extracted ``/proc/uptime`` parsing to a separate function.
- Generalized error handling (of permission errors and race conditions).
- Expose ``/proc/[pid]/environ`` (also: ``notify-send-headless`` :-).

.. _Release 0.5: https://github.com/xolox/python-proc/compare/0.4.1...0.5

`Release 0.4.1`_ (2015-11-10)
-----------------------------

Two minor bug fixes:

- Added a ``Process.command_line`` to ``Process.cmdline`` alias (to improve the
  compatibility with the process management code that's shared between the
  executor_ and proc_ packages).

- Improved the documentation after refactorings in the 0.4 release broke some
  references.

.. _Release 0.4.1: https://github.com/xolox/python-proc/compare/0.4...0.4.1

`Release 0.4`_ (2015-11-10)
---------------------------

- Improved process management (shared between the executor_ and proc_ packages).
- Switched from cached-property_ to property-manager_.

.. _Release 0.4: https://github.com/xolox/python-proc/compare/0.3...0.4
.. _executor: https://pypi.org/project/executor/
.. _proc: https://pypi.org/project/proc/
.. _cached-property: https://pypi.org/project/cached-property/
.. _property-manager: https://pypi.org/project/property-manager/

`Release 0.3`_ (2015-09-25)
---------------------------

Make the ``cron-graceful`` command "repeatable" (as in, running it twice will
not report a ``CronDaemonNotRunning`` exception to the terminal but will just
mention that cron is not running and then exit gracefully).

.. _Release 0.3: https://github.com/xolox/python-proc/compare/0.2.3...0.3

`Release 0.2.3`_ (2015-09-25)
-----------------------------

- Bug fix: Make sure interactive spinners restore cursor visibility.
- Refactored ``setup.py`` script, improved trove classifiers.
- Removed redundant ``:py:`` prefixes from reStructuredText fragments.
- Bug fix for ``make coverage`` target in ``Makefile``.

.. _Release 0.2.3: https://github.com/xolox/python-proc/compare/0.2.2...0.2.3

`Release 0.2.2`_ (2015-06-26)
-----------------------------

Bug fix: Avoid ``KeyError`` exception during tree construction.

.. _Release 0.2.2: https://github.com/xolox/python-proc/compare/0.2.1...0.2.2

`Release 0.2.1`_ (2015-04-16)
-----------------------------

- Fixed incompatibility with cached-property 1.1.0 (removed ``__slots__`` usage).
- Fixed last remaining Python 2.6 incompatibility (in test suite).

.. _Release 0.2.1: https://github.com/xolox/python-proc/compare/0.2...0.2.1

`Release 0.2`_ (2015-03-30)
---------------------------

- Added an example ``proc.apache`` module that monitors Apache worker memory usage.
- Made the test suite more robust and increased test coverage.

.. _Release 0.2: https://github.com/xolox/python-proc/compare/0.1.1...0.2

`Release 0.1.1`_ (2015-03-30)
-----------------------------

- Enable callers to override object type for ``proc.tree.get_process_tree()``.
- Started documenting similar projects in the readme.

.. _Release 0.1.1: https://github.com/xolox/python-proc/compare/0.1...0.1.1

`Release 0.1`_ (2015-03-29)
---------------------------

This was the initial commit and release. The "History" section of the readme
provides a bit more context:

I've been writing shell and Python scripts that parse ``/proc`` for years now
(it seems so temptingly easy when you get started ;-). Sometimes I resorted to
copy/pasting snippets of Python code between personal and work projects because
the code was basically done, just not available in an easy to share form.

Once I started fixing bugs in diverging copies of that code I decided it was
time to combine all of the features I'd grown to appreciate into a single well
tested and well documented Python package with an easy to use API and share it
with the world.

This means that, although I made my first commit on the `proc` package in March
2015, much of its code has existed for years in various forms.

.. _Release 0.1: https://github.com/xolox/python-proc/tree/0.1
