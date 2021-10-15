FROM python:3.7

ENV PYTHONUNBUFFERED 1

ENV CALCUS_SCR_HOME "/calcus/scr"
ENV CALCUS_RESULTS_HOME "/calcus/results"
ENV CALCUS_KEY_HOME "/calcus/keys"
ENV CALCUS_TEST_SCR_HOME "/calcus/frontend/tests/scr"
ENV CALCUS_TEST_RESULTS_HOME "/calcus/frontend/tests/results"
ENV CALCUS_TEST_KEY_HOME "/calcus/frontend/tests/keys"

ENV EBROOTORCA "/binaries/orca"
ENV GAUSS_EXEDIR "/binaries/g16"
ENV XTBHOME "/binaries/xtb"
ENV XTB4STDAHOME "/binaries/xtb"
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:"/binaries/orca"
ENV CALCUS_DOCKER "True"

ENV PATH=$PATH:"/binaries/xtb:/binaries/g16:/binaries/orca:/binaries/other:/binaries/openmpi"
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/binaries/orca:/usr/lib/openmpi/

ADD requirements.txt /calcus/requirements.txt

WORKDIR /calcus/

RUN pip install -r requirements.txt
RUN apt update && apt install openbabel sshpass -y
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ buster-pgdg main" >>  /etc/apt/sources.list.d/pgdg.list
RUN sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ buster-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
RUN apt install wget ca-certificates -y
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
RUN apt update && apt install postgresql-client -y
RUN adduser --disabled-password --gecos '' calcus  

RUN pip install -U "celery[redis]"

ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN mkdir -p /calcus/logs
RUN mkdir -p /calcus/keys
RUN mkdir -p /calcus/scr
RUN mkdir -p /calcus/results
