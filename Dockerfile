FROM python:3.9-bullseye AS calcus_user

ARG CALCUS_VERSION_HASH
ENV CALCUS_VERSION_HASH=${CALCUS_VERSION_HASH}

ENV PYTHONUNBUFFERED 1

ENV CALCUS_SCR_HOME "/calcus/scr"
ENV CALCUS_KEY_HOME "/calcus/keys"
ENV CALCUS_TEST_SCR_HOME "/calcus/scratch/scr"
ENV CALCUS_TEST_KEY_HOME "/calcus/scratch/keys"

ENV EBROOTORCA "/binaries/orca"
ENV GAUSS_EXEDIR "/binaries/g16"
ENV XTB4STDAHOME "/binaries/xtb"
ENV XTBPATH "/binaries/xtb/xtb:$XTB4STDAHOME"
ENV STDAHOME "/binaries/xtb"
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:"/binaries/orca"

ENV PATH=$PATH:$XTB4STDAHOME/xtb/bin:$XTB4STDAHOME:$EBROOTORCA:$GAUSS_EXEDIR
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/binaries/orca:/usr/lib/openmpi/

RUN apt update && apt install openbabel sshpass postgresql-client dos2unix python3-dev gfortran mpi-default-bin mpi-default-dev -y
RUN curl -LJO https://github.com/nwchemgit/nwchem/releases/download/v7.2.0-release/nwchem-data_7.2.0-2_all.debian_bullseye.deb
RUN curl -LJO https://github.com/nwchemgit/nwchem/releases/download/v7.2.0-release/nwchem_7.2.0-2_amd64.debian_bullseye.deb
RUN dpkg -i nwchem*7.2.0*.deb

ADD ./requirements.txt /calcus/requirements.txt
RUN pip install -r /calcus/requirements.txt

RUN mkdir -p /binaries/
COPY bin /binaries/xtb
COPY scripts /calcus/scripts
RUN dos2unix /calcus/scripts/*
RUN python /calcus/scripts/extract_xtb.py

COPY calcus /calcus/calcus
COPY static /calcus/static
COPY frontend /calcus/frontend
COPY docker /calcus/docker
COPY manage.py /calcus/manage.py
COPY docker/cluster/config /etc/ssh/ssh_config

WORKDIR /calcus/

RUN ls /calcus/

RUN adduser --disabled-password --gecos '' calcus  

FROM calcus_user as calcus_dev

ADD ./test-requirements.txt /calcus/test-requirements.txt
ADD ./cloud_requirements.txt /calcus/cloud_requirements.txt
RUN  pip install -r /calcus/test-requirements.txt
RUN  pip install -r /calcus/cloud_requirements.txt
RUN mkdir -p /calcus/scratch/keys
RUN mkdir -p /calcus/scratch/scr
RUN chown -R calcus:calcus /calcus/scratch
