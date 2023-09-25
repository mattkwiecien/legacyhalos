#! /bin/bash

stage=$1
ncores=$2
fname=64_randoms_tuning.fits
# Source the base env variables 
# This is overwriting the docker container global variables with your local repos/paths

source $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-env.sh

if [ $stage = "coadds" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.py --coadds --nproc $ncores --mpi --fname $fname --clobber --force
elif [ $stage = "ellipse" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.py --ellipse --nproc $ncores --mpi --fname $fname --force --clobber
elif [ $stage = "htmlplots" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.py --htmlplots --nproc $ncores --mpi --fname $fname --clobber --force
elif [ $stage = "htmlindex" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.py --htmlindex --nproc $ncores --fname $fname --clobber --force
elif [ $stage = "refcat" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.py --build-refcat --fname $fname --clobber --debug
else
    echo "Unrecognized stage "$stage
fi
