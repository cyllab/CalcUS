FROM python:3.10-slim-bookworm AS build

RUN mkdir -p /binaries/
COPY scripts /calcus/scripts
COPY bin /binaries/xtb
RUN python /calcus/scripts/extract_xtb.py

RUN apt update && apt install build-essential gcc libxm4 libgl1 libmagic1 -y

ADD ./cloud_requirements.txt /calcus/cloud_requirements.txt
RUN pip install -r /calcus/cloud_requirements.txt

####
ADD ./requirements.txt /calcus/requirements.txt
RUN pip install -r /calcus/requirements.txt

FROM python:3.10-slim-bookworm AS calcus_user

COPY --from=0 /binaries/ /binaries/

ARG CALCUS_VERSION_HASH
ENV CALCUS_VERSION_HASH=${CALCUS_VERSION_HASH}

ENV CALCUS_SCR_HOME "/calcus/scr"
ENV CALCUS_KEY_HOME "/calcus/keys"
ENV CALCUS_TEST_SCR_HOME "/calcus/scratch/scr"
ENV CALCUS_TEST_KEY_HOME "/calcus/scratch/keys"

ENV EBROOTORCA "/binaries/orca"
ENV GAUSS_EXEDIR "/binaries/g16"
ENV XTB4STDAHOME "/binaries/xtb"
ENV XTBPATH "/binaries/xtb/xtb:$XTB4STDAHOME"
ENV STDAHOME "/binaries/xtb"

ENV PATH=$PATH:$XTB4STDAHOME/xtb/bin:$XTB4STDAHOME:$EBROOTORCA:$GAUSS_EXEDIR
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/binaries/orca:/usr/lib/openmpi/

ENV PYTHONUNBUFFERED 1

COPY --from=0 /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

RUN apt update && apt install openbabel postgresql-client dos2unix libxm4 libgl1 libmagic1 sshpass python3-dev gfortran mpi-default-bin mpi-default-dev curl -y
RUN curl -LJO https://github.com/nwchemgit/nwchem/releases/download/v7.2.1-release/nwchem-data_7.2.1-1_all.debian_bookworm.deb
RUN curl -LJO https://github.com/nwchemgit/nwchem/releases/download/v7.2.1-release/nwchem_7.2.1-1_amd64.debian_bookworm.deb
RUN dpkg -i nwchem*.deb

COPY calcus /calcus/calcus
COPY frontend /calcus/frontend
COPY docker /calcus/docker
COPY manage.py /calcus/manage.py
COPY scripts /calcus/scripts
#RUN dos2unix /calcus/scripts/*
COPY docker/cluster/config /etc/ssh/ssh_config

RUN adduser --disabled-password --gecos '' calcus  

WORKDIR /calcus/

CMD exec python -m gunicorn calcus.wsgi:application --bind :$PORT --timeout 10 --workers $NUM_WORKERS --threads $NUM_THREADS --timeout $GUNICORN_TIMEOUT

FROM calcus_user AS calcus_cloud

ENV CALCUS_CLOUD True

FROM calcus_user as calcus_dev

ADD ./test-requirements.txt /calcus/test-requirements.txt
RUN  pip install -r /calcus/test-requirements.txt

RUN mkdir -p /calcus/scratch/keys
RUN mkdir -p /calcus/scratch/scr
RUN chown -R calcus:calcus /calcus/scratch
