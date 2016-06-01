# Makefile for proc.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 1, 2016
# URL: https://github.com/xolox/python-proc

WORKON_HOME ?= $(HOME)/.virtualenvs
VIRTUAL_ENV ?= $(WORKON_HOME)/proc
PATH := $(VIRTUAL_ENV)/bin:$(PATH)
MAKE := $(MAKE) --no-print-directory

default:
	@echo 'Makefile for proc'
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make install   install the package in a virtual environment'
	@echo '    make reset     recreate the virtual environment'
	@echo '    make test      run the test suite'
	@echo '    make coverage  run the tests, report coverage'
	@echo '    make docs      update documentation using Sphinx'
	@echo '    make publish   publish changes to GitHub/PyPI'
	@echo '    make clean     cleanup all temporary files'
	@echo

install:
	@test -d "$(VIRTUAL_ENV)" || mkdir -p "$(VIRTUAL_ENV)"
	@test -x "$(VIRTUAL_ENV)/bin/python" || virtualenv --quiet "$(VIRTUAL_ENV)"
	@test -x "$(VIRTUAL_ENV)/bin/pip" || easy_install pip
	@test -x "$(VIRTUAL_ENV)/bin/pip-accel" || pip install --quiet pip-accel
	@pip uninstall -y proc 1>/dev/null 2>&1 || true
	@pip-accel install --quiet --editable .

reset:
	$(MAKE) clean
	rm -Rf "$(VIRTUAL_ENV)"
	$(MAKE) install

check: install
	test -x "$(VIRTUAL_ENV)/bin/flake8" || pip-accel install --quiet flake8-pep257
	flake8

pytest: install
	test -x "$(VIRTUAL_ENV)/bin/py.test" || pip-accel install --quiet pytest
	py.test

tox: install
	test -x "$(VIRTUAL_ENV)/bin/tox" || pip-accel install --quiet tox
	tox

coverage: install
	test -x "$(VIRTUAL_ENV)/bin/coverage" || pip-accel install --quiet coverage
	coverage run setup.py test
	coverage combine
	coverage html
	coverage report --fail-under=90

# The following makefile target isn't documented on purpose, I don't want
# people to execute this without them knowing very well what they're doing.

full-coverage: install
	test -x "$(VIRTUAL_ENV)/bin/coverage" || pip-accel install --quiet coverage
	scripts/collect-full-coverage
	coverage html

docs: install
	test -x "$(VIRTUAL_ENV)/bin/sphinx-build" || pip-accel install --quiet sphinx
	cd docs && sphinx-build -nb html -d build/doctrees . build/html

publish:
	git push origin && git push --tags origin
	make clean && python setup.py sdist upload

clean:
	rm -Rf *.egg *.egg-info .coverage .tox build dist docs/build htmlcov
	find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	find -type f -name '*.pyc' -delete

.PHONY: default install reset pytest tox coverage full-coverage docs publish clean
