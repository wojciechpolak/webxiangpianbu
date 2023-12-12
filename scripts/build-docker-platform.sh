#!/bin/bash

set -xe

PLATFORM=${PLATFORM:-linux/amd64}

docker build . -t wap/webxiang --platform $PLATFORM
