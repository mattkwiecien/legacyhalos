from legacyhalos.sv3 import call_ellipse
from .mpi_step import MpiStep
from astropy.table import Table


class BuildEllipse(MpiStep):
    def __init__(self, args, sample: Table):
        super.__init__(args, sample)

    def run(self):
        call_ellipse(
            self.onegal,
            galaxy=self.galaxy,
            galaxydir=self.galaxydir,
            bands=["g", "r", "z"],
            refband="r",
            pixscale=self.args.pixscale,
            nproc=self.args.nproc,
            verbose=self.args.verbose,
            debug=self.args.debug,
            sky_tests=self.args.sky_tests,
            unwise=False,
            logfile=self.logfile,
            clobber=self.args.clobber,
        )
