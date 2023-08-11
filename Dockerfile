FROM legacysurvey/legacypipe:DR10.1.3

# Remove the policy.xml file so we do not get an 'exhausted cache resources'
# error when we build mosaics for very large systems.
RUN echo '<policymap></policymap>' > /etc/ImageMagick-6/policy.xml

RUN /sbin/ldconfig

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
SHELL [ "/bin/bash", "--login", "-c" ]

# Get non python dependencies
RUN apt-get update && \
    apt-get -y upgrade
RUN apt-get install -y curl build-essential gfortran && \
    apt-get clean all

# Create a non-root user
ARG username=legacyhalos
ARG uid=1000
ARG gid=100
ENV USER $username
ENV UID $uid
ENV GID $gid
ENV HOME /home/$USER

RUN adduser --disabled-password \
    --gecos "Non-root user" \
    --uid $UID \
    --gid $GID \
    --home $HOME \
    $USER

COPY environment.yml /tmp/
RUN chown $UID:$GID /tmp/environment.yml

# create a project directory inside user home
ENV PROJECT_DIR $HOME/src
RUN mkdir $PROJECT_DIR
WORKDIR $PROJECT_DIR

COPY . $PROJECT_DIR
RUN chown -R $USER $PROJECT_DIR

USER legacyhalos

ENV CONDA_DIR $HOME/miniforge

RUN curl -L -o ~/mambaforge.sh https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh && \
    chmod +x ~/mambaforge.sh && \
    ~/mambaforge.sh -b -p $CONDA_DIR && \
    rm ~/mambaforge.sh

# make non-activate conda commands available
ENV PATH=$CONDA_DIR/bin:$PATH

# make conda activate command available from /bin/bash --login shells
RUN echo ". $CONDA_DIR/etc/profile.d/conda.sh" >> ~/.profile

# make conda activate command available from /bin/bash --interative shells
RUN conda init bash

# build the conda environment
RUN mamba env create --name legacyhalos-env --file /tmp/environment.yml --force && \
    conda clean --all --yes

RUN . $CONDA_DIR/etc/profile.d/conda.sh && \
    conda activate legacyhalos-env && \
    pip install -e .

ENV IPYTHONDIR /tmp/ipython-config
ENV PYTHONPATH=/opt/legacyhalos/workdir:$PYTHONPATH
ENV PATH=/opt/legacyhalos/workdir:$PATH





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