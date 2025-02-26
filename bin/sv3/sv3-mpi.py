#!/usr/bin/env python
"""MPI wrapper for the sv3 sample.
sv3-mpi --coadds
"""
import os, time, pdb
import numpy as np
from astropy.table import Table


def main():
    """Top-level wrapper."""
    import legacyhalos.io
    import legacyhalos.sv3

    from legacypipe.runs import get_survey
    from legacyhalos.sv3 import (
        ZCOLUMN,
        RACOLUMN,
        DECCOLUMN,
        DIAMCOLUMN,
        GALAXYCOLUMN,
        REFIDCOLUMN,
        MAGCOLUMN,
    )
    from legacyhalos.sv3 import get_galaxy_galaxydir

    basedir = legacyhalos.io.legacyhalos_dir()
    datadir = legacyhalos.io.legacyhalos_data_dir()
    htmldir = legacyhalos.io.legacyhalos_html_dir()

    args = legacyhalos.sv3.mpi_args()

    if args.mpi:
        from mpi4py import MPI

        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()
        size = comm.Get_size()
    else:
        comm = None
        rank, size = 0, 1

    # Read and broadcast the sample.
    sample = None
    if rank == 0:
        print("$LEGACYHALOS_DIR={}".format(basedir))
        print("$LEGACYHALOS_DATA_DIR={}".format(datadir))
        print("$LEGACYHALOS_HTML_DIR={}".format(htmldir))
        sample = legacyhalos.sv3.read_sample(
            first=args.first,
            last=args.last,
            galaxylist=args.galaxylist,
            verbose=args.verbose,
            filenm=args.fname,
        )
        if len(sample) == 0:
            return

    if comm:
        sample = comm.bcast(sample, root=0)

    # Building the web-page and integrating the ellipse-fitting results work on
    # the full sample, so do that here and then return.

    # Refcat / htmlindex, serial stacks
    if rank == 0:
        refcat = "R1"
        if args.build_refcat:
            # Build a reference catalog for use with the pipeline.
            import fitsio

            ngal = len(sample)

            ref = Table()
            ref["ra"] = sample[RACOLUMN]
            ref["dec"] = sample[DECCOLUMN]
            ref["sga_id"] = sample[REFIDCOLUMN]
            ref["mag_leda"] = sample[MAGCOLUMN]
            ref["ba"] = np.repeat(1.0, ngal).astype("f4")  # fixed b/a
            ref["pa"] = np.repeat(0.0, ngal).astype("f4")  # fixed position angle
            ref["diam"] = np.repeat(10.0 / 60.0, ngal).astype("f4")  # fixed diameter = 10 arcsec [arcmin]

            # Directly get the path to the reference catalog from the environment.
            reffile = os.environ["LARGEGALAXIES_CAT"]
            kdreffile = reffile.replace(".fits", ".kd.fits")
            print("Writing {} galaxies to {}".format(ngal, reffile))

            hdr = fitsio.FITSHDR()
            hdrver = refcat
            hdr["SGAVER"] = hdrver
            fitsio.write(reffile, ref.as_array(), header=hdr, clobber=True)

            print("Writing {}".format(kdreffile))
            cmd = "startree -i {} -o {} -T -P -k -n stars".format(reffile, kdreffile)
            print(cmd)
            _ = os.system(cmd)

            cmd = "modhead {} SGAVER {}".format(kdreffile, hdrver)
            _ = os.system(cmd)

            return

        if args.htmlindex:
            legacyhalos.sv3.make_html(
                sample,
                survey=None,
                pixscale=args.pixscale,
                racolumn=RACOLUMN,
                deccolumn=DECCOLUMN,
                diamcolumn=DIAMCOLUMN,
                zcolumn=ZCOLUMN,
                nproc=args.nproc,
                clobber=args.clobber,
                makeplots=False,
                verbose=args.verbose,
                htmldir=args.htmldir,
                mpiargs=args,
            )
            return

        if args.build_catalog:
            print("Write me!")
            return

    # Determine how many more galaxies we need to analyze and divide them across
    # ranks.
    if rank == 0:
        suffix, groups, _, fail = legacyhalos.sv3.missing_files(args, sample, size)
    else:
        groups, suffix = [], ""

    if comm:
        groups = comm.bcast(groups, root=0)
        suffix = comm.bcast(suffix, root=0)

    if rank == 0:
        ntodo = len(np.hstack(groups))
        print(
            "{} left to do: {} / {} divided across {} rank(s).".format(suffix.upper(), ntodo, len(sample), size),
            flush=True,
        )

    # Wait for all ranks to catch up.
    if comm is not None:
        comm.barrier()

    if len(groups[rank]) == 0:
        # This MPI rank has no more work to do, so early exit.
        print(
            "{} for all {} galaxies on rank {} are complete!".format(suffix.upper(), len(sample), rank),
            flush=True,
        )

        # If we're debugging, loop through and print the failures.
        if rank == 0 and args.count and args.debug:
            if len(fail[rank]) == 0:
                if comm is not None:
                    comm.barrier()
                return

            print(
                "{} failures: {} / {}".format(suffix.upper(), len(fail[rank]), len(sample)),
                flush=True,
            )
            galaxy, galaxydir = get_galaxy_galaxydir(sample[fail[rank]])

            for ii, dd, diam in zip(fail[rank], np.atleast_1d(galaxydir), sample[fail[rank]][DIAMCOLUMN]):
                print("  {} {} (r={:.3f} arcsec)".format(ii, dd, diam), flush=True)

        if comm is not None:
            comm.barrier()
        return

    print("Rank {}: {} galaxies left to do.".format(rank, len(groups[rank])), flush=True)

    if rank == 0 and args.count and args.debug:
        if len(fail[rank]) > 0:
            print(
                "{} failures: {} / {}".format(suffix.upper(), len(fail[rank]), len(sample)),
                flush=True,
            )
            galaxy, galaxydir = get_galaxy_galaxydir(sample[fail[rank]])
            for ii, dd, diam in zip(fail[rank], np.atleast_1d(galaxydir), sample[fail[rank]][DIAMCOLUMN]):
                print("  {} {} (r={:.3f} arcsec)".format(ii, dd, diam))

        todo = np.hstack(groups)
        if len(todo) > 0:
            print(
                "{} todo: {} / {}".format(suffix.upper(), len(todo), len(sample)),
                flush=True,
            )
            galaxy, galaxydir = get_galaxy_galaxydir(sample[todo])
            for ii, dd, diam in zip(todo, np.atleast_1d(galaxydir), sample[todo][DIAMCOLUMN]):
                print("  {} {} (r={:.3f} arcsec)".format(ii, dd, diam))
        if comm is not None:
            comm.barrier()
        return

    # Loop on the remaining objects.
    print(
        "Starting {} {} on rank {} with {} cores on {}".format(
            len(groups[rank]), suffix.upper(), rank, args.nproc, time.asctime()
        ),
        flush=True,
    )

    tall = time.time()
    for count, ii in enumerate(groups[rank]):
        onegal = sample[ii]
        galaxy, galaxydir = get_galaxy_galaxydir(onegal)

        if not os.path.isdir(galaxydir):
            os.makedirs(galaxydir, exist_ok=True)

        print(
            "Rank {:03d} ({} / {}): {} (index {})".format(rank, count + 1, len(groups[rank]), galaxydir, ii),
            flush=True,
        )

        if args.debug:
            logfile = None
        else:
            if rank == 0:
                logfile = os.path.join(galaxydir, "{}-{}.log".format(galaxy, suffix))
            else:
                logfile = os.path.join(galaxydir, "{}-{}-rank{}.log".format(galaxy, suffix, rank))

        # Need the cluster "radius" to build the coadds.
        radius_mosaic_arcsec = onegal[DIAMCOLUMN] / 2  # radius [arcsec]
        subsky_radii = radius_mosaic_arcsec * np.array(
            [
                1.0,
                1.1,  # annulus 0
                1.2,
                1.3,  # annulus 1
                1.3,
                1.4,  # annulus 2
                1.4,
                1.5,
            ]
        )  # annulus 3

        run = legacyhalos.io.get_run(onegal, racolumn=RACOLUMN, deccolumn=DECCOLUMN)

        survey = get_survey(run, output_dir=galaxydir)

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
            try:
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
            except:
                print(f"Rank {rank} threw in ellipse, continuing to next barrier", flush=True)

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

        _, groups, _, _ = legacyhalos.sv3.missing_files(args, sample, size, clobber_overwrite=False)

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
