#!/bin/bash --login
set -e

conda activate legacyhalos-env
exec "$@"