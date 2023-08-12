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
    mamba env create -n legacyhalos -f environment.yml && \
    mamba clean -af --yes

RUN echo ". /opt/conda/etc/profile.d/conda.sh" > /opt/legacyhalos/startup.sh && \
    echo "conda activate legacyhalos" >> /opt/legacyhalos/startup.sh
    
RUN . /opt/conda/etc/profile.d/conda.sh && \
    cd /opt/legacyhalos/workdir && \
    conda activate legacyhalos && \
    pip install . --no-deps

ENV IPYTHONDIR /tmp/ipython-config
ENV PYTHONPATH=/home/legacyhalos/src:$PYTHONPATH
ENV PATH=/home/legacyhalos/src:$PATH

ENTRYPOINT [ "/opt/legacyhalos/entrypoint.sh" ]


# # # MPI install needs to be done explicitly 
# # ARG mpich=4.0.2
# # ARG mpich_prefix=mpich-$mpich
# # RUN wget https://www.mpich.org/static/downloads/$mpich/$mpich_prefix.tar.gz         && \
# #     tar xvzf $mpich_prefix.tar.gz                                                   && \
# #     cd $mpich_prefix                                                                && \
# #     ./configure FFLAGS=-fallow-argument-mismatch FCFLAGS=-fallow-argument-mismatch  && \
# #     make -j 4                                                                       && \
# #     make install                                                                    && \
# #     make clean                                                                      && \
# #     cd ..                                                                           && \
# #     rm -rf $mpich_prefix