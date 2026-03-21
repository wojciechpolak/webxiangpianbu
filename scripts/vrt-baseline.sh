#!/bin/bash

set -eu
VRT=1 VRT_UPDATE=1 uv run pytest -m e2e "$@"
