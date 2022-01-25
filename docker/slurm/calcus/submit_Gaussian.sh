#!/bin/bash
#SBATCH --job-name=CalcUS
#SBATCH --output=%x-%j.log
#SBATCH --time=168:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=8

export PATH=$PATH:/home/slurm/g16
export GAUSS_EXEDIR=/home/slurm/g16
export PGI_FASTMATH_CPU=sandybridge

cd $SLURM_SUBMIT_DIR

