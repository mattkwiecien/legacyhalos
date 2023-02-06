from abc import ABC, abstractmethod
import os
import numpy as np
from astropy.table import Table

class MpiStep(ABC):

    def __init__(self, args):
        self.args = args

    @abstractmethod
    def run(self, **kwargs):
        pass

class StepGenerator(object):

    @classmethod
    def get(self, args) -> MpiStep:
        if args.coadds:
            return BuildCoadds(args)
        if args.ellipse:
            return BuildEllipse(args)
        if args.htmlplots:
            return BuildPlots(args)
        if args.htmlindex:
            return BuildHtmlIndex(args)
        if args.build_refcat:
            return BuildRefcat(args)
        else:
            raise NotImplementedError()
 

class BuildRefcat(MpiStep):
    
    def run(self, **kwargs):
        # Build a reference catalog for use with the pipeline.
        from legacyhalos.sv3 import (
            RACOLUMN,
            DECCOLUMN,
            REFIDCOLUMN,
            MAGCOLUMN,
        )
        import fitsio
        sample = kwargs["sample"]

        ngal = len(sample)

        ref = Table()
        ref["ra"] = sample[RACOLUMN]
        ref["dec"] = sample[DECCOLUMN]
        ref["sga_id"] = sample[REFIDCOLUMN]
        ref["mag_leda"] = sample[MAGCOLUMN]
        ref["ba"] = np.repeat(1.0, ngal).astype("f4")  # fixed b/a
        ref["pa"] = np.repeat(0.0, ngal).astype(
            "f4"
        )  # fixed position angle
        ref["diam"] = np.repeat(10.0 / 60.0, ngal).astype(
            "f4"
        )  # fixed diameter = 10 arcsec [arcmin]

        # Directly get the path to the reference catalog from the environment.
        reffile = os.environ["LARGEGALAXIES_CAT"]
        kdreffile = reffile.replace(".fits", ".kd.fits")
        print("Writing {} galaxies to {}".format(ngal, reffile))

        hdr = fitsio.FITSHDR()
        hdrver = "R1"
        hdr["SGAVER"] = hdrver
        fitsio.write(reffile, ref.as_array(), header=hdr, clobber=True)

        print("Writing {}".format(kdreffile))
        cmd = "startree -i {} -o {} -T -P -k -n stars".format(
            reffile, kdreffile
        )
        print(cmd)
        _ = os.system(cmd)

        cmd = "modhead {} SGAVER {}".format(kdreffile, hdrver)
        _ = os.system(cmd)

        return


class BuildCoadds(MpiStep):

    def run(self, **kwargs):
        from legacyhalos.mpi import call_custom_coadds
        from legacyhalos.sv3 import (
            RACOLUMN,
            DECCOLUMN
        )
        galaxydir, galaxy = kwargs["galaxydir"], kwargs["galaxy"]
        samplefile = os.path.join(galaxydir, "{}-sample.fits".format(galaxy))

        if self.args.clobber or not os.path.isfile(samplefile):
            tmpfile = samplefile + ".tmp"
            onegal = kwargs["onegal"]
            Table(onegal).write(tmpfile, overwrite=True, format="fits")
            os.rename(tmpfile, samplefile)

        survey, run, logfile, radius_mosaic_arcsec, subsky_radii = (
            kwargs["survey"], kwargs["run"], kwargs["logfile"], kwargs["radius_mosaic_arcsec"], kwargs["subsky_radii"]
        )

        call_custom_coadds(
            onegal,
            galaxy,
            survey,
            run,
            radius_mosaic_arcsec,
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
            subsky_radii=subsky_radii,
            just_coadds=self.args.just_coadds,
            no_gaia=False,
            no_tycho=False,
            require_grz=True,
            debug=self.args.debug,
            logfile=logfile,
            write_wise_psf=False,
        )
        return

class BuildEllipse(MpiStep):
    def run(self, **kwargs):
        from legacyhalos.sv3 import call_ellipse

        onegal, galaxy, galaxydir, input_ellipse, logfile = (
            kwargs["onegal"], kwargs["galaxy"], kwargs["galaxydir"], kwargs["input_ellipse"], kwargs["logfile"]
        )

        call_ellipse(
            onegal,
            galaxy=galaxy,
            galaxydir=galaxydir,
            input_ellipse=input_ellipse,
            bands=["g", "r", "z"],
            refband="r",
            pixscale=self.args.pixscale,
            nproc=self.args.nproc,
            verbose=self.args.verbose,
            debug=self.args.debug,
            sky_tests=self.args.sky_tests,
            unwise=False,
            logfile=logfile,
            clobber=self.args.clobber,
        )

        return


class BuildPlots(MpiStep):
    def run(self, **kwargs):
        from legacyhalos.io import legacyhalos_data_dir, legacyhalos_html_dir
        from legacyhalos.mpi import call_htmlplots
        from legacyhalos.sv3 import get_cosmology, read_multiband
        from legacyhalos.sv3 import (
            ZCOLUMN,
            GALAXYCOLUMN,
        )

        cosmo = get_cosmology()
        barlabel = "30 arcsec"
        barlen = np.ceil(30 / self.args.pixscale).astype(int)  # [pixels]
        
        onegal, galaxy, survey, logfile = (
            kwargs["onegal"], kwargs["galaxy"], kwargs["survey"], kwargs["logfile"]
        )

        get_galaxy_galaxydir, radius_mosaic_arcsec = (
            kwargs["get_galaxy_galaxydir"], kwargs["radius_mosaic_arcsec"]
        )
        
        call_htmlplots(
            onegal,
            galaxy,
            survey,
            pixscale=self.args.pixscale,
            nproc=self.args.nproc,
            verbose=self.args.verbose,
            debug=self.args.debug,
            clobber=self.args.clobber,
            logfile=logfile,
            zcolumn=ZCOLUMN,
            htmldir=legacyhalos_html_dir(),
            datadir=legacyhalos_data_dir(),
            barlen=barlen,
            barlabel=barlabel,
            galaxy_id=onegal[GALAXYCOLUMN],
            radius_mosaic_arcsec=radius_mosaic_arcsec,
            cosmo=cosmo,
            just_coadds=self.args.just_coadds,
            get_galaxy_galaxydir=get_galaxy_galaxydir,
            read_multiband=read_multiband,
        )

        return


class BuildHtmlIndex(MpiStep):
    def run(self, **kwargs):
        from legacyhalos.sv3 import make_html
        from legacyhalos.sv3 import (
            ZCOLUMN,
            DIAMCOLUMN,
            DECCOLUMN,
            RACOLUMN,
        )
        sample = kwargs["sample"]
        make_html(
            sample,
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
