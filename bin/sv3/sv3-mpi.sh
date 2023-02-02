#! /bin/bash

<<comment
Shell script for running the various stages of the legacyhalos code using
MPI+shifter at NERSC. Required arguments:
  {1} stage [coadds, pipeline-coadds, ellipse, htmlplots]
  {2} ncores [should match the resources requested.]

Example: build the coadds using 64 MPI tasks with 4 cores per node (and therefore 64*4/32=8 nodes)


Allocate
salloc -N 8 -C haswell -A desi -L cfs,SCRATCH -t 01:00:00 --qos interactive --image=legacysurvey/legacyhalos:v1.2

export BGS_FILENAME=subsampled_bgs_min_8235.47_max_14582.40

Coadds
srun -n 64 -c 8 shifter --module=mpich-cle6 $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh coadds 8 \
    > /global/homes/m/mkwiecie/desi/sv3-clustering/subsampled_bgs/logs/coadds-$BGS_FILENAME.log 2>&1

Ellipse
srun -n 64 -c 8 shifter --module=mpich-cle6 $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh ellipse 8 \
    > /global/homes/m/mkwiecie/desi/sv3-clustering/subsampled_bgs/logs/coadds-$BGS_FILENAME.log 2>&1

Plots
srun -n 32 -c 16 shifter --module=mpich-cle6 $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlplots 16 \
    > /global/homes/m/mkwiecie/desi/sv3-clustering/subsampled_bgs/logs/coadds-$BGS_FILENAME.log 2>&1

Index
srun -n 128 -c 1 shifter --module=mpich-cle6 $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlindex 1 \
    > /global/homes/m/mkwiecie/desi/sv3-clustering/subsampled_bgs/logs/coadds-$BGS_FILENAME.log 2>&1

comment
# Grab the input arguments--
stage=$1
ncores=$2

# Choose which catalog to run on
# subsampled_bgs_min_8235.47_max_14582.40.fits
# subsampled_bgs_min_3860.05_max_7096.44.fits
# subsampled_bgs_min_1922.97_max_3773.81.fits
# subsampled_bgs_min_968.14_max_1908.68.fits
# subsampled_bgs_min_492.14_max_957.75.fits
# subsampled_bgs_min_246.13_max_480.84.fits
# subsampled_bgs_min_124.30_max_241.02.fits
# subsampled_bgs_min_62.70_max_123.38.fits
# subsampled_bgs_min_31.50_max_62.21.fits
# subsampled_bgs_min_15.85_max_29.39.fits
export BGS_FILENAME=subsampled_bgs_min_8235.47_max_14582.40

# Source the base env variables
source $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-env

# Set the refcat
export LARGEGALAXIES_CAT=$LEGACYHALOS_DIR/$BGS_FILENAME-refcat.kd.fits

if [ $stage = "test" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --help
elif [ $stage = "coadds" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --coadds --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose --clobber --debug
elif [ $stage = "ellipse" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --ellipse --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose --clobber --debug
elif [ $stage = "htmlplots" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --htmlplots --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose --clobber --debug
elif [ $stage = "htmlindex" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --htmlindex --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose --clobber --debug
elif [ $stage = "refcat" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --build-refcat --fname $BGS_FILENAME.fits
else
    echo "Unrecognized stage "$stage
fi