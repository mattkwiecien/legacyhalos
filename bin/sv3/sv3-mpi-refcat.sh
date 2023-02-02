#! /bin/bash
<<comment
Shell script for running the various stages of the legacyhalos code using
MPI+shifter at NERSC. Required arguments:
  {1} stage [coadds, pipeline-coadds, ellipse, htmlplots]
  {2} ncores [should match the resources requested.]

Example: build the coadds using 64 MPI tasks with 4 cores per node (and therefore 64*4/32=8 nodes)

Allocate
salloc -N 8 -C haswell -A desi -L cfs,SCRATCH -t 01:00:00 --qos interactive --image=legacysurvey/legacyhalos:v1.2

Refcat


comment
FILES=(\
    "subsampled_bgs_min_8235.47_max_14582.40"\
    "subsampled_bgs_min_3860.05_max_7096.44"\
    "subsampled_bgs_min_1922.97_max_3773.81"\
    "subsampled_bgs_min_968.14_max_1908.68"\
    "subsampled_bgs_min_492.14_max_957.75"\
    "subsampled_bgs_min_246.13_max_480.84"\
    "subsampled_bgs_min_124.30_max_241.02"\
    "subsampled_bgs_min_62.70_max_123.38"\
    "subsampled_bgs_min_31.50_max_62.21"\
    "subsampled_bgs_min_15.85_max_29.39"\
)
# Source the master env file.
source $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-env

for FILE in ${FILES[@]}; do
    echo $FILE
    # Update the large_gal cat for each one (no .kd for refcat)
    export LARGEGALAXIES_CAT=$LEGACYHALOS_DIR/$FILE-refcat.fits
    
    shifter --module=mpich-cle6 $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh refcat \
    0 $FILE.fits 

done
