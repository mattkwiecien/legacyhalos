from astropy.stats import sigma_clipped_stats
import tractor
from astrometry.util.fits import fits_table
from astrometry.util.multiproc import multiproc
from astrometry.util.miscutils import estimate_mode
from legacypipe.catalog import read_fits_catalog


def _forced_phot(args):
    """Wrapper function for the multiprocessing."""
    return forced_phot(*args)


def forced_phot(newtims, custom_srcs, band):
    """Perform forced photometry, returning the bandpass, the (newly optimized)
    flux, and the (new) inverse variance flux (all in nanomaggies).

    """
    bandtims = [tim for tim in newtims if tim.band == band]
    tr = tractor.Tractor(bandtims, custom_srcs)
    tr.freezeParamsRecursive("*")
    tr.thawPathsTo(band)
    R = tr.optimize_forced_photometry(
        minsb=0,
        mindlnp=1.0,
        sky=False,
        fitstats=True,
        variance=True,
        shared_params=False,
        wantims=False,
    )
    return (band, np.array(tr.getParams()), R.IV)


def isolate_central(cat, wcs, psf_sigma=1.1, radius_search=5.0, centrals=True):
    """Isolate the central galaxy.

    radius_mosaic in arcsec
    """
    from astrometry.libkd.spherematch import match_radec
    from legacyhalos.mge import find_galaxy

    if type(wcs) is not tractor.wcs.ConstantFitsWcs:
        wcs = tractor.wcs.ConstantFitsWcs(wcs)

    racen, deccen = wcs.wcs.crval
    _, width = wcs.wcs.shape
    radius_mosaic = width * wcs.wcs.pixel_scale() / 2  # [arcsec]

    keep = np.ones(len(cat)).astype(bool)
    if centrals:
        # Build a model image with all the sources whose centroids are within
        # the inner XX% of the mosaic and then "find" the central galaxy.
        m1, m2, d12 = match_radec(cat.ra, cat.dec, racen, deccen, 0.5 * radius_mosaic / 3600.0, nearest=False)
        srcs = read_fits_catalog(cat[m1], fluxPrefix="")
        mod = legacyhalos.misc.srcs2image(srcs, wcs, psf_sigma=psf_sigma)
        if np.sum(np.isnan(mod)) > 0:
            print(
                "Problem rendering model image of galaxy {}".format(galaxy),
                flush=True,
                file=log,
            )

        mgegalaxy = find_galaxy(mod, nblob=1, binning=3, quiet=True)

        # Now use the ellipse parameters to get a better list of the model
        # sources in and around the central, and remove the largest ones.
        if False:
            majoraxis = mgegalaxy.majoraxis
            these = legacyhalos.misc.ellipse_mask(
                width / 2,
                width / 2,
                majoraxis,
                majoraxis * (1 - mgegalaxy.eps),
                np.radians(mgegalaxy.theta - 90),
                cat.bx,
                cat.by,
            )

            galrad = np.max(np.array((cat.shapedev_r, cat.shapeexp_r)), axis=0)
            # galrad = (cat.fracdev * cat.shapedev_r + (1-cat.fracdev) * cat.shapeexp_r) # type-weighted radius
            these *= galrad > 3
        else:
            these = np.zeros(len(cat), dtype=bool)

        # Also add the sources nearest to the central coordinates.
        m1, m2, d12 = match_radec(cat.ra, cat.dec, racen, deccen, radius_search / 3600.0, nearest=False)
        if len(m1) > 0:
            these[m1] = True

        if np.sum(these) > 0:
            keep[these] = False
        else:
            m1, m2, d12 = match_radec(cat.ra, cat.dec, racen, deccen, radius_search / 3600.0, nearest=False)
            if len(d12) > 0:
                keep = ~np.isin(cat.objid, cat[m1].objid)
    else:
        # Find and remove all the objects within XX arcsec of the target
        # coordinates.
        m1, m2, d12 = match_radec(cat.ra, cat.dec, racen, deccen, radius_search / 3600.0, nearest=False)
        if len(d12) > 0:
            keep = ~np.isin(cat.objid, cat[m1].objid)
        else:
            print(
                "No matching galaxies found -- probably not what you wanted.",
                flush=True,
                file=log,
            )
            # raise ValueError

    return keep


def _build_objmask(img, ivar, skypix, boxcar=5, boxsize=1024):
    """Build an object mask by doing a quick estimate of the sky background on a
    given CCD.

    """
    from scipy.ndimage.morphology import binary_dilation
    from scipy.ndimage.filters import uniform_filter

    from tractor.splinesky import SplineSky

    # Get an initial guess of the sky using the mode, otherwise the median.
    skysig1 = 1.0 / np.sqrt(np.median(ivar[skypix]))
    # try:
    #    skyval = estimate_mode(img[skypix], raiseOnWarn=True)
    # except:
    #    skyval = np.median(img[skypix])
    skyval = np.median(img[skypix])

    # Mask objects in a boxcar-smoothed (image - initial sky model), smoothed by
    # a boxcar filter before cutting pixels above the n-sigma threshold.
    if min(img.shape) / boxsize < 4:  # handle half-DECam chips
        boxsize /= 2

    # Compute initial model...
    skyobj = SplineSky.BlantonMethod(img - skyval, skypix, boxsize)
    skymod = np.zeros_like(img)
    skyobj.addTo(skymod)

    bskysig1 = skysig1 / boxcar  # sigma of boxcar-smoothed image.
    objmask = np.abs(uniform_filter(img - skyval - skymod, size=boxcar, mode="constant") > (3 * bskysig1))
    objmask = binary_dilation(objmask, iterations=3)

    return objmask


def _get_skystats(img, ivarmask, refmask, galmask, objmask, skymask, tim):
    """Low-level function to get the sky statistics given an image and the pixels of
    interest.

    """
    log = None
    skypix = ((ivarmask * 1 + refmask * 1 + galmask * 1 + objmask * 1) == 0) * skymask

    # If there are no sky pixels then use the statistics from the pipeline sky
    # map.  For example, the algorithm here can fail in and around bright stars.
    if np.sum(skypix) == 0:
        print("No viable sky pixels; using pipeline sky statistics!", file=log)
        pipesky = np.zeros_like(img)
        tim.sky.addTo(pipesky)
        skymean, skymedian, skysig = sigma_clipped_stats(pipesky, mask=~skymask, sigma=3.0)
        try:
            skymode = estimate_mode(pipesky[skymask], raiseOnWarn=True).astype("f4")
        except:
            print("Warning: sky mode estimation failed!", file=log)
            skymode = np.array(0.0).astype("f4")
    else:
        skypix = ((ivarmask * 1 + galmask * 1 + objmask * 1) == 0) * skymask

        try:
            skymean, skymedian, skysig = sigma_clipped_stats(img, mask=~skypix, sigma=3.0)
        except:
            print("Warning: sky statistic estimates failed!", file=log)
            skymean, skymedian, skysig = 0.0, 0.0, 0.0
        # skysig = 1.0 / np.sqrt(np.median(ivar[skypix]))
        # skymedian = np.median(img[skypix])
        try:
            skymode = estimate_mode(img[skypix], raiseOnWarn=True).astype("f4")
        except:
            print("Warning: sky mode estimation failed!", file=log)
            skymode = np.array(0.0).astype("f4")

    return skymean, skymedian, skysig, skymode


def _custom_sky(args):
    """Wrapper function for the multiprocessing."""
    return custom_sky(*args)


