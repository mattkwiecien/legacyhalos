#! /bin/bash
# Shell script to set the environment variables for SV3 data.

project=sv3

#############################
# For a power-user / testing. Use local checkouts of the code even though it's
# in the Docker container.
# Prepend your local repo directories to your python path to use yours version
export LEGACYPIPE_CODE_DIR=/global/homes/m/mkwiecie/desi/repos/legacypipe
export LEGACYHALOS_CODE_DIR=/global/homes/m/mkwiecie/desi/repos/legacyhalos
export PYTHONPATH=$LEGACYHALOS_CODE_DIR/py:$LEGACYPIPE_CODE_DIR/py:$PYTHONPATH
export PATH=$LEGACYHALOS_CODE_DIR/bin/sv3:$PATH
#############################

# Specify the location of the input and output data.
export LEGACYHALOS_DIR=/global/homes/m/mkwiecie/desi/sv3-clustering
export LEGACYHALOS_DATA_DIR=/pscratch/sd/m/mkwiecie/legacydata/sv3_perf_tuning/64/output
export LEGACYHALOS_HTML_DIR=/pscratch/sd/m/mkwiecie/legacydata/sv3_perf_tuning/64/html
#export LARGEGALAXIES_CAT=$LEGACYHALOS_DIR/128_randoms_tuning-refcat.kd.fits
#export LARGEGALAXIES_CAT=$LEGACYHALOS_DIR/128_randoms_tuning-refcat.kd.fits

# Pipeline variables---only change these if you know what you're doing!
export LEGACY_SURVEY_DIR=/global/cfs/cdirs/cosmo/work/legacysurvey/dr9
export SKY_TEMPLATE_DIR=/global/cfs/cdirs/cosmo/data/legacysurvey/dr9/calib/sky_pattern

export GAIA_CAT_VER=2
export GAIA_CAT_DIR=/global/cfs/cdirs/cosmo/work/gaia/chunks-gaia-dr2-astrom-2
export UNWISE_COADDS_DIR=/global/cfs/cdirs/cosmo/data/unwise/neo6/unwise-coadds/fulldepth:/global/cfs/cdirs/cosmo/data/unwise/allwise/unwise-coadds/fulldepth
export UNWISE_MODEL_SKY_DIR=/global/cfs/cdirs/cosmo/work/wise/unwise_catalog/dr3/mod
export TYCHO2_KD_DIR=/global/cfs/cdirs/cosmo/staging/tycho2
#export LARGEGALAXIES_CAT=/global/cfs/cdirs/cosmo/staging/largegalaxies/v3.0/SGA-parent-v3.0.kd.fits
#export LARGEGALAXIES_CAT=/global/cfs/cdirs/cosmo/staging/largegalaxies/v3.0/SGA-ellipse-v3.0.kd.fits
export PS1CAT_DIR=/global/cfs/cdirs/cosmo/work/ps1/cats/chunks-qz-star-v3
export DUST_DIR=/global/cfs/cdirs/cosmo/data/dust/v0_1
export GALEX_DIR=/global/cfs/cdirs/cosmo/data/galex/images
export REDMAPPER_DIR=/global/cfs/cdirs/desi/users/ioannis/redmapper

# Uncomment this variable if you want time-resolved unWISE photometry (generally not needed). 
#export UNWISE_COADDS_TIMERESOLVED_DIR=/global/cfs/cdirs/cosmo/work/wise/outputs/merge/neo6

export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export KMP_AFFINITY=disabled
export MPICH_GNI_FORK_MODE=FULLCOPY

# Config directory nonsense
export TMPCACHE=$(mktemp -d)
mkdir $TMPCACHE/cache
mkdir $TMPCACHE/config
# astropy
export XDG_CACHE_HOME=$TMPCACHE/cache
export XDG_CONFIG_HOME=$TMPCACHE/config
mkdir $XDG_CACHE_HOME/astropy
cp -r $HOME/.astropy/cache $XDG_CACHE_HOME/astropy
mkdir $XDG_CONFIG_HOME/astropy
cp -r $HOME/.astropy/config $XDG_CONFIG_HOME/astropy
# matplotlib
export MPLCONFIGDIR=$TMPCACHE/matplotlib
mkdir $MPLCONFIGDIR
cp -r $HOME/.config/matplotlib $MPLCONFIGDIR
