#!/bin/bash
project=sv3

echo 'Updating and loading the shifter image docker:legacysurvey/legacyhalos:v1.2'
echo 'Load the environment with: '
echo 'source '$LEGACYHALOS_CODE_DIR'/bin/sv3/sv3-env'

shifterimg pull docker:legacysurvey/legacyhalos:v1.2
shifter /bin/bash 