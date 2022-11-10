FROM python:3.9 AS calcus_user

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

ADD ./requirements.txt /calcus/requirements.txt
RUN pip install -r /calcus/requirements.txt
RUN apt update && apt install openbabel sshpass postgresql-client dos2unix openmpi-bin -y

RUN mkdir -p /binaries/

COPY calcus /calcus/calcus
COPY scripts /calcus/scripts
COPY static /calcus/static
COPY frontend /calcus/frontend
COPY docker /calcus/docker
COPY bin /binaries/xtb
COPY manage.py /calcus/manage.py
COPY docker/cluster/config /etc/ssh/ssh_config

WORKDIR /calcus/

RUN ls /calcus/

RUN dos2unix scripts/*
RUN python scripts/extract_xtb.py

RUN adduser --disabled-password --gecos '' calcus  

FROM calcus_user as calcus_dev

ADD ./test-requirements.txt /calcus/test-requirements.txt
RUN  pip install -r /calcus/test-requirements.txt
RUN mkdir -p /calcus/scratch/keys
RUN mkdir -p /calcus/scratch/scr
RUN mkdir -p /calcus/scratch/results
RUN chown -R calcus:calcus /calcus/scratch
