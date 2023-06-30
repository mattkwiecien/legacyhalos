#!/bin/bash
project=sv3

echo 'Updating and loading the shifter image docker:mattkwiecien/legacyhalos:v1.3.1'
echo 'Load the environment with: '
echo 'source '$LEGACYHALOS_CODE_DIR'/bin/sv3/sv3-env'

shifterimg pull docker:mattkwiecien/legacyhalos:v1.3.1
shifter --image=docker:mattkwiecien/legacyhalos:v1.3.1 /bin/bash 
