#!/bin/sh
#SBATCH --job-name=sv3-jiaxuan-overlap-legacyhalos-1
#SBATCH --mem=256000
#SBATCH --nodes=8
#SBATCH --ntasks=16
#SBATCH --cpus-per-task=16
#SBATCH --time=12:00:00
#SBATCH --account=desi
#SBATCH --qos=regular
#SBATCH --constraint=cpu
#SBATCH --licenses=cfs,SCRATCH
#SBATCH --image=docker:legacysurvey/legacyhalos:v1.2
#SBATCH --output=/pscratch/sd/m/mkwiecie/legacydata/sv3j_overlap_outputs/logs/sv3-jiaxuan.log-%j.txt
#SBATCH --mail-user=mkwiecie@ucsc.edu
#SBATCH --mail-type=ALL
#SBATCH --module=mpich

# Specify tasks and cores per task
ntasks=16
ncores=16

# Run refcat
export LARGEGALAXIES_CAT=/pscratch/sd/m/mkwiecie/legacydata/refcats/sv3_matches.fits
srun -n 1 -c $ncores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh refcat $ncores

# Update refcat name
export LARGEGALAXIES_CAT=/pscratch/sd/m/mkwiecie/legacydata/refcats/sv3_matches.kd.fits

# Coadds step
srun -n $ntasks -c $ncores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh coadds $ncores

# Ellipse fitting
srun -n $ntasks -c $ncores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh ellipse $ncores

# Build plots
srun -n $ntasks -c $ncores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlplots $ncores

# Build index page
# srun -n 1 -c $ncores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlindex $ncores

