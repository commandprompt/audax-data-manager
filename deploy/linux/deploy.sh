#!/bin/bash

docker run -e VERSION=${1} -e BRANCH=${2-dev} -v $PWD:/deploy --rm pgmanage/tarbuild

sudo chown $USER:$USER *.tar.gz
sudo chown $USER:$USER *.AppImage
sudo chown $USER:$USER *.deb
sudo chown $USER:$USER *.rpm
