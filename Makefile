# Makefile for proc.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: March 30, 2015
# URL: https://github.com/xolox/python-proc

WORKON_HOME ?= $(HOME)/.virtualenvs
VIRTUAL_ENV ?= $(WORKON_HOME)/proc
ACTIVATE = . $(VIRTUAL_ENV)/bin/activate

default:
	@echo 'Makefile for proc'
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make install    install the package in a virtual environment'
	@echo '    make reset      recreate the virtual environment'
	@echo '    make test       run the test suite'
	@echo '    make coverage   run the tests, report coverage'
	@echo '    make docs       update documentation using Sphinx'
	@echo '    make publish    publish changes to GitHub/PyPI'
	@echo '    make clean      cleanup all temporary files'
	@echo

install:
	@test -d "$(VIRTUAL_ENV)" || virtualenv "$(VIRTUAL_ENV)"
	@test -x "$(VIRTUAL_ENV)/bin/pip" || ($(ACTIVATE) && easy_install pip)
	@test -x "$(VIRTUAL_ENV)/bin/pip-accel" || ($(ACTIVATE) && pip install pip-accel)
	@$(ACTIVATE) && pip uninstall -y proc 1>/dev/null 2>&1 || true
	@$(ACTIVATE) && pip-accel install --editable .

reset:
	rm -Rf "$(VIRTUAL_ENV)"
	make --no-print-directory clean install

check: install
	test -x "$(VIRTUAL_ENV)/bin/pep8" || ($(ACTIVATE) && pip-accel install pep8)
	test -x "$(VIRTUAL_ENV)/bin/pep257" || ($(ACTIVATE) && pip-accel install pep257)
	$(ACTIVATE) && pep8 --ignore=E402 --max-line-length=120 setup.py docs/conf.py proc
	$(ACTIVATE) && pep257 --ignore=D200 setup.py docs/conf.py proc

pytest: install
	test -x "$(VIRTUAL_ENV)/bin/py.test" || ($(ACTIVATE) && pip-accel install pytest)
	$(ACTIVATE) && py.test --capture=no proc/tests.py

tox: install
	test -x "$(VIRTUAL_ENV)/bin/tox" || ($(ACTIVATE) && pip-accel install tox)
	$(ACTIVATE) && tox

coverage: install
	test -x "$(VIRTUAL_ENV)/bin/coverage" || ($(ACTIVATE) && pip-accel install coverage)
	$(ACTIVATE) && coverage run setup.py test
	$(ACTIVATE) && coverage html
	$(ACTIVATE) && coverage report --fail-under=90

# The following makefile target isn't documented on purpose, I don't want
# people to execute this without them knowing very well what they're doing.

full-coverage: install
	test -x "$(VIRTUAL_ENV)/bin/coverage" || ($(ACTIVATE) && pip-accel install coverage)
	$(ACTIVATE) && scripts/collect-full-coverage
	$(ACTIVATE) && coverage html

docs: install
	test -x "$(VIRTUAL_ENV)/bin/sphinx-build" || ($(ACTIVATE) && pip-accel install sphinx)
	$(ACTIVATE) && cd docs && sphinx-build -b html -d build/doctrees . build/html

publish:
	git push origin && git push --tags origin
	make clean && python setup.py sdist upload

clean:
	rm -Rf *.egg *.egg-info .coverage .tox build dist docs/build htmlcov
	find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	find -type f -name '*.pyc' -delete

.PHONY: default install reset pytest tox coverage full-coverage docs publish clean
