#! /bin/bash
<<comment

Shell script for running the various stages of the legacyhalos code using
MPI+shifter at NERSC. Required arguments:
  {1} stage [coadds, pipeline-coadds, ellipse, htmlplots]
  {2} ncores [should match the resources requested.]

Example: build the coadds using 64 MPI tasks with 4 cores per node (and therefore 64*4/32=8 nodes)
Note 2>&1 redirects stoud and stderr to file AND shows on console. 
& allows he process ot start in background

Allocate
salloc -N 8 -C haswell -A desi -L cfs,SCRATCH -t 01:00:00 --qos interactive --image=legacysurvey/legacyhalos:v1.2

Refcat
shifter --module=mpich-cle6 $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh refcat \
    0 subsampled_bgs_min_22.73_max_23.85_111.fits 

Coadds
srun -n 64 -c 8 shifter --module=mpich-cle6 \
   $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh coadds 8 subsampled_bgs_min_22.73_max_23.85_111.fits 

Ellipse
srun -n 64 -c 8 shifter --module=mpich-cle6 \
    $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh ellipse 8 subsampled_bgs_min_22.73_max_23.85_111.fits 

Plots
srun -n 64 -c 8 shifter --module=mpich-cle6 \
    $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlplots 8 subsampled_bgs_min_22.73_max_23.85_111.fits 

Index
srun -n 128 -c 1 shifter --module=mpich-cle6 \
    $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlindex 1 subsampled_bgs_min_21.57_max_22.71_111.fits 

comment
# Grab the input arguments--
stage=$1
ncores=$2
fname=$3
last=$4


source $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-env

if [ $stage = "test" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --help
elif [ $stage = "coadds" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --coadds --nproc $ncores --mpi --fname $fname --verbose
elif [ $stage = "ellipse" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --ellipse --nproc $ncores --mpi --fname $fname --verbose
elif [ $stage = "htmlplots" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --htmlplots --nproc $ncores --mpi --fname $fname --verbose
elif [ $stage = "htmlindex" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --htmlindex --nproc $ncores --mpi --fname $fname --verbose
elif [ $stage = "refcat" ]; then
    time python $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi --build-refcat --fname $fname
else
    echo "Unrecognized stage "$stage
fi