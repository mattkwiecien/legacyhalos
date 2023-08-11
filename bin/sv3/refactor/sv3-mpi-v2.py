#!/usr/bin/env python
"""MPI wrapper for the sv3 sample.
sv3-mpi --coadds
"""
import os, time, pdb
import numpy as np
from astropy.table import Table
from .sv3_builder import Sv3Builder
import legacyhalos.sv3 as sv3


def main():
    args = sv3.mpi_args()

    mpi_setup = Sv3Builder(args)
    mpi_setup.run_step()

    if args.coadds:
        from legacyhalos.mpi import call_custom_coadds

        samplefile = os.path.join(galaxydir, "{}-sample.fits".format(galaxy))

        if args.clobber or not os.path.isfile(samplefile):
            tmpfile = samplefile + ".tmp"
            Table(onegal).write(tmpfile, overwrite=True, format="fits")
            os.rename(tmpfile, samplefile)

        call_custom_coadds(
            onegal,
            galaxy,
            survey,
            run,
            radius_mosaic_arcsec,
            nproc=args.nproc,
            pixscale=args.pixscale,
            racolumn=RACOLUMN,
            deccolumn=DECCOLUMN,
            custom=True,
            apodize=False,
            unwise=args.unwise,
            force=args.force,
            plots=False,
            verbose=args.verbose,
            cleanup=args.cleanup,
            write_all_pickles=True,
            subsky_radii=subsky_radii,
            just_coadds=args.just_coadds,
            no_gaia=False,
            no_tycho=False,
            require_grz=True,
            debug=args.debug,
            logfile=logfile,
            write_wise_psf=False,
        )

    if args.ellipse:
        from legacyhalos.sv3 import call_ellipse

        input_ellipse = None

        call_ellipse(
            onegal,
            galaxy=galaxy,
            galaxydir=galaxydir,
            input_ellipse=input_ellipse,
            bands=["g", "r", "z"],
            refband="r",
            pixscale=args.pixscale,
            nproc=args.nproc,
            verbose=args.verbose,
            debug=args.debug,
            sky_tests=args.sky_tests,
            unwise=False,
            logfile=logfile,
            clobber=args.clobber,
        )

    if args.htmlplots:
        from legacyhalos.mpi import call_htmlplots
        from legacyhalos.sv3 import get_cosmology, read_multiband

        cosmo = get_cosmology()
        barlabel = "30 arcsec"
        barlen = np.ceil(30 / args.pixscale).astype(int)  # [pixels]

        call_htmlplots(
            onegal,
            galaxy,
            survey,
            pixscale=args.pixscale,
            nproc=args.nproc,
            verbose=args.verbose,
            debug=args.debug,
            clobber=args.clobber,
            logfile=logfile,
            zcolumn=ZCOLUMN,
            htmldir=htmldir,
            datadir=datadir,
            barlen=barlen,
            barlabel=barlabel,
            galaxy_id=onegal[GALAXYCOLUMN],
            radius_mosaic_arcsec=radius_mosaic_arcsec,
            cosmo=cosmo,
            just_coadds=args.just_coadds,
            get_galaxy_galaxydir=get_galaxy_galaxydir,
            read_multiband=read_multiband,
        )

    # Wait for all ranks to finish.
    print(f"Rank {rank} waiting at barrier.", flush=True)
    if comm is not None:
        comm.barrier()

    if rank == 0:
        print(
            "Finished {} {} at {} after {:.3f} minutes".format(
                ntodo,
                suffix.upper(),
                time.asctime(),
                (time.time() - tall) / 60,
            ),
            flush=True,
        )

        _, groups, _, _ = legacyhalos.sv3.missing_files(
            args, sample, size, clobber_overwrite=False
        )

        if len(groups) > 0:
            stilltodo = len(np.hstack(groups))
        else:
            stilltodo = 0

        print(
            "{} left to do: {} / {}.".format(suffix.upper(), stilltodo, ntodo),
            flush=True,
        )


if __name__ == "__main__":
    main()