def custom_sky(survey, brickname, brickwcs, onegal, radius_mask_arcsec, apodize, sky_annulus, ccd):
    """Perform custom sky-subtraction on a single CCD."""
    from astrometry.util.resample import resample_with_wcs
    from legacypipe.reference import get_reference_sources
    from legacypipe.oneblob import get_inblob_map

    log = None

    # Preliminary stuff: read the full-field tim and parse it.
    im = survey.get_image_object(ccd)
    hdr = im.read_image_header()
    hdr.delete("INHERIT")
    hdr.delete("EXTVER")

    print(
        im,
        im.band,
        "exptime",
        im.exptime,
        "propid",
        ccd.propid,
        "seeing {:.2f}".format(ccd.fwhm * im.pixscale),
        "object",
        getattr(ccd, "object", None),
        file=log,
    )

    radius_mask = np.round(radius_mask_arcsec / im.pixscale).astype("int")  # [pixels]

    tim = im.get_tractor_image(splinesky=True, subsky=False, hybridPsf=True, normalizePsf=True, apodize=apodize)

    targetwcs, bands = tim.subwcs, tim.band
    H, W = targetwcs.shape
    H, W = np.int(H), np.int(W)

    img = tim.getImage()
    ivar = tim.getInvvar()

    # Next, read the splinesky model (for comparison purposes).
    T = fits_table(im.merged_splineskyfn)
    (I,) = np.nonzero((T.expnum == im.expnum) * np.array([c.strip() == im.ccdname for c in T.ccdname]))
    if len(I) != 1:
        print("Multiple splinesky models!", file=log)
        return 0
    splineskytable = T[I]

    # Third, build up a mask consisting of (1) masked pixels in the inverse
    # variance map; (2) known bright stars; (3) astrophysical sources in the
    # image; and (4) the object of interest.
    ivarmask = ivar <= 0

    refs, _ = get_reference_sources(
        survey,
        targetwcs,
        im.pixscale,
        ["r"],
        tycho_stars=True,
        gaia_stars=True,
        large_galaxies=False,
        star_clusters=False,
    )
    refmask = get_inblob_map(targetwcs, refs) != 0

    # http://stackoverflow.com/questions/8647024/how-to-apply-a-disc-shaped-mask-to-a-numpy-array
    _, x0, y0 = targetwcs.radec2pixelxy(onegal["RA"], onegal["DEC"])
    xcen, ycen = np.round(x0 - 1).astype("int"), np.round(y0 - 1).astype("int")
    ymask, xmask = np.ogrid[-ycen : H - ycen, -xcen : W - xcen]
    galmask = (xmask**2 + ymask**2) <= radius_mask**2

    skypix = (ivarmask * 1 + refmask * 1 + galmask * 1) == 0
    objmask = _build_objmask(img, ivar, skypix)

    # Next, optionally define an annulus of sky pixels centered on the object of
    # interest.
    if sky_annulus:
        skyfactor_in = np.array([0.5, 0.5, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 3.0], dtype="f4")
        skyfactor_out = np.array([1.0, 2.0, 2.0, 3.0, 4.0, 3.0, 4.0, 5.0, 5.0], dtype="f4")
        # skyrow_use = (skyfactor_in == 2.0) * (skyfactor_out == 4.0)
        skyrow_use = np.zeros(len(skyfactor_in)).astype(bool)
        skyrow_use[7] = True

        nsky = len(skyfactor_in)
        skymean = np.zeros(nsky, dtype="f4")
        skymedian, skysig, skymode = (
            np.zeros_like(skymean),
            np.zeros_like(skymean),
            np.zeros_like(skymean),
        )
        for ii in range(nsky):
            inmask = (xmask**2 + ymask**2) <= skyfactor_in[ii] * radius_mask**2
            outmask = (xmask**2 + ymask**2) <= skyfactor_out[ii] * radius_mask**2
            skymask = (outmask * 1 - inmask * 1 - galmask * 1) == 1
            # There can be no sky pixels if the CCD is on the periphery.
            if np.sum(skymask) == 0:
                skymask = np.ones_like(img).astype(bool)

            skymean1, skymedian1, skysig1, skymode1 = _get_skystats(img, ivarmask, refmask, galmask, objmask, skymask, tim)
            skymean[ii], skymedian[ii], skysig[ii], skymode[ii] = (
                skymean1,
                skymedian1,
                skysig1,
                skymode1,
            )
    else:
        nsky = 1
        skyfactor_in, skyfactor_out = np.array(0.0, dtype="f4"), np.array(0.0, dtype="f4")
        skyrow_use = np.array(False)

        skymask = np.ones_like(img).astype(bool)
        skymean, skymedian, skysig, skymode = _get_skystats(img, ivarmask, refmask, galmask, objmask, skymask, tim)

    # Final steps:

    # (1) Build the final bit-mask image.
    #   0    =
    #   2**0 = refmask  - reference stars and galaxies
    #   2**1 = objmask  - threshold-detected objects
    #   2**2 = galmask  - central galaxy & system
    mask = np.zeros_like(img).astype(np.int16)
    # mask[ivarmask] += 2**0
    mask[refmask] += 2**0
    mask[objmask] += 2**1
    mask[galmask] += 2**2

    # (2) Resample the mask onto the final mosaic image.
    HH, WW = brickwcs.shape
    comask = np.zeros((HH, WW), np.int16)
    try:
        Yo, Xo, Yi, Xi, _ = resample_with_wcs(brickwcs, targetwcs)
        comask[Yo, Xo] = mask[Yi, Xi]
    except:
        pass

    # (3) Add the sky values and also the central pixel coordinates of the object of
    # interest (so we won't need the WCS object downstream, in QA).

    # for card, value in zip(('SKYMODE', 'SKYMED', 'SKYMEAN', 'SKYSIG'),
    #                       (skymode, skymed, skymean, skysig)):
    #    hdr.add_record(dict(name=card, value=value))
    hdr.add_record(dict(name="CAMERA", value=im.camera))
    hdr.add_record(dict(name="EXPNUM", value=im.expnum))
    hdr.add_record(dict(name="CCDNAME", value=im.ccdname))
    hdr.add_record(dict(name="RADMASK", value=np.array(radius_mask, dtype="f4"), comment="pixels"))
    hdr.add_record(dict(name="XCEN", value=x0 - 1, comment="zero-indexed"))
    hdr.add_record(dict(name="YCEN", value=y0 - 1, comment="zero-indexed"))

    customsky = fits_table()
    customsky.skymode = np.array(skymode)
    customsky.skymedian = np.array(skymedian)
    customsky.skymean = np.array(skymean)
    customsky.skysig = np.array(skysig)
    customsky.skyfactor_in = np.array(skyfactor_in)
    customsky.skyfactor_out = np.array(skyfactor_out)
    customsky.skyrow_use = np.array(skyrow_use)
    # customsky.xcen = np.repeat(x0 - 1, nsky) # 0-indexed
    # customsky.ycen = np.repeat(y0 - 1, nsky)
    customsky.to_np_arrays()

    # (4) Pack into a dictionary and return.
    out = dict()
    ext = "{}-{}-{}".format(im.camera, im.expnum, im.ccdname.lower().strip())
    # ext = '{}-{:02d}-{}'.format(im.name, im.hdu, im.band)
    out["{}-mask".format(ext)] = mask
    out["{}-image".format(ext)] = img
    out["{}-splinesky".format(ext)] = splineskytable
    out["{}-header".format(ext)] = hdr
    out["{}-customsky".format(ext)] = customsky
    out["{}-comask".format(ext)] = comask

    return out


