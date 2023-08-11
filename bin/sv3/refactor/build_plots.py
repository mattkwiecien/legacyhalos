from legacyhalos.io import legacyhalos_data_dir, legacyhalos_html_dir
from legacyhalos.mpi import call_htmlplots
from legacyhalos.sv3 import get_cosmology, read_multiband
from legacyhalos.sv3 import ZCOLUMN, GALAXYCOLUMN
from .mpi_step import MpiStep
import numpy as np
from astropy.table import Table


class BuildPlots(MpiStep):
    def __init__(self, args, sample: Table):
        super.__init__(args, sample)

    def run(self):
        cosmo = get_cosmology()
        barlabel = "30 arcsec"
        barlen = np.ceil(30 / self.args.pixscale).astype(int)  # [pixels]

        call_htmlplots(
            self.onegal,
            self.galaxy,
            self.survey,
            pixscale=self.args.pixscale,
            nproc=self.args.nproc,
            verbose=self.args.verbose,
            debug=self.args.debug,
            clobber=self.args.clobber,
            logfile=self.logfile,
            zcolumn=ZCOLUMN,
            htmldir=legacyhalos_html_dir(),
            datadir=legacyhalos_data_dir(),
            barlen=barlen,
            barlabel=barlabel,
            galaxy_id=self.onegal[GALAXYCOLUMN],
            radius_mosaic_arcsec=self.radius_mosaic_arcsec,
            cosmo=cosmo,
            just_coadds=self.args.just_coadds,
            get_galaxy_galaxydir=get_galaxy_galaxydir,
            read_multiband=read_multiband,
        )

        return
