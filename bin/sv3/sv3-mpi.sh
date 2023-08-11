#! /bin/bash

stage=$1
ncores=$2

# Source the base env variables 
# This is overwriting the docker container global variables with your local repos/paths

source $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-env.sh

if [ $stage = "coadds" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.py --coadds --nproc $ncores --mpi --fname sv3_matches.fits --verbose --clobber --debug --force
elif [ $stage = "ellipse" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.py --ellipse --nproc 256 --mpi --fname sv3_matches.fits --verbose --force --clobber --debug --force
elif [ $stage = "htmlplots" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.py --htmlplots --nproc $ncores --mpi --fname sv3_matches.fits --verbose --clobber --debug --force
elif [ $stage = "htmlindex" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.py --htmlindex --nproc $ncores --fname sv3_matches.fits --verbose --clobber --debug --force
elif [ $stage = "refcat" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.py --build-refcat --fname sv3_matches.fits --clobber --debug
else
    echo "Unrecognized stage "$stage
fi