def obsolete_custom_coadds(
    onegal,
    galaxy=None,
    survey=None,
    radius_mosaic=None,
    radius_mask=None,
    nproc=1,
    pixscale=0.262,
    log=None,
    apodize=False,
    plots=False,
    verbose=False,
    cleanup=True,
    write_ccddata=False,
    sky_annulus=True,
    centrals=True,
    doforced_phot=True,
):
    """Build a custom set of coadds for a single galaxy, with a custom mask and sky
    model.

    radius_mosaic and radius_mask in arcsec

    centrals - if this is the centrals project (legacyhalos or HSC) then deal
      with the central with dedicated code.

    """
    import copy
    import tractor

    import legacypipe.runbrick
    from legacypipe.runbrick import stage_tims, stage_refs, stage_outliers, stage_halos
    from legacypipe.runbrick import _get_mod
    from legacypipe.coadds import make_coadds, write_coadd_images
    from legacypipe.survey import get_rgb, imsave_jpeg
    from legacypipe.image import DQ_BITS

    if survey is None:
        from legacypipe.survey import LegacySurveyData

        survey = LegacySurveyData()

    if galaxy is None:
        galaxy = "galaxy"

    if plots:
        from astrometry.util.plotutils import PlotSequence

        ps = PlotSequence("qa-{}".format(brickname))
    else:
        ps = None

    mp = multiproc(nthreads=nproc)

    if radius_mask is None:
        radius_mask = radius_mosaic
        radius_search = 5.0  # [arcsec]
    else:
        radius_search = radius_mask

    # Parse the runbrick keyword arguments in order to get all the correct
    # defaults, etc.
    ra, dec = onegal["RA"], onegal["DEC"]
    brickname = custom_brickname(ra, dec)
    width = _mosaic_width(radius_mosaic, pixscale)
    opt, _ = legacypipe.runbrick.get_parser().parse_known_args()
    opt.ra = ra
    opt.dec = dec
    opt.W = width
    opt.H = width
    opt.threads = nproc
    opt.pixscale = pixscale
    opt.brickname = brickname
    opt.bands = "g,r,z"
    opt.mp = mp
    opt.plots = plots
    opt.ps = ps
    opt.apodize = apodize
    opt.do_calibs = False
    opt.subsky = False
    opt.tycho_stars = False
    opt.gaia_stars = False
    opt.large_galaxies = False
    opt.outlier_mask_file = os.path.join(survey.output_dir, "{}-outlier-mask.fits.fz".format(galaxy))

    _, kwargs = legacypipe.runbrick.get_runbrick_kwargs(**vars(opt))

    # tims --> refs --> outliers --> halos
    P = stage_tims(survey=survey, **kwargs)
    P.update(kwargs)

    Q = stage_refs(**P)
    Q.update(P)
    Q.update(kwargs)

    R = stage_outliers(**Q)
    R.update(Q)
    R.update(P)
    R.update(kwargs)

    S = stage_halos(**R)
    S.update(kwargs)

    # [1] Initialize the "tims" stage of the pipeline, returning a
    # dictionary with the following keys:

    #   ['brickid', 'target_extent', 'version_header', 'targetrd',
    #    'brickname', 'pixscale', 'bands', 'survey', 'brick', 'ps',
    #    'H', 'ccds', 'W', 'targetwcs', 'tims']

    def call_stage_tims():
        """Note that we return just the portion of the CCDs centered on the galaxy, and
        that we turn off sky-subtraction.

        """
        return stage_tims(
            ra=onegal["RA"],
            dec=onegal["DEC"],
            brickname=brickname,
            survey=survey,
            W=width,
            H=width,
            pixscale=pixscale,
            mp=mp,
            normalizePsf=True,
            pixPsf=True,
            hybridPsf=True,
            splinesky=True,
            subsky=False,  # note!
            # depth_cut=False, rex=True,  OBSOLETE!
            apodize=apodize,
            do_calibs=False,
            unwise_dir=unwise_dir,
            plots=plots,
            ps=ps,
        )

    if log:
        with redirect_stdout(log), redirect_stderr(log):
            P = call_stage_tims()
    else:
        P = call_stage_tims()

    tims, brickwcs = P["tims"], P["targetwcs"]
    bands, version_header = P["bands"], P["version_header"]
    del P

    # Read and apply the outlier masks.
    outliersfile = os.path.join(survey.output_dir, "{}-outlier-mask.fits.fz".format(galaxy))
    if not os.path.isfile(outliersfile):
        print("Missing outliers masks {}".format(outliersfile), flush=True, file=log)
        return 0

    outliers = fitsio.FITS(outliersfile)
    for tim in tims:
        ext = "{}-{}-{}".format(tim.imobj.camera, tim.imobj.expnum, tim.imobj.ccdname.lower().strip())
        if ext in outliers:
            mask = outliers[ext].read()
            maskhdr = outliers[ext].read_header()
            tim.dq |= (mask > 0) * DQ_BITS["outlier"]
            tim.inverr[mask > 0] = 0.0
        else:
            print(
                "Warning: extension {} not found in image {}".format(ext, outliersfile),
                flush=True,
                file=log,
            )

    # [2] Derive the custom mask and sky background for each (full) CCD and
    # write out a MEF -custom-mask.fits.gz file.
    skyargs = [(survey, brickname, brickwcs, onegal, radius_mask, apodize, sky_annulus, _ccd) for _ccd in survey.ccds]
    result = mp.map(_custom_sky, skyargs)
    # result = list( zip( *mp.map(_custom_sky, args) ) )
    sky = dict()
    [sky.update(res) for res in result]
    del result

    # Write out the "coadd" mask.
    cokeys = [key for key in sky.keys() if "comask" in key]
    _comask = np.array([sky[cokey] for cokey in cokeys])

    comask = np.bitwise_or.reduce(_comask, axis=0)
    hdr = fitsio.FITSHDR()
    brickwcs.add_to_header(hdr)
    hdr.delete("IMAGEW")
    hdr.delete("IMAGEH")

    maskfile = os.path.join(survey.output_dir, "{}-custom-mask-grz.fits.gz".format(galaxy))
    fitsio.write(maskfile, comask, header=hdr, clobber=True)
    print("Writing {}".format(maskfile), flush=True, file=log)
    del comask

    skyfile = os.path.join(survey.output_dir, "{}-pipeline-sky.fits".format(galaxy))
    print("Writing {}".format(skyfile), flush=True, file=log)
    if os.path.isfile(skyfile):
        os.remove(skyfile)
    for ii, ccd in enumerate(survey.ccds):
        im = survey.get_image_object(ccd)
        ext = "{}-{}-{}".format(im.camera, im.expnum, im.ccdname.lower().strip())
        sky["{}-splinesky".format(ext)].write_to(skyfile, append=ii > 0, extname=ext)

    skyfile = os.path.join(survey.output_dir, "{}-custom-sky.fits".format(galaxy))
    print("Writing {}".format(skyfile), flush=True, file=log)
    if os.path.isfile(skyfile):
        os.remove(skyfile)
    for ii, ccd in enumerate(survey.ccds):
        im = survey.get_image_object(ccd)
        ext = "{}-{}-{}".format(im.camera, im.expnum, im.ccdname.lower().strip())
        sky["{}-customsky".format(ext)].write_to(skyfile, append=ii > 0, extname=ext, header=sky["{}-header".format(ext)])

    # Optionally write out separate CCD-level files with the images/data and
    # individual masks (converted to unsigned integer).  These are still pretty
    # big and I'm not sure we will ever need them.  Keep the code here for
    # legacy value but don't write out.
    if write_ccddata:
        ccdfile = os.path.join(survey.output_dir, "{}-custom-ccdmask-grz.fits.gz".format(galaxy))
        print("Writing {}".format(ccdfile), flush=True, file=log)
        if os.path.isfile(ccdfile):
            os.remove(ccdfile)
        with fitsio.FITS(ccdfile, "rw") as ff:
            for ii, ccd in enumerate(survey.ccds):
                im = survey.get_image_object(ccd)
                ext = "{}-{}-{}".format(im.camera, im.expnum, im.ccdname.lower().strip())
                hdr = sky["{}-header".format(ext)]
                ff.write(sky["{}-mask".format(ext)], extname=ext, header=hdr)

        # These are the actual images, which results in a giant file.  Keeping
        # the code here for legacy purposes but I'm not sure we should ever
        # write it out.
        if False:
            ccdfile = os.path.join(survey.output_dir, "{}-ccddata-grz.fits.fz".format(galaxy))
            print("Writing {}".format(ccdfile), flush=True, file=log)
            if os.path.isfile(ccdfile):
                os.remove(ccdfile)
            with fitsio.FITS(ccdfile, "rw") as ff:
                for ii, ccd in enumerate(survey.ccds):
                    im = survey.get_image_object(ccd)
                    ext = "{}-{}-{}".format(im.camera, im.expnum, im.ccdname.lower().strip())
                    hdr = sky["{}-header".format(ext)]
                    ff.write(
                        sky["{}-image".format(ext)].astype("f4"),
                        extname=ext,
                        header=hdr,
                    )

    # [3] Modify each tim by subtracting our new estimate of the sky. Then
    # sky-subtract the pipeline_tims so we can build coadds without the central,
    # below.
    custom_tims, pipeline_tims = [], []
    for tim in tims:
        custom_tim = copy.deepcopy(tim)
        image = custom_tim.getImage()
        ext = "{}-{}-{}".format(
            custom_tim.imobj.camera,
            custom_tim.imobj.expnum,
            custom_tim.imobj.ccdname.lower().strip(),
        )

        customsky = sky["{}-customsky".format(ext)]
        newsky = customsky.skymedian[customsky.skyrow_use]
        # newsky = sky['{}-header'.format(ext)]['SKYMED']

        custom_tim.setImage(image - newsky)
        custom_tim.sky = tractor.sky.ConstantSky(0)
        custom_tims.append(custom_tim)
        del custom_tim

        pipeline_tim = copy.deepcopy(tim)
        pipesky = np.zeros_like(tim.getImage())
        pipeline_tim.sky.addTo(pipesky)
        pipeline_tim.setImage(image - pipesky)
        pipeline_tim.sky = tractor.sky.ConstantSky(0)
        pipeline_tims.append(pipeline_tim)
        del pipeline_tim
    del sky, tims

    # [4] Read the pipeline Tractor catalog and update the individual-object
    # photometry measured from the custom sky-subtracted CCDs.
    tractorfile = os.path.join(survey.output_dir, "{}-pipeline-tractor.fits".format(galaxy))
    if not os.path.isfile(tractorfile):
        print("Missing Tractor catalog {}".format(tractorfile), flush=True, file=log)
        return 0
    pipeline_cat = fits_table(tractorfile)
    print(
        "Read {} sources from {}".format(len(pipeline_cat), tractorfile),
        flush=True,
        file=log,
    )

    pipeline_srcs = read_fits_catalog(pipeline_cat, fluxPrefix="")
    custom_srcs = [src.copy() for src in pipeline_srcs]

    custom_cat = pipeline_cat.copy()
    if doforced_phot:
        t0 = time.time()
        print(
            "Performing forced photometry on the custom sky-subtracted CCDs.",
            flush=True,
            file=log,
        )
        forcedflx = mp.map(_forced_phot, [(custom_tims, custom_srcs, band) for band in bands])
        # forcedflx = []
        # for band in bands:
        #    forcedflx.append(forced_phot(custom_tims, custom_srcs, band))
        print(
            "  Total time for forced photometry = {:.3f} min".format(time.time() - t0),
            flush=True,
            file=log,
        )

        # Populate the new custom catalog and write out.
        for band, flux, ivar in forcedflx:
            custom_cat.set("flux_{}".format(band), flux.astype("f4"))
            custom_cat.set("flux_ivar_{}".format(band), ivar.astype("f4"))

        tractorfile = os.path.join(survey.output_dir, "{}-custom-tractor.fits".format(galaxy))
        if os.path.isfile(tractorfile):
            os.remove(tractorfile)
        custom_cat.writeto(tractorfile)
        print(
            "Wrote {} sources to {}".format(len(custom_cat), tractorfile),
            flush=True,
            file=log,
        )

    else:
        print(
            "Skipping forced photometry on the custom sky-subtracted CCDs.",
            flush=True,
            file=log,
        )

    custom_srcs = read_fits_catalog(custom_cat, fluxPrefix="")

    # [5] Next, render the model image of each CCD, with and without the central
    # large galaxy (custom and pipeline).

    # Custom code for dealing with centrals.
    keep = isolate_central(custom_cat, brickwcs, centrals=centrals)

    custom_srcs_nocentral = np.array(custom_srcs)[keep].tolist()
    pipeline_srcs_nocentral = np.array(pipeline_srcs)[keep].tolist()

    print(
        "Rendering model images with and without surrounding galaxies...",
        flush=True,
        file=log,
    )
    custom_mods = mp.map(_get_mod, [(tim, custom_srcs) for tim in custom_tims])
    pipeline_mods = mp.map(_get_mod, [(tim, pipeline_srcs) for tim in pipeline_tims])

    custom_mods_nocentral = mp.map(_get_mod, [(tim, custom_srcs_nocentral) for tim in custom_tims])
    pipeline_mods_nocentral = mp.map(_get_mod, [(tim, pipeline_srcs_nocentral) for tim in pipeline_tims])

    # import matplotlib.pyplot as plt ; plt.imshow(np.log10(mod), origin='lower') ; plt.savefig('junk.png')
    # pdb.set_trace()

    # [6] Build the custom coadds, with and without the surrounding galaxies.
    print("Producing coadds...", flush=True, file=log)

    def call_make_coadds(usemods, usetims):
        return make_coadds(
            usetims,
            bands,
            brickwcs,
            mods=usemods,
            mp=mp,
            callback=write_coadd_images,
            callback_args=(survey, brickname, version_header, usetims, brickwcs),
        )

    # Custom coadds--all galaxies. (Pipeline coadds already exist.)
    if log:
        with redirect_stdout(log), redirect_stderr(log):
            C = call_make_coadds(custom_mods, custom_tims)
            # P = call_make_coadds(pipeline_mods, pipeline_tims)
    else:
        C = call_make_coadds(custom_mods, custom_tims)
        # P = call_make_coadds(pipeline_mods, pipeline_tims)

    for suffix in ("image", "model"):
        for band in bands:
            ok = _copyfile(
                os.path.join(
                    survey.output_dir,
                    "coadd",
                    brickname[:3],
                    brickname,
                    "legacysurvey-{}-{}-{}.fits.fz".format(brickname, suffix, band),
                ),
                os.path.join(
                    survey.output_dir,
                    "{}-custom-{}-{}.fits.fz".format(galaxy, suffix, band),
                ),
            )
            # os.path.join(survey.output_dir, '{}-custom-{}-{}.fits.fz'.format(galaxy, suffix, band)) )
            if not ok:
                return ok

    # Custom coadds--without the central.
    imtype = "custom"
    if log:
        with redirect_stdout(log), redirect_stderr(log):
            C_nocentral = call_make_coadds(custom_mods_nocentral, custom_tims)
    else:
        C_nocentral = call_make_coadds(custom_mods_nocentral, custom_tims)
    for band in bands:
        ok = _copyfile(
            os.path.join(
                survey.output_dir,
                "coadd",
                brickname[:3],
                brickname,
                "legacysurvey-{}-model-{}.fits.fz".format(brickname, band),
            ),
            os.path.join(
                survey.output_dir,
                "{}-{}-model-nocentral-{}.fits.fz".format(galaxy, imtype, band),
            ),
        )
        if not ok:
            return ok

    # Pipeline coadds--without the central.
    imtype = "pipeline"
    if log:
        with redirect_stdout(log), redirect_stderr(log):
            P_nocentral = call_make_coadds(pipeline_mods_nocentral, pipeline_tims)
    else:
        P_nocentral = call_make_coadds(pipeline_mods_nocentral, pipeline_tims)
    for band in bands:
        ok = _copyfile(
            os.path.join(
                survey.output_dir,
                "coadd",
                brickname[:3],
                brickname,
                "legacysurvey-{}-model-{}.fits.fz".format(brickname, band),
            ),
            os.path.join(
                survey.output_dir,
                "{}-{}-model-nocentral-{}.fits.fz".format(galaxy, imtype, band),
            ),
        )
        if not ok:
            return ok

    # [7] Finally, build png images.
    def call_make_png(R, imtype, nocentral=False):
        rgbkwargs = dict(mnmx=(-1, 100), arcsinh=1)
        # rgbkwargs_resid = dict(mnmx=(0.1, 2), arcsinh=1)
        rgbkwargs_resid = dict(mnmx=(-1, 100), arcsinh=1)

        if nocentral:
            coadd_list = [
                ("{}-model-nocentral".format(imtype), R.comods, rgbkwargs),
                ("{}-image-central".format(imtype), R.coresids, rgbkwargs_resid),
            ]
        else:
            coadd_list = [
                ("custom-image", R.coimgs, rgbkwargs),
                ("custom-model", R.comods, rgbkwargs),
                ("custom-resid", R.coresids, rgbkwargs_resid),
            ]

        for suffix, ims, rgbkw in coadd_list:
            rgb = get_rgb(ims, bands, **rgbkw)
            kwa = {}
            outfn = os.path.join(survey.output_dir, "{}-{}-grz.jpg".format(galaxy, suffix))
            print("Writing {}".format(outfn), flush=True, file=log)
            imsave_jpeg(outfn, rgb, origin="lower", **kwa)
            del rgb

    call_make_png(C, "custom", nocentral=False)
    call_make_png(C_nocentral, "custom", nocentral=True)
    call_make_png(P_nocentral, "pipeline", nocentral=True)

    if cleanup:
        shutil.rmtree(os.path.join(survey.output_dir, "coadd"))
        for stage in ("srcs", "checkpoint"):
            picklefile = os.path.join(survey.output_dir, "{}-runbrick-{}.p".format(galaxy, stage))
            if os.path.isfile(picklefile):
                os.remove(picklefile)

    return 1


