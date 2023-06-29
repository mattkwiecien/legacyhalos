#!/bin/sh
#SBATCH --job-name=sv3-legacyhalos-coadds-1
#SBATCH --mem=256000
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=1
#SBATCH --ntasks=64
#SBATCH --cpus-per-task=64
#SBATCH --time=12:00:00
#SBATCH --account=desi
#SBATCH --qos=regular
#SBATCH --constraint=cpu
#SBATCH --licenses=cfs,SCRATCH
#SBATCH --image=docker:legacysurvey/legacyhalos:v1.3
#SBATCH --output=/pscratch/sd/m/mkwiecie/sv3-mpi.log-%j.txt
#SBATCH --mail-user=mkwiecie@ucsc.edu
#SBATCH --mail-type=ALL
#SBATCH --module=mpich

# Specify tasks and cores per task
ntasks=64
ncores=64

# Since we are using SBATCH to load mpich and the image, we can just call shifter 

# Coadds step
srun -n $ntasks -c $ncores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh coadds $ncores

# Ellipse fitting
srun -n $ntasks -c $ncores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh ellipse $ncores

# Build plots
srun -n $ntasks -c $ncores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlplots $ncores

# Build index page
# srun -n 1 -c $ncores shifter $LEGACYHALOS_CODE_DIR/bin/sv3/sv3-mpi.sh htmlindex $ncores

