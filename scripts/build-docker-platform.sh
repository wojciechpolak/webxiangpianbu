#!/bin/bash

PLATFORM=${PLATFORM:-linux/amd64}

set -xe

docker build . -t wap/webxiang --platform $PLATFORM
