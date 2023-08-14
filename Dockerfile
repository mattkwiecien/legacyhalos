FROM legacysurvey/legacypipe:DR10.1.3

# BASE IMAGE REMARK: We need to match astrometry's python version, otherwise there will be errors
# see https://github.com/Homebrew/homebrew-core/issues/116710

# Tractor isn't added to the pythonpath in the base image.
ENV PYTHONPATH=$PYTHONPATH:/src/tractor

# Remove the policy.xml file so we do not get an 'exhausted cache resources'
# error when we build mosaics for very large systems.
RUN echo '<policymap></policymap>' > /etc/ImageMagick-6/policy.xml
RUN /sbin/ldconfig

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PATH=/opt/conda/bin:$PATH

# Get non python dependencies
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y curl build-essential gfortran tini && \
    apt-get clean all

# Create a non-root user
RUN /usr/sbin/groupadd -g 1000 user && \
    /usr/sbin/useradd -u 1000 -g 1000 -d /opt/legacyhalos legacyhalos && \
    mkdir /opt/legacyhalos && \
    chown legacyhalos.user /opt/legacyhalos && \
    chown -R legacyhalos.user /opt

# Copy codebase to /opt/legacyhalos
COPY . /src/legacyhalos
COPY docker/docker-entrypoint.sh /usr/local/bin/

RUN chown -R legacyhalos.user /src && \
    chown -R legacyhalos.user /src/legacyhalos && \
    chown legacyhalos.user /usr/local/bin/docker-entrypoint.sh && \
    chmod u+x /usr/local/bin/docker-entrypoint.sh && \
    mkdir /opt/legacyhalos/env && \
    chown -R legacyhalos.user /opt/legacyhalos/env

# Install mamba/conda
RUN curl -L -o ~/mambaforge.sh https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh && \
    /bin/bash ~/mambaforge.sh -b -p /opt/conda && \
    rm ~/mambaforge.sh

# Finally, swap to non-root user and set their home directory
USER legacyhalos
WORKDIR /src
ENV HOME=/opt/legacyhalos

# Install the development environment
RUN . /opt/conda/etc/profile.d/conda.sh && \
    cd /src/legacyhalos && \
    mamba env create -p /opt/legacyhalos/env -f environment.yml && \
    conda clean -af --yes

# Extra work for mpi on NERSC
# ENV LD_LIBRARY_PATH=/opt/cray/pe/mpt/7.7.10/gni/mpich-gnu-abi/8.2/lib:$LD_LIBRARY_PATH 
# RUN . /opt/conda/etc/profile.d/conda.sh && \
#     conda activate /opt/legacyhalos/env && \
#     mamba remove mpi4py --yes && \
#     mamba install --yes -c conda-forge  "mpich=4.0.3=external_*" mpi4py 

# Install legacyhalos into the conda environment
RUN . /opt/conda/etc/profile.d/conda.sh && \
    cd /src/legacyhalos && \
    conda activate /opt/legacyhalos/env && \
    pip install . --no-deps

ENV IPYTHONDIR=/tmp/ipython-config PYTHONPATH=/src/legacyhalos:$PYTHONPATH PATH=/src/legacyhalos:$PATH

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]
