FROM legacysurvey/legacypipe:DR10.1.3

ENV dependencies="ipython pydl pyyaml h5py colossus gnureadline corner \
                scikit-image fitsio scipy numpy matplotlib astropy astrometry \
                photutils seaborn corner"
RUN python3 -m pip --no-cache-dir install --no-deps $dependencies

# Extra steps for mpi4py
RUN \
    apt-get update        && \
    apt-get upgrade --yes && \
    apt-get install --yes    \
        libmpich-dev  \
        python3-dev && \
    apt-get clean all

RUN python3 -m pip install --no-binary=mpi4py mpi4py

# Remove the policy.xml file so we do not get an 'exhausted cache resources'
# error when we build mosaics for very large systems.
RUN echo '<policymap></policymap>' > /etc/ImageMagick-6/policy.xml
ENV IPYTHONDIR /tmp/ipython-config

WORKDIR /src

# Copy codebase to /src
COPY . /src/legacyhalos
RUN cd /src/legacyhalos && \
    python3 -m pip install --no-deps .

ENV PYTHONPATH=/src/legacyhalos/py:$PYTHONPATH
ENV PATH=/src/legacyhalos/bin:$PATH