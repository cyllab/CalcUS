#!/bin/bash
#
echo "Setting SHM size"

mount -o remount,size=8G /dev/shm

df -h
