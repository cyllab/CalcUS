#!/bin/sh

sed -i -e 's/$HOSTNAME/'"$HOSTNAME"'/' /etc/slurm-llnl/slurm.conf
sed -i -e 's/$NUM_CPU/'"$NUM_CPU"'/' /etc/slurm-llnl/slurm.conf


service ssh start
service munge start
service slurmctld start
service slurmd start

chgrp calcus /home/slurm/g16
chgrp calcus /home/slurm/g16/*
chgrp calcus /home/slurm/orca
chgrp calcus /home/slurm/orca/*
chgrp calcus /home/slurm/xtb/*

USER slurm

tail -f /var/log/slurmd/slurmd.log

