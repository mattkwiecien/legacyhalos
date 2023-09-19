#!/bin/bash
project=sv3

echo 'Updating and loading the shifter image docker:mattkwiecien/legacyhalos:latest'
echo 'Load the environment with: '
echo 'source '$LEGACYHALOS_CODE_DIR'/bin/sv3/sv3-env.sh'

shifterimg pull docker:mattkwiecien/legacyhalos:latest
shifter --image=docker:mattkwiecien/legacyhalos:latest /bin/bash 
