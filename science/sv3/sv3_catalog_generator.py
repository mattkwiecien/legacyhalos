#!/usr/bin/env python

# Extract the data from the output and store in a FITS catalog

from collections import defaultdict
from glob import glob
import os
from astropy.table import Table, Column, vstack
import fitsio
import numpy as np

# path = '/global/homes/m/mkwiecie/desi/sv3-clustering'
# base_cat = 'BGS_BRIGHT_S_clustering.dat.fits'


def read_ccds_tractor_sample(galaxy_dir, galaxy, prefix="custom"):
    _, tractor, sample = None, None, None
    refcolumn = "TARGETID"

    files = os.listdir(galaxy_dir)
    for f in files:
        if "isfail" in f:
            return None, None

    # samplefile can exist without tractorfile when using --just-coadds
    samplefile = os.path.join(galaxy_dir, "{}-sample.fits".format(galaxy))
    if os.path.isfile(samplefile):
        sample = Table(fitsio.read(samplefile, upper=True))

    tractorfile = os.path.join(galaxy_dir, "{}-{}-tractor.fits".format(galaxy, prefix))
    if os.path.isfile(tractorfile):
        tractor = Table(fitsio.read(tractorfile, lower=True))

        wt, ws = [], []
        for ii, sid in enumerate(sample[refcolumn]):
            ww = np.where(tractor["ref_id"] == sid)[0]
            if len(ww) > 0:
                wt.append(ww)
                ws.append(ii)
        if len(wt) == 0:
            tractor = None
        else:
            wt = np.hstack(wt)
            ws = np.hstack(ws)
            tractor = tractor[wt]
            sample = sample[ws]
            srt = np.argsort(tractor["flux_r"])[::-1]
            tractor = tractor[srt]
            sample = sample[srt]
            assert np.all(tractor["ref_id"] == sample[refcolumn])
    return tractor, sample


def read_ellipsefit(galaxy, galaxydir, filesuffix="", galaxy_id="", verbose=True, asTable=True):
    """Read the output of write_ellipsefit. Convert the astropy Table into a
    dictionary so we can use a bunch of legacy code.

    """
    if galaxy_id.strip() == "":
        galid = ""
    else:
        galid = "-{}".format(galaxy_id)
    if filesuffix.strip() == "":
        fsuff = ""
    else:
        fsuff = "-{}".format(filesuffix)

    ellipsefitfile = os.path.join(galaxydir, "{}{}-ellipse{}.fits".format(galaxy, fsuff, galid))

    if os.path.isfile(ellipsefitfile):
        print(ellipsefitfile, " exists")
        data = Table(fitsio.read(ellipsefitfile))

        # Optionally convert (back!) into a dictionary.
        if asTable:
            return data
        ellipsefit = {}
        for key in data.colnames:
            val = data[key][0]
            ellipsefit[key.lower()] = val  # lowercase!
    else:
        print(ellipsefitfile, " doesnt exist")
        return None

    return ellipsefit


def get_ellipse_col_dtypes(ellipse_rows):
    col_lkp = {}

    for col in ellipse_rows[0].columns:
        max_len = 1
        max_shape = (1,)

        for row in ellipse_rows:
            if len(row.columns[col].shape) > 1:
                row_len = row.columns[col].shape[1]

                # Store the max length/shape row (for use later when building the table)
                if row_len > max_len:
                    max_len = row_len

                    max_shape = row.columns[col].shape

        col_lkp[col] = (row.columns[col].dtype, max_len, max_shape)

    return col_lkp


def get_ellipse_column_metadata(ellipse_rows):
    cols = defaultdict(list)
    for row in ellipse_rows:
        for col in row.columns:
            cols[col].append(row[col].value[0])

    new_cols = dict()

    for k, v in cols.items():
        if hasattr(v[0], "__len__") and len(v[0]) > 1:
            maxlen = 1
            for item in v:
                if hasattr(item, "__len__") and len(item) > maxlen:
                    is_str = type(item[0]) == np.str_ or type(item[0]) == str
                    maxlen = len(item)

            if is_str:
                new_cols[k] = v
            else:
                new_items = []
                for item in v:
                    new_items.append(
                        np.pad(
                            item.astype(float),
                            (0, maxlen - len(item)),
                            "constant",
                            constant_values=-1,
                        )
                    )

                new_cols[k] = new_items
        else:
            new_cols[k] = v


def main():
    output_path = "/pscratch/sd/m/mkwiecie/legacydata/sv3j_overlap_outputs/output/3962/"
    finished_galaxy_paths = glob(output_path + "*", recursive=False)

    # Create ordered lists of tractor, sample, and ellipse data.
    tractor_rows = []
    sample_rows = []
    ellipse_rows = []

    for path in finished_galaxy_paths[0:5]:
        galaxydir = path
        galaxy = path.split("/")[-1]

        tractor, sample = read_ccds_tractor_sample(galaxydir, galaxy, prefix="custom")
        if tractor is not None:
            tractor_rows.append(tractor)
            sample_rows.append(sample)

        ellipse = read_ellipsefit(
            galaxy,
            galaxydir,
            filesuffix="custom",
            galaxy_id=galaxy,
            verbose=True,
            asTable=True,
        )
        if ellipse is not None:
            ellipse_rows.append(ellipse)

    total_tractor: Table = vstack(tractor_rows)
    total_sample: Table = vstack(sample_rows)

    # We need to do extra work for the ellipse data.
    column_mappings = get_ellipse_col_dtypes()
    column_metadata = get_ellipse_column_metadata()

    total_ellipse = Table()
    for k, v in column_mappings.items():
        dat = column_metadata[k]
        total_ellipse.add_column(Column(data=dat, name=k, dtype=v[0], shape=v[2], length=len(ellipse_rows)))

    # Ensure all reference ID's match
    print(total_ellipse["ID_CENT"])
    print(total_tractor["ref_id"])
    print(total_sample["TARGETID"])

    # Write out files
    total_sample.write("total_sample.fits", format="fits", overwrite=True)
    total_tractor.write("total_tractor.fits", format="fits", overwrite=True)
    total_ellipse.write("total_ellipse.fits", format="fits", overwrite=True)


if __name__ == "__main__":
    main()
