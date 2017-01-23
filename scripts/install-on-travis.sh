#!/bin/bash -e

# This shell script is used by .travis.yml:
#
#  - To install and configure the Apache webserver and
#    mod_wsgi in order to test the proc.apache module.
#
#  - To install the gpg-agent in order to test the proc.gpg module.
#
# This script assumes it is running on Ubuntu 12.04 because
# that's what Travis CI uses at the time of writing.

# Let apt-get, dpkg and related tools know that we want the following
# commands to be 100% automated (no interactive prompts).
export DEBIAN_FRONTEND=noninteractive

# Update apt-get's package lists.
sudo apt-get update -qq

# Use apt-get to install the Apache webserver, mod_wsgi and the GnuPG agent.
sudo apt-get install --yes apache2-mpm-prefork libapache2-mod-wsgi gnupg-agent

# Create a dummy virtual host that contains the minimal mod_wsgi directives
# required to cause it to spawn daemon worker processes. Yes, this is a nasty
# hack, but we really don't need more than this :-).
sudo tee /etc/apache2/sites-enabled/proc-test-vhost >/dev/null << EOF
<VirtualHost *>
  WSGIScriptAlias / /foo/bar/baz/wsgi.py
  WSGIDaemonProcess proc-test processes=4 threads=1 display-name=%{GROUP}
  WSGIProcessGroup proc-test
</VirtualHost>
EOF

# Activate the dummy virtual host.
sudo service apache2 reload