def coadds_skysub(
    tims,
    targetwcs,
    survey,
    brickname,
    bands,
    mp,
    subsky_radii=None,
    plots=False,
    plots2=False,
    ps=None,
    verbose=False,
):
    from tractor.sky import ConstantSky
    from legacypipe.reference import get_reference_sources, get_reference_map
    from legacypipe.coadds import make_coadds
    from legacypipe.survey import get_rgb, imsave_jpeg
    from astropy.stats import sigma_clipped_stats

    if plots or plots2:
        import os
        import matplotlib.pyplot as plt

    if plots:
        import matplotlib.patches as patches

        refs, _ = get_reference_sources(
            survey,
            targetwcs,
            targetwcs.pixel_scale(),
            ["r"],
            tycho_stars=False,
            gaia_stars=False,
            large_galaxies=True,
            star_clusters=False,
        )

        pixscale = targetwcs.pixel_scale()
        width, height = (
            targetwcs.get_width() * pixscale / 3600,
            targetwcs.get_height() * pixscale / 3600,
        )  # [degrees]
        bb, bbcc = targetwcs.radec_bounds(), targetwcs.radec_center()  # [degrees]
        pad = 0.5 * width  # [degrees]

        delta = np.max((np.diff(bb[0:2]), np.diff(bb[2:4]))) / 2 + pad / 2
        xlim = bbcc[0] - delta, bbcc[0] + delta
        ylim = bbcc[1] - delta, bbcc[1] + delta

        plt.clf()
        fig, allax = plt.subplots(1, 3, figsize=(12, 5), sharey=True, sharex=True)
        for ax, band in zip(allax, ("g", "r", "z")):
            ax.set_xlabel("RA (deg)")
            ax.text(
                0.9,
                0.05,
                band,
                ha="center",
                va="bottom",
                transform=ax.transAxes,
                fontsize=18,
            )

            if band == "g":
                ax.set_ylabel("Dec (deg)")
            ax.get_xaxis().get_major_formatter().set_useOffset(False)
            for gal in refs:
                ax.add_patch(
                    patches.Circle(
                        (gal.ra, gal.dec),
                        gal.radius,
                        fill=False,
                        edgecolor="black",
                        lw=2,
                    )
                )

            these = np.where([tim.band == band for tim in tims])[0]
            col = plt.cm.Set1(np.linspace(0, 1, len(tims)))
            for ii, indx in enumerate(these):
                tim = tims[indx]
                wcs = tim.subwcs
                cc = wcs.radec_bounds()
                ax.add_patch(
                    patches.Rectangle(
                        (cc[0], cc[2]),
                        cc[1] - cc[0],
                        cc[3] - cc[2],
                        fill=False,
                        lw=2,
                        edgecolor=col[these[ii]],
                        label="ccd{:02d}".format(these[ii]),
                    )
                )
                ax.legend(ncol=2, frameon=False, loc="upper left", fontsize=10)

            ax.set_ylim(ylim)
            ax.set_xlim(xlim)
            ax.invert_xaxis()
            ax.set_aspect("equal")

        plt.subplots_adjust(bottom=0.12, wspace=0.05, left=0.12, right=0.97, top=0.95)
        plt.savefig(os.path.join(survey.output_dir, "metrics", "cus", "{}-ccdpos.jpg".format(ps.basefn)))

    if plots:
        plt.figure(figsize=(8, 6))
        mods = []
        for tim in tims:
            imcopy = tim.getImage().copy()
            tim.sky.addTo(imcopy, -1)
            mods.append(imcopy)
        C = make_coadds(tims, bands, targetwcs, mods=mods, callback=None, mp=mp)
        imsave_jpeg(
            os.path.join(
                survey.output_dir,
                "metrics",
                "cus",
                "{}-pipelinesky.jpg".format(ps.basefn),
            ),
            get_rgb(C.comods, bands),
            origin="lower",
        )

    for tim in tims:
        # full-field mosaic with no sky-subtraction
        tim.imobj.get_tractor_image(gaussPsf=True, pixPsf=False, subsky=False, dq=True, apodize=False)
        H, W = tim.subwcs.shape
        H, W = np.int(H), np.int(W)
        pixel_scale = tim.subwcs.pixel_scale()

        refs, _ = get_reference_sources(
            survey,
            tim.subwcs,
            pixel_scale,
            ["r"],
            tycho_stars=True,
            gaia_stars=True,
            large_galaxies=True,
            star_clusters=True,
        )
        refmask = get_reference_map(tim.subwcs, refs) != 0  # True=object pixels

        # Mask the center of the (target) field--
        # http://stackoverflow.com/questions/8647024/how-to-apply-a-disc-shaped-mask-to-a-numpy-array
        _, x0, y0 = targetwcs.radec2pixelxy(targetwcs.crval[0], targetwcs.crval[1])
        xcen, ycen = np.round(x0 - 1).astype("int"), np.round(y0 - 1).astype("int")
        ymask, xmask = np.ogrid[-ycen : H - ycen, -xcen : W - xcen]
        cenmask = (xmask**2 + ymask**2) <= (subsky_radii[0] / pixel_scale) ** 2

        # plt.imshow(refmask, origin='lower') ; plt.savefig('junk.png')
        # plt.imshow(cenmask, origin='lower') ; plt.savefig('junk.png')
        # plt.imshow(np.log10(tim.data), origin='lower') ; plt.savefig('junk.png')

    allbands = np.array([tim.band for tim in tims])
    for band in sorted(set(allbands)):
        print("Working on band {}".format(band))
        I = np.where(allbands == band)[0]

        bandtims = [
            tims[ii].imobj.get_tractor_image(gaussPsf=True, pixPsf=False, subsky=False, dq=True, apodize=False) for ii in I
        ]

    C = make_coadds(tims, bands, targetwcs, callback=None, sbscale=False, mp=mp)
    for coimg, coiv, band in zip(C.coimgs, C.cowimgs, bands):
        # cosky = np.median(coimg[refmask * (coiv > 0)])
        skypix = _build_objmask(coimg, coiv, refmask * (coiv > 0))
        skymean, skymedian, skysig = sigma_clipped_stats(coimg, mask=~skypix, sigma=3.0)

        I = np.where(allbands == band)[0]
        # print('Band', band, 'Coadd sky:', skymedian)

        for ii in I:
            tims[ii].data -= skymedian
            # print('Tim', tims[ii], 'after subtracting skymedian: median', np.median(tims[ii].data))

    return tims
