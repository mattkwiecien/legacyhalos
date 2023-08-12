from legacyhalos.sv3 import (
    RACOLUMN,
    DECCOLUMN,
    REFIDCOLUMN,
    MAGCOLUMN,
)
import fitsio, os
from astropy.table import Table
from .mpi_step import MpiStep
import numpy as np


class BuildRefcat(MpiStep):
    def __init__(self, args, sample: Table):
        super.__init__(args, sample)
        self.is_serial = True

    def run(self):
        # Build a reference catalog for use with the pipeline.

        ngal = len(self.sample)

        ref = Table()
        ref["ra"] = self.sample[RACOLUMN]
        ref["dec"] = self.sample[DECCOLUMN]
        ref["sga_id"] = self.sample[REFIDCOLUMN]
        ref["mag_leda"] = self.sample[MAGCOLUMN]
        ref["ba"] = np.repeat(1.0, ngal).astype("f4")  # fixed b/a
        ref["pa"] = np.repeat(0.0, ngal).astype("f4")  # fixed position angle
        ref["diam"] = np.repeat(10.0 / 60.0, ngal).astype("f4")  # fixed diameter = 10 arcsec [arcmin]

        # Directly get the path to the reference catalog from the environment.
        reffile = os.environ["LARGEGALAXIES_CAT"]
        kdreffile = reffile.replace(".fits", ".kd.fits")
        print("Writing {} galaxies to {}".format(ngal, reffile))

        hdr = fitsio.FITSHDR()
        hdrver = "R1"
        hdr["SGAVER"] = hdrver
        fitsio.write(reffile, ref.as_array(), header=hdr, clobber=True)

        print("Writing {}".format(kdreffile))
        cmd = "startree -i {} -o {} -T -P -k -n stars".format(reffile, kdreffile)
        print(cmd)
        _ = os.system(cmd)

        cmd = "modhead {} SGAVER {}".format(kdreffile, hdrver)
        _ = os.system(cmd)

        return
