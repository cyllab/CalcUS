#!/bin/sh

sed -i -e 's/$HOSTNAME/'"$HOSTNAME"'/' /etc/slurm-llnl/slurm.conf
sed -i -e 's/$NUM_CPU/'"$NUM_CPU"'/' /etc/slurm-llnl/slurm.conf

service ssh start
service munge start
service slurmctld start
service slurmd start
tail -f /var/log/slurmd/slurmd.log

