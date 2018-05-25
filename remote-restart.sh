#!/bin/bash -xe

scp restart.sh root@ec2-52-18-28-163.eu-west-1.compute.amazonaws.com:restart.sh
ssh -A root@ec2-52-18-28-163.eu-west-1.compute.amazonaws.com /bin/bash restart.sh
