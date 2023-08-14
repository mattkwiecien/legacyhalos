#!/bin/bash --login
set -e

source /opt/conda/etc/profile.d/conda.sh
conda activate /opt/legacyhalos/env

exec "$@"