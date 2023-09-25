#!/bin/sh
#SBATCH --job-name=legacyhalos_n_64
#SBATCH --mem=256000
#SBATCH --nodes=2
#SBATCH --ntasks=16
#SBATCH --cpus-per-task=16
#SBATCH --time=1:00:00
#SBATCH --account=desi
#SBATCH --qos=regular
#SBATCH --constraint=cpu
#SBATCH --licenses=cfs,SCRATCH
#SBATCH --image=docker:mattkwiecien/legacyhalos:latest
#SBATCH --output=/pscratch/sd/m/mkwiecie/legacydata/legacyhalos_n_64-%j.txt
#SBATCH --mail-user=mkwiecie@ucsc.edu
#SBATCH --mail-type=ALL
#SBATCH --module=mpich

# Interactive
# salloc -N 1 -A desi -C cpu -L cfs,SCRATCH -t 04:00:00 --qos interactive --module mpich --image docker:mattkwiecien/legacyhalos:latest

# Specify tasks and cores per task
ntasks=16
ncores=16
# Run refcat
export LARGEGALAXIES_CAT=/global/homes/m/mkwiecie/desi/sv3-clustering/64_randoms_tuning-refcat.fits
srun -n 1 -c 256 --cpu-bind=cores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh refcat 256
# Update refcat name
export LARGEGALAXIES_CAT=/global/homes/m/mkwiecie/desi/sv3-clustering/64_randoms_tuning-refcat.kd.fits

# Coadds step
srun -n $ntasks -c $ncores --cpu-bind=cores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh coadds $ncores

# Ellipse fitting
srun -n $ntasks -c $ncores --cpu-bind=cores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh ellipse $ncores

# Build plots
# srun -n $ntasks -c $ncores --cpu-bind=cores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlplots $ncores

# Build index page
# srun -n 1 -c 256 --cpu-bind=cores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlindex 256

