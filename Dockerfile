FROM legacysurvey/legacypipe:DR10.1.3

ENV dependencies="ipython pydl pyyaml h5py colossus gnureadline corner \
                scikit-image fitsio scipy numpy matplotlib astropy astrometry \
                photutils seaborn corner"
RUN python3 -m pip --no-cache-dir install --no-deps $dependencies

# Extra steps for mpich

RUN \
    apt-get update        && \
    apt-get upgrade --yes && \
    apt-get install --yes    \
        build-essential      \
        gfortran             \
        libcurl4             \
        wget                 \
        vim              &&  \
    apt-get clean all    &&  \
    rm -rf /var/lib/apt/lists/*

ARG mpich=4.0.2
ARG mpich_prefix=mpich-$mpich

RUN \
    wget https://www.mpich.org/static/downloads/$mpich/$mpich_prefix.tar.gz && \
    tar xvzf $mpich_prefix.tar.gz                                           && \
    cd $mpich_prefix                                                        && \
    FFLAGS=-fallow-argument-mismatch FCFLAGS=-fallow-argument-mismatch ./configure            && \
    make -j 16                                                              && \
    make install                                                            && \
    make clean                                                              && \
    cd ..                                                                   && \
    rm -rf $mpich_prefix

RUN /sbin/ldconfig

RUN python3 -m pip install mpi4py

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