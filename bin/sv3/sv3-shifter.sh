#!/bin/bash
project=sv3

echo 'Updating and loading the shifter image docker:ghcr.io/mattkwiecien/legacyhalos:docker-img-0.1.0'
echo 'Load the environment with: '
echo 'source '$LEGACYHALOS_CODE_DIR'/bin/sv3/sv3-env.sh'

shifterimg pull docker:ghcr.io/mattkwiecien/legacyhalos:docker-img-0.1.0
shifter --image=docker:ghcr.io/mattkwiecien/legacyhalos:docker-img-0.1.0 /bin/bash 
