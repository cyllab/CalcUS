#!/bin/bash
#SBATCH --job-name=CalcUS
#SBATCH --output=%x-%j.log
#SBATCH --time=168:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=8

export OMP_NUM_THREADS=8,1
export OMP_STACKSIZE=1G
export PATH=$PATH:/home/slurm/:/home/slurm/openmpi
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/slurm/orca:/usr/lib/openmpi
export EBROOTORCA=/home/slurm/orca

cd $SLURM_SUBMIT_DIR

