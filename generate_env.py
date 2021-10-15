#!/usr/bin/python3

import secrets
import os
from shutil import which

ENV_TEMPLATE = """
CALCUS_SECRET_KEY='{}'
CALCUS_GAUSSIAN={}
CALCUS_ORCA={}
CALCUS_OPENMPI={}
CALCUS_XTB={}
OMP_NUM_THREADS={},1
NUM_CPU={}
OMP_STACKSIZE={}G
USE_CACHED_LOGS=true
POSTGRES_PASSWORD={}
UID={}
GID={}
CALCUS_SU_NAME={}
"""

cwd = os.getcwd()

if not os.path.isdir("data"):
    os.mkdir("data")

def gen_key():
    length = 50
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'

    return ''.join(secrets.choice(chars) for i in range(length))

def gen_pass():
    length = 50
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789'

    return ''.join(secrets.choice(chars) for i in range(length))

def valid_dir(path, name):
    if path == "":
        return False
    if not os.path.isdir(path):
        return False
    if not os.path.isfile(os.path.join(path, name)):
        return False
    return True

def find_software(name):
    ret = which(name)
    if ret is not None:
        print("{} found in $PATH ({})".format(name, ret))
        return os.path.dirname(ret)

    ans = ""
    while True:
        ans = input("{} has not been found in $PATH. Will you use this software locally? (Y/N)".format(name))
        if ans.lower() in ['y', 'n']:
            break
        print("Invalid option")

    if ans.lower() == 'n':
        print("{} skipped".format(name))
        return ""

    path = ""
    while True:
        path = input("What is the full path to the directory containing this software?")
        if not valid_dir(path, name):
            print("The specified path is invalid or does not contain the software {}".format(name))
        else:
            break

    return path

HEADER = """
******************************
CalcUS parameters file creator
******************************
"""

print(HEADER)

if os.path.isfile(".env"):
    print("The local directory already contains a .env file. Delete it if you want to create a new one.")
    exit(0)

print("Generating secret key...")
secret_key = gen_key()
print("Secret key generated")
print("")

print("Generating PostgreSQL password...")
postgres = gen_pass()
print("PostgreSQL password generated")
print("")

while True:
    su_name = input("Choose a username for the superuser account. This account will have the password 'calcus_default_password'. Make sure to change this password in the profile.")
    if su_name.strip() == "":
        print("Invalid username")
    else:
        break

print("")
software_list = ["g16", "orca", "xtb", "mpirun"]
software_paths = {}
local_calc = False
for s in software_list:
    path = find_software(s)
    if path == "":
        software_paths[s] = cwd
    else:
        if s == "mpirun":
            software_paths[s] = os.path.dirname(path)
        else:
            software_paths[s] = path
        local_calc = True

if local_calc:
    while True:
        n = input("How many CPU cores do you want CalcUS to use for local calculations? (e.g. 8)")
        try:
            num_cpu = int(n)
        except ValueError:
            print("Invalid number of cores")
        else:
            if num_cpu < 1:
                print("Invalid number of cores")
            else:
                break
    print("")
    while True:
        n = input("How many GB of RAM per core do you want CalcUS to use for local calculations? (e.g. 1)")
        try:
            mem = int(n)
        except ValueError:
            print("Invalid number of GB")
        else:
            if mem < 1:
                print("Invalid number of GB")
            else:
                break
    print("")
else:
    num_cpu = 1
    mem = 1

print("Writing .env file...")
with open(".env", 'w') as out:
    out.write(ENV_TEMPLATE.format(secret_key, software_paths["g16"], software_paths["orca"], software_paths["mpirun"], software_paths["xtb"], num_cpu, num_cpu, mem, postgres, os.getuid(), os.getgid(), su_name))
print("Done!")
