#! /bin/bash

stage=$1
ncores=$2

# Source the base env variables 
# This is overwriting the docker container global variables with your local repos/paths

source $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-env

if [ $stage = "coadds" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --coadds --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose 
elif [ $stage = "ellipse" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --ellipse --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose
elif [ $stage = "htmlplots" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --htmlplots --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose
elif [ $stage = "htmlindex" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --htmlindex --nproc $ncores --fname $BGS_FILENAME.fits --verbose
elif [ $stage = "refcat" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --build-refcat --fname $BGS_FILENAME.fits
else
    echo "Unrecognized stage "$stage
fi