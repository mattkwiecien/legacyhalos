Steps to run on a new sv3 catalog
=================================

1. Create a new catalog of massive galaxies that you want to run on
2. Copy this to NERSC. 
   1. It must remain under your user, cannot be on PSCRATCH
   2. Output / html directories CAN be on PSCRATCH
3. Update sv3-env.sh to point to new directories
4. Update `sv3-mpi.sh` to use the new name of your catalog
   1. `LARGEGALAXIES_CAT` needs to have a `-refcat.fits` suffix before running refcat, and `-refcat.kd.fits` after
5. Build the refcat (**Bug Workaround Below**)
   1. Run `export LARGECALAXIES_CAT=/path/to/your/fits-refcat.fits`
   2. Run refcat step (`sv3-mpi.sh refcat`)
   3. Run `export LARGEGALAXIES_CAT=/path/to/your/fits-refcat.kd.fits`
6. Run coadds step
7. Run ellipse step
8. Run htmlplots step
9. Run htmlindex step