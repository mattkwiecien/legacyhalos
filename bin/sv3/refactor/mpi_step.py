from abc import ABC, abstractmethod
from .build_coadds import BuildCoadds
from .build_ellipse import BuildEllipse
from .build_html_index import BuildHtmlIndex
from .build_plots import BuildPlots
from .build_refcat import BuildRefcat
from astropy.table import Table
import os, time
import numpy as np
import legacypipe


class MpiStep(ABC):
    def __init__(self, args, sample: Table):
        self.args = args
        self.is_serial = False
        self.sample = sample

    def run_ranks(self, rank, comm, size):
        if rank == 0:
            suffix, groups, _, fail = self._missing_files()
        else:
            groups, suffix = [], ""

        if comm:
            groups = comm.bcast(groups, root=0)
            suffix = comm.bcast(suffix, root=0)

        if rank == 0:
            ntodo = len(np.hstack(groups))
            print(
                f"{suffix.upper()} left to do: {ntodo} / {len(self.sample)} divided across {size} rank(s).",
                flush=True,
            )

        # Wait for all ranks to catch up.
        if comm is not None:
            comm.barrier()

        my_groups = groups[rank]
        failures = fail[rank]

        if len(my_groups) == 0:
            # This MPI rank has no more work to do, so early exit.
            print(
                f"{suffix.upper()} for all {len(self.sample)} galaxies on rank {rank} are complete!",
                flush=True,
            )

            if rank > 0 or not self.args.count or not self.args.debug:
                return

            # If we're debugging, loop through and print the failures.
            if len(failures) == 0:
                return

            print(
                f"{suffix.upper()} failures: {len(failures)} / {len(self.sample)}",
                flush=True,
            )
            galaxy, galaxydir = get_galaxy_galaxydir(self.sample[failures])

            for ii, dd, diam in zip(failures, np.atleast_1d(galaxydir), self.sample[failures][diam_column]):
                print(f"  {ii} {dd} (r={diam:.3f} arcsec)", flush=True)

            return

        print(f"Rank {rank}: {len(my_groups)} galaxies left to do.", flush=True)

        if rank == 0 and self.args.count and self.args.debug:
            if len(failures) > 0:
                print(
                    f"{suffix.upper()} failures: {len(failures)} / {len(self.sample)}",
                    flush=True,
                )
                galaxy, galaxydir = get_galaxy_galaxydir(self.sample[failures])
                for ii, dd, diam in zip(
                    failures,
                    np.atleast_1d(galaxydir),
                    self.sample[failures][diam_column],
                ):
                    print(f"  {ii} {dd} (r={diam:.3f} arcsec)")

            todo = np.hstack(groups)
            if len(todo) > 0:
                print(
                    f"{suffix.upper()} todo: {len(todo)} / {len(self.sample)}",
                    flush=True,
                )
                galaxy, galaxydir = get_galaxy_galaxydir(self.sample[todo])
                for ii, dd, diam in zip(todo, np.atleast_1d(galaxydir), self.sample[todo][diam_column]):
                    print(f"  {ii} {dd} (r={diam:.3f} arcsec)")
            return

        # Loop on the remaining objects.
        print(
            f"Starting {len(my_groups)} {suffix.upper()} on rank {rank} with {self.args.nproc} cores on {time.asctime()}",
            flush=True,
        )

        tall = time.time()
        for count, ii in enumerate(my_groups):
            self.onegal = self.sample[ii]
            self.galaxy, self.galaxydir = get_galaxy_galaxydir(self.onegal)

            if not os.path.isdir(galaxydir):
                os.makedirs(galaxydir, exist_ok=True)

            print(
                "Rank {:03d} ({} / {}): {} (index {})".format(rank, count + 1, len(my_groups), galaxydir, ii),
                flush=True,
            )

            self.logfile = os.path.join(galaxydir, f"{galaxy}-{suffix}.log") if self.args.debug else None
            # Need the cluster "radius" to build the coadds.
            self.radius_mosaic_arcsec = self.onegal[diam_column] / 2  # radius [arcsec]
            self.subsky_radii = self.radius_mosaic_arcsec * np.array(
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

            self.lh_run = legacyhalos.io.get_run(self.onegal, racolumn=ra_column, deccolumn=dec_column)
            self.survey = legacypipe.runs.get_survey(self.lh_run, output_dir=galaxydir)

            self.run()

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

                _, groups, _, _ = legacyhalos.sv3.missing_files(self.args, self.sample, self.size, clobber_overwrite=False)

                if len(groups) > 0:
                    stilltodo = len(np.hstack(groups))
                else:
                    stilltodo = 0

                print(
                    "{} left to do: {} / {}.".format(suffix.upper(), stilltodo, ntodo),
                    flush=True,
                )

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def get_galaxy_galaxydir():
        pass


class StepFactory(object):
    @classmethod
    def get(self, args, sample) -> MpiStep:
        if args.coadds:
            return BuildCoadds(args, sample)
        if args.ellipse:
            return BuildEllipse(args, sample)
        if args.htmlplots:
            return BuildPlots(args, sample)
        if args.htmlindex:
            return BuildHtmlIndex(args, sample)
        if args.build_refcat:
            return BuildRefcat(args, sample)
        else:
            raise NotImplementedError()
