from .mpi_builder import MpiBuilder
import legacyhalos.sv3 as sv3
from astropy.table import Table

class Sv3Builder(MpiBuilder):
    
    def __init__(self):
        super.__init__()

    def _get_sample(self) -> Table:
        sample = sv3.read_sample(
            first = self.args.first,
            last = self.args.last,
            galaxylist = self.args.galaxylist,
            verbose = self.args.verbose,
            filenm = self.args.fname
        )
        return sample
    
    def _missing_files(self):
        return sv3.missing_files(self.args, self.sample, self.size)
