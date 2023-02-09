#! /bin/bash

<<comment
Shell script for running the various stages of the legacyhalos code using
MPI+shifter at NERSC. Required arguments:
  {1} stage [coadds, pipeline-coadds, ellipse, htmlplots]
  {2} ncores [should match the resources requested.]

Example: build the coadds using 64 MPI tasks with 4 cores per node (and therefore 64*4/32=8 nodes)


Allocate
salloc -N 16 -C haswell -A desi -L cfs,SCRATCH -t 03:00:00 --qos interactive --image=legacysurvey/legacyhalos:v1.2

export BGS_FILENAME=subsampled_bgs_min_23.86_max_25.00_111

Runall
srun -n 16 -c 64 shifter --module=mpich-cle6 $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh runall 64 \
    > /global/homes/m/mkwiecie/desi/sv3-clustering/subsampled_bgs/logs/runall-$BGS_FILENAME.log 2>&1 &


Coadds
srun -n 16 -c 64 shifter --module=mpich-cle6 $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh coadds 64 \
    > /global/homes/m/mkwiecie/desi/sv3-clustering/subsampled_bgs/logs/coadds-$BGS_FILENAME.log 2>&1 &

Ellipse
srun -n 16 -c 64 shifter --module=mpich-cle6 $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh ellipse 64 \
    > /global/homes/m/mkwiecie/desi/sv3-clustering/subsampled_bgs/logs/ellipse-$BGS_FILENAME.log 2>&1 &

Plots
srun -n 16 -c 64 shifter --module=mpich-cle6 $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlplots 64 \
    > /global/homes/m/mkwiecie/desi/sv3-clustering/subsampled_bgs/logs/plots-$BGS_FILENAME.log 2>&1 &

Index
srun -N 1 -n 1 -c 64 shifter --module=mpich-cle6 $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlindex 64 \
    > /global/homes/m/mkwiecie/desi/sv3-clustering/subsampled_bgs/logs/index-$BGS_FILENAME.log 2>&1 &

comment
# Grab the input arguments--
stage=$1
ncores=$2

# wont complete /global/cscratch1/sd/mkwiecie/legacydata/output/3962/39628438616674378
# subsampled_bgs_min_15.85_max_29.39.fits
export BGS_FILENAME=subsampled_bgs_min_23.86_max_25.00_111

# Source the base env variables
source $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-env

# Set the refcat
export LARGEGALAXIES_CAT=$LEGACYHALOS_DIR/$BGS_FILENAME-refcat.kd.fits

if [ $stage = "test" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --help
elif [ $stage = "coadds" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --coadds --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose 
elif [ $stage = "ellipse" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --ellipse --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose
elif [ $stage = "htmlplots" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --htmlplots --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose
elif [ $stage = "htmlindex" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --htmlindex --nproc $ncores --fname $BGS_FILENAME.fits --verbose
elif [ $stage = "refcat" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --build-refcat --fname $BGS_FILENAME.fits
elif [ $stage = "runall" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --coadds --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose --clobber
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --ellipse --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose --clobber
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --htmlplots --nproc $ncores --mpi --fname $BGS_FILENAME.fits --verbose --clobber
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --htmlindex --nproc $ncores --fname $BGS_FILENAME.fits --verbose --clobber
else
    echo "Unrecognized stage "$stage
fi