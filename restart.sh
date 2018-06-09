#!/bin/bash

set -e
cd /usr/local/bin/ebisu

# env
rm -f /etc/init.d/ebisu
ln -s /usr/local/bin/ebisu/init.d/ebisu /etc/init.d/ebisu

# force pull
git fetch origin
git reset --hard origin/master

# restart all service
service ebisu restart
