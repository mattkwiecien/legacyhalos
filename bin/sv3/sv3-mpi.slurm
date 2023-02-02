#! /bin/bash
#SBATCH -A desi
#SBATCH --module=mpich-cle6
#SBATCH -C haswell
#SBATCH -L cfs,SCRATCH
#SBATCH -o sv3-mpi.log-%j.txt
#SBATCH --image=legacysurvey/legacyhalos:v1.2
#SBATCH --mail-user=mkwiecie@ucsc.edu
#SBATCH --mail-type=ALL
#SBATCH --job-name=sv3-legacyhalos-coadds-1
#SBATCH -p regular
#SBATCH -N 8
#SBATCH -n 64
#SBATCH -t 04:00:00

export BGS_FILENAME=subsampled_bgs_min_1908.68_max_3777.09

source $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-env

export LARGEGALAXIES_CAT=$LEGACYHALOS_DIR/$BGS_FILENAME-refcat.kd.fits

# coadds
time srun -N 8 -n 64 -c 8 shifter --module=mpich-cle6 \
   $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh coadds 8 $BGS_FILENAME.fits

# # coadds
# time srun -N 8 -n 64 -c 8 shifter --module=mpich-cle6 \
#    $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh ellipse 8 $BGS_FILENAME.fits


# # coadds
# time srun -N 8 -n 64 -c 8 shifter --module=mpich-cle6 \
#    $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlplots 8 $BGS_FILENAME.fits


# # coadds
# time srun -N 8 -n 128 -c 1 shifter --module=mpich-cle6 \
#    $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlindex 1 $BGS_FILENAME.fits
