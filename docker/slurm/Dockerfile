FROM ubuntu:latest
ENV DEBIAN_FRONTEND "noninteractive"
RUN apt update && apt install slurmd slurmctld munge openssh-server openmpi-bin -y
RUN mkdir -p /home/slurm/
RUN usermod --shell /bin/bash --home /home/slurm slurm
RUN chown slurm:slurm /home/slurm
RUN groupadd calcus
RUN usermod -a -G calcus slurm

RUN yes "clustertest" | passwd slurm

ENV EBROOTORCA "/home/slurm/orca"
ENV GAUSS_EXEDIR "/home/slurm/g16"
ENV XTB4STDAHOME "/binaries/xtb/"
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:"/home/slurm/orca"

ENV PATH=$PATH:"/home/slurm/xtb:/home/slurm/g16:/home/slurm/orca:/home/slurm/other:/home/slurm/openmpi"
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/binaries/orca:/usr/lib/openmpi/

ADD slurm.conf /etc/slurm-llnl/
ADD cgroup.conf /etc/slurm-llnl/
ADD sshd_config /etc/ssh/
ADD run_slurm.sh /home/slurm

RUN mkdir -p /var/spool/slurmd
RUN mkdir -p /var/log/slurmctl/
RUN mkdir -p /var/log/slurmd/
RUN chown slurm:slurm /var/spool/slurmd
RUN chown slurm:slurm /var/log/slurmctl
RUN chown slurm:slurm /var/log/slurmd

ENV PYTHONUNBUFFERED 1

RUN echo "export PATH="$PATH > /home/slurm/.bashrc
RUN chown slurm:slurm /home/slurm/.bashrc
