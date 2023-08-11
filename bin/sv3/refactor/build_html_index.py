from legacyhalos.sv3 import make_html
from legacyhalos.sv3 import (
    ZCOLUMN,
    DIAMCOLUMN,
    DECCOLUMN,
    RACOLUMN,
)
from .mpi_step import MpiStep


class BuildHtmlIndex(MpiStep):

    def __init__(self, args, sample):
        super.__init__(args, sample)
        self.is_serial = True

    def run(self):

        make_html(
            self.sample,
            survey=None,
            pixscale=self.args.pixscale,
            racolumn=RACOLUMN,
            deccolumn=DECCOLUMN,
            diamcolumn=DIAMCOLUMN,
            zcolumn=ZCOLUMN,
            nproc=self.args.nproc,
            clobber=self.args.clobber,
            makeplots=False,
            verbose=self.args.verbose,
            htmldir=self.args.htmldir,
            mpiargs=self.args,
        )
        return