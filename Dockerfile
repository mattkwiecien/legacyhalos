FROM legacysurvey/legacypipe:DR10.1.3

# Remove the policy.xml file so we do not get an 'exhausted cache resources'
# error when we build mosaics for very large systems.
RUN echo '<policymap></policymap>' > /etc/ImageMagick-6/policy.xml
RUN /sbin/ldconfig

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH

# Get non python dependencies
RUN apt-get update && \
    apt-get -y upgrade
RUN apt-get install -y curl build-essential gfortran tini && \
    apt-get clean all

# Create a non-root user
RUN /usr/sbin/groupadd -g 1000 user && \
    /usr/sbin/useradd -u 1000 -g 1000 -d /opt/legacyhalos legacyhalos && \
    mkdir /opt/legacyhalos && \
    chown legacyhalos.user /opt/legacyhalos && \
    chown -R legacyhalos.user /opt

COPY . /opt/legacyhalos/workdir
RUN chown -R legacyhalos.user /opt/legacyhalos/workdir

RUN mkdir /opt/legacyhalos/env && \
    chown -R legacyhalos.user /opt/legacyhalos/env

COPY docker/entrypoint.sh /opt/legacyhalos/entrypoint.sh
RUN chown legacyhalos.user /opt/legacyhalos/entrypoint.sh && \
    chmod u+x /opt/legacyhalos/entrypoint.sh

# Install mamba/conda
RUN curl -L -o ~/mambaforge.sh https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh && \
    /bin/bash ~/mambaforge.sh -b -p /opt/conda && \
    rm ~/mambaforge.sh
RUN chown -R legacyhalos.user /homedir

# Finally, swap to non-root user
USER legacyhalos

RUN . /opt/conda/etc/profile.d/conda.sh && \
    cd /opt/legacyhalos/workdir && \
    mamba env create -p /opt/legacyhalos/env -f environment.yml && \
    conda clean -af --yes

# Extra work for mpi on NERSC
ENV LD_LIBRARY_PATH=/opt/cray/pe/mpt/7.7.10/gni/mpich-gnu-abi/8.2/lib:$LD_LIBRARY_PATH 
RUN . /opt/conda/etc/profile.d/conda.sh && \
    conda activate /opt/legacyhalos/env && \
    mamba remove mpi4py && \
    mamba install -c conda-forge  "mpich=4.0.3=external_*" mpi4py 

RUN . /opt/conda/etc/profile.d/conda.sh && \
    cd /opt/legacyhalos/workdir && \
    conda activate /opt/legacyhalos/env && \
    pip install . --no-deps

# Prepend paths to use this conda environment's package 
# Note we do this instead of using an entrypoint script due to non-root user issues.
ENV IPYTHONDIR /tmp/ipython-config
ENV PYTHONPATH=/opt/legacyhalos/env/bin:$PYTHONPATH
ENV PATH=/opt/legacyhalos/env/bin:$PATH