[![Coverage Status](https://coveralls.io/repos/github/mattkwiecien/legacyhalos/badge.svg?branch=main)](https://coveralls.io/github/mattkwiecien/legacyhalos?branch=main)

# Stellar Mass Content of Dark Matter Halos in Legacy Surveys Imaging

The `DESI Legacy Imaging Surveys`_ have delivered deep *grz* optical imaging and
unWISE *W1* and *W2* mid-infrared imaging of over 20,000 sq. deg of the
extragalactic sky.

This repository contains code and papers for a multi-pronged analysis of the
group- and cluster-scale dark matter halos identified in Legacy Survey imaging,
particularly the stellar mass content of the central galaxies.  

The key science goals are to:

1. Obtain an accurate census of the integrated stellar masses of massive central
   galaxies---which dominate the massive end of the galaxy stellar mass
   function---as a function of halo mass and redshift.

2. Measure the stellar mass density profiles and structural properties (e.g.,
   half-mass radius, concentration), and their correlation with dark matter halo
   assembly histories.  

3. Measure the stellar mass-halo mass relation and the scatter in the stellar
   masses of central galaxies, as a probe of star formation efficiency and
   feedback in massive systems.

4. Measure the fraction of stars formed *in situ* versus *ex situ* in massive
   spheroidal galaxies.

5. And much more...!

We gratefully acknowledge funding support for this work from the National
Science Foundation under grants AST-1616414 and AST-1909374, and the
U.S. Department of Energy, Office of Science, Office of High Energy Physics
under Award Number DE-SC0020086.

`DESI Legacy Imaging Surveys`: http://legacysurvey.org

## Development 

To install legacyhalos to do development it's recommended to use conda (or mamba).  

First clone the repository

`git clone https://github.com/mattkwiecien/legacyhalos`

Create the conda environment

```
conda env create -n legacyhalos -f environment.yml
conda activate legacyhalos
```

Lastly, install `legacyhalos` with pip from within your `legacyhalos` directory

`pip install -e .`

### Tests

Tests are run with `pytest`.  Run 

`pytest -vv py/test/` 

from the root directory to run all tests.

### Publishing new Docker images

Docker images can automatically be published by pushing tags to `main`.  To publish a new docker image, create a new tag that begins with `docker` e.g.

```
git tag docker-img-0.1.0.1
git push origin docker-img-0.1.0.1
```

This will kick off a build of your docker image and publish it on github's docker image host.  This image is then pullable using the web address

`docker:ghcr.io/mattkwiecien/legacyhalos:docker-img-0.1.0.1`