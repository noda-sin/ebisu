#!/bin/bash

set -e
cd /usr/local/bin/daikokuten

# force pull
git fetch origin
git reset --hard origin/master

# restart all service
service daikokuten restart
