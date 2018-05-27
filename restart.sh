#!/bin/bash

set -e
cd /usr/local/bin/daikokuten

# env
rm -f /etc/init.d/daikokuten
ln -s /usr/local/bin/daikokuten/init.d/daikokuten /etc/init.d/daikokuten

# force pull
git fetch origin
git reset --hard origin/master

# restart all service
service daikokuten restart
