from abc import ABC, abstractmethod
import os, time
from .mpi_step import StepFactory, MpiStep
import legacyhalos
from astropy.table import Table
import numpy as np


class MpiBuilder(ABC):
    basedir: str = legacyhalos.io.legacyhalos_dir()
    datadir: str = legacyhalos.io.legacyhalos_data_dir()
    htmldir: str = legacyhalos.io.legacyhalos_html_dir()
    step: MpiStep = None
    args = None

    @property
    def diam_column(self):
        pass

    @property
    def ra_column(self):
        pass

    @property
    def dec_column(self):
        pass

    def __init__(self, args):
        self.args = args

        if args.mpi:
            from mpi4py import MPI

            self.comm = MPI.COMM_WORLD
            self.rank = self.comm.Get_rank()
            self.size = self.comm.Get_size()
        else:
            self.comm = None
            self.rank, self.size = 0, 1

        sample = self.get_sample()
        self.step = StepFactory.get(self.args, sample)

    def get_sample(self) -> Table:
        # Read and broadcast the sample.
        sample = None

        if self.rank == 0:
            print(f"$LEGACYHALOS_DIR={self.basedir}")
            print(f"$LEGACYHALOS_DATA_DIR={self.basedir}")
            print(f"$LEGACYHALOS_HTML_DIR={self.basedir}")
            sample = self._get_sample()

            if len(sample) == 0:
                return sample

        if self.comm:
            sample = self.comm.bcast(sample, root=0)

        return sample

    def run_step(self):
        sample = self.get_sample()

        if self.step.is_serial:
            if self.rank == 0:
                self.step.run(sample)
            else:
                print(f"Cannot run serial step in parallel. Rank {self.rank} exiting.")
            return

        self.step.run_ranks(self.rank, self.comm, self.size)

    @abstractmethod
    def _get_sample(self) -> Table:
        pass

    @abstractmethod
    def _missing_files(self):
        pass
