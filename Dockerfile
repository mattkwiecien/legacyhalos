FROM legacysurvey/legacypipe:DR10.1.3

# Setup conda path
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH

# Get non python dependencies
RUN apt-get update && \
    apt-get -y upgrade
RUN apt-get install -y curl tini build-essential gfortran python3-dev python3-pip wget && \
    apt-get clean all

# MPI install needs to be done explicitly 
ARG mpich=4.0.2
ARG mpich_prefix=mpich-$mpich
RUN wget https://www.mpich.org/static/downloads/$mpich/$mpich_prefix.tar.gz         && \
    tar xvzf $mpich_prefix.tar.gz                                                   && \
    cd $mpich_prefix                                                                && \
    ./configure FFLAGS=-fallow-argument-mismatch FCFLAGS=-fallow-argument-mismatch  && \
    make -j 4                                                                       && \
    make install                                                                    && \
    make clean                                                                      && \
    cd ..                                                                           && \
    rm -rf $mpich_prefix

RUN /sbin/ldconfig

# Create a legacyhalos user, and assign it to container
RUN /usr/sbin/groupadd -g 1000 user && \
    /usr/sbin/useradd -u 1000 -g 1000 -d /opt/legacyhalos legacyhalos && \
    mkdir /opt/legacyhalos && chown legacyhalos.user /opt/legacyhalos && \
    chown -R legacyhalos.user /opt

COPY . /opt/legacyhalos/workdir
RUN chown -R legacyhalos.user /opt/legacyhalos/workdir

USER legacyhalos

# Install mamba and create legacyhalos environment
RUN curl -L -o ~/mambaforge.sh https://github.com/conda-forge/miniforge/releases/download/23.1.0-1/Mambaforge-23.1.0-1-Linux-x86_64.sh && \
    /bin/bash ~/mambaforge.sh -b -p /opt/conda && \
    rm ~/mambaforge.sh
RUN . /opt/conda/etc/profile.d/conda.sh && mamba create --yes --name legacyhalos-env
RUN echo ". /opt/conda/etc/profile.d/conda.sh" > /opt/legacyhalos/startup.sh && \
    echo "mamba activate legacyhalos-env" >> /opt/legacyhalos/startup.sh

COPY . environment.yml
RUN source /opt/conda/etc/profile.d/conda.sh && \
    mamba create env -f environment.yml && \
    mamba clean -af --yes

RUN . /opt/conda/etc/profile.d/conda.sh && mamba activate legacyhalos-env && \
    cd /opt/legacyhalos/workdir && \
    python setup.py install

# Remove the policy.xml file so we do not get an 'exhausted cache resources'
# error when we build mosaics for very large systems.
RUN echo '<policymap></policymap>' > /etc/ImageMagick-6/policy.xml
ENV IPYTHONDIR /tmp/ipython-config

# Now set up legacyhalos
WORKDIR /src

ENV PYTHONPATH=/src/legacyhalos/py:$PYTHONPATH
ENV PATH=/src/legacyhalos/bin:$PATH

# Install local legacyhalos 
RUN . /opt/conda/etc/profile.d/conda.sh && mamba activate legacyhalos && \
    cd /opt/legacyhalos/workdir && \
    python setup.py install
