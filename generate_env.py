#!/usr/bin/python3

import secrets
import os
import sys
from shutil import which

ENV_TEMPLATE = """
# Django cryptographic salt
CALCUS_SECRET_KEY='{}'

{}
# Number of OpenMPI threads to use (xTB)
OMP_NUM_THREADS={},1

# Number of cores to use for local calculations
NUM_CPU={}

# Amount of memory allocated per core/thread in Gb (must be whole number)
OMP_STACKSIZE={}G

# Use cached calculation logs during testing (for developers)
USE_CACHED_LOGS=true

# Password of the PostgreSQL database (SENSITIVE)
POSTGRES_PASSWORD={}

# User ID to use (Linux/Mac only)
UID={}

# Group ID to use (Linux/Mac only)
GID={}

# Username of the superuser account (automatically created on startup if does not already exist)
CALCUS_SU_NAME={}

# Ping server to participate in user statistics (True/False)
CALCUS_PING_SATELLITE={}

# Randomly generated user code to identify this instance of CalcUS
CALCUS_PING_CODE={}
"""

OVERRIDE_TEMPLATE = """
version: "3.4"

services:
        celery_comp:
                volumes:
                        - .:/calcus
{}"""

TEST_OVERRIDE_TEMPLATE = """
version: "3.4"

services:
        web:
                volumes:
                        - .:/calcus
{}
        slurm:
                volumes:
                        - .:/calcus
                        - ./docker/slurm/calcus:/home/slurm/calcus
{}"""

cwd = os.getcwd()

if not os.path.isdir("data"):
    os.mkdir("data")


def gen_key():
    length = 50
    chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"

    return "".join(secrets.choice(chars) for i in range(length))


def gen_chars():
    length = 50
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"

    return "".join(secrets.choice(chars) for i in range(length))


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
        print(f"{name} found in $PATH ({ret})")
        return os.path.dirname(ret)

    ans = ""
    while True:
        ans = input(
            f"{name} has not been found in $PATH. Will you use this software locally? (Y/N)\n"
        )
        if ans.lower() in ["y", "n"]:
            break
        print("Invalid option")

    if ans.lower() == "n":
        print(f"{name} skipped")
        return ""

    path = ""
    while True:
        path = input(
            "What is the full path to the directory containing this software?\n"
        )
        if not valid_dir(path, name):
            print(
                f"The specified path is invalid or does not contain the software {name}"
            )
        else:
            break

    return path


def get_env_backup_path():
    for i in range(1, 51):
        path = os.path.join("backups", f"env.backup.{i}")
        if not os.path.isfile(path):
            return path
    else:
        path = "env.backup.latest"
        print(f"Too many backup environment files! Writing to {path}")
        return path


HEADER = """
******************************
CalcUS parameters file creator
******************************
"""

print(HEADER)

if os.path.isfile(".env"):
    print(
        "The local directory already contains a .env file. Delete it if you want to create a new one."
    )
    exit(0)

secret_key = gen_key()
print("Secret key generated")
print("\n")

postgres = gen_chars()
print("PostgreSQL password generated")
print("\n")

while True:
    su_name = input(
        "Choose a username for the superuser account. This account will have the password 'default'. Make sure to change this password in the profile.\n"
    )
    if su_name.strip() == "":
        print("Invalid username\n")
    else:
        break

print("\n")

software_list = {
    "g16": "# Path to the directory directly containing g16 (e.g. /home/user/software/gaussian)\nCALCUS_GAUSSIAN={}\n",
    "orca": "# Path to the directory directly containing orca\nCALCUS_ORCA={}\n",
    "xtb": "# Path to the directory directly containing xtb, crest, stda, xtb4stda\nCALCUS_XTB={}\n",
}

override_list = {
    "g16": ["                        - ${CALCUS_GAUSSIAN}:/binaries/g16"],
    "orca": ["                        - ${CALCUS_ORCA}:/binaries/orca"],
    "xtb": ["                        - ${CALCUS_XTB}:/binaries/xtb"],
}

software_paths = ""
override_content = ""

local_calc = False
for s, path_template in software_list.items():
    path = find_software(s)
    if path != "":
        software_paths += path_template.format(path)
        for p in override_list[s]:
            override_content += p + "\n"
        local_calc = True

if local_calc:
    while True:
        n = input(
            "How many CPU cores do you want CalcUS to use for local calculations? (e.g. 8)\n"
        )
        try:
            num_cpu = int(n)
        except ValueError:
            print("Invalid number of cores\n")
        else:
            if num_cpu < 1:
                print("Invalid number of cores\n")
            else:
                break
    print("\n")
    while True:
        n = input(
            "How many GB of RAM per core do you want CalcUS to use for local calculations? (e.g. 1)\n"
        )
        try:
            mem = int(n)
        except ValueError:
            print("Invalid number of GB\n")
        else:
            if mem < 1:
                print("Invalid number of GB\n")
            else:
                break
    print("\n")
else:
    num_cpu = 1
    mem = 1

while True:
    ans = input(
        "Do you accept to send anonymous signals to indicate that you are using CalcUS? (Y/N)\n\nThis will allow us to estimate how many users are benefiting from this project and report this number to funding agencies. If enabled, CalcUS will send a signal every hour to our server. You will only be identified by a randomly generated code in order to differentiate unique instances. This is optional, but helps the project.\n"
    )
    if ans.lower() in ["y", "n"]:
        break
    print("Invalid option\n")

if ans.lower() == "y":
    print("Anonymous signals enabled\n")
    ping = "True"
    ping_code = gen_chars()
    print("Code generated")
else:
    print("Anonymous signals disabled\n")
    ping = "False"
    ping_code = "empty"

if sys.platform == "win32":
    uid = ""
    gid = ""
else:
    uid = os.getuid()
    gid = os.getgid()

print("Writing .env and docker override files...\n")
with open(".env", "w") as out:
    out.write(
        ENV_TEMPLATE.format(
            secret_key,
            software_paths,
            num_cpu,
            num_cpu,
            mem,
            postgres,
            uid,
            gid,
            su_name,
            ping,
            ping_code,
        )
    )

with open("docker-compose.override.yml", "w") as out:
    out.write(OVERRIDE_TEMPLATE.format(override_content))

with open("test-compose.override.yml", "w") as out:
    out.write(
        TEST_OVERRIDE_TEMPLATE.format(
            override_content, override_content.replace("binaries", "home/slurm")
        )
    )

print("Creating necessary folders")
for d in ["scr", "results", "keys", "logs", "backups"]:
    if not os.path.isdir(d):
        os.mkdir(d)

env_backup_path = get_env_backup_path()
print(f"Creating .env backup ({env_backup_path})")
with open(env_backup_path, "w") as out:
    out.write(
        ENV_TEMPLATE.format(
            secret_key,
            software_paths,
            num_cpu,
            num_cpu,
            mem,
            postgres,
            uid,
            gid,
            su_name,
            ping,
            ping_code,
        )
    )

print("Done! You can now start CalcUS.")
