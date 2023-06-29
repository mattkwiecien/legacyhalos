#!/bin/bash
project=sv3

echo 'Updating and loading the shifter image docker:legacysurvey/legacyhalos:v1.3'
echo 'Load the environment with: '
echo 'source '$LEGACYHALOS_CODE_DIR'/bin/sv3/sv3-env'

shifterimg pull docker:legacysurvey/legacyhalos:v1.3
shifter --module=mpich --image=docker:legacysurvey/legacyhalos:v1.3 /bin/bash 