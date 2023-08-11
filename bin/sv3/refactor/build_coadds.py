from legacyhalos.mpi import call_custom_coadds
from legacyhalos.sv3 import RACOLUMN, DECCOLUMN
import os
from astropy.table import Table
from .mpi_step import MpiStep


class BuildCoadds(MpiStep):
    def __init__(self, args, sample: Table):
        super.__init__(args, sample)

    def run(self):
        samplefile = os.path.join(self.galaxydir, "{}-sample.fits".format(self.galaxy))

        if self.args.clobber or not os.path.isfile(samplefile):
            tmpfile = samplefile + ".tmp"
            Table(self.onegal).write(tmpfile, overwrite=True, format="fits")
            os.rename(tmpfile, samplefile)

        call_custom_coadds(
            self.onegal,
            self.galaxy,
            self.survey,
            self.lh_run,
            self.radius_mosaic_arcsec,
            nproc=self.args.nproc,
            pixscale=self.args.pixscale,
            racolumn=RACOLUMN,
            deccolumn=DECCOLUMN,
            custom=True,
            apodize=False,
            unwise=self.args.unwise,
            force=self.args.force,
            plots=False,
            verbose=self.args.verbose,
            cleanup=self.args.cleanup,
            write_all_pickles=True,
            subsky_radii=self.subsky_radii,
            just_coadds=self.args.just_coadds,
            no_gaia=False,
            no_tycho=False,
            require_grz=True,
            debug=self.args.debug,
            logfile=self.logfile,
            write_wise_psf=False,
        )
