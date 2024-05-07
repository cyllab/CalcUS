import os
import subprocess
import shlex

if not os.path.isdir("/binaries/xtb"):
    ret = subprocess.call(shlex.split("tar xvf xtb_suite.tar.xz"), cwd="/binaries/")
    if ret != 0:
        raise Exception(f"Got ret {ret}")

    ret = subprocess.call(
        shlex.split("chmod +x crest stda xtb4stda xtb/bin/xtb"),
        cwd="/binaries/",
    )
    if ret != 0:
        raise Exception(f"Got ret {ret}")

    os.remove("/binaries/xtb_suite.tar.xz")
if not os.path.isdir("/binaries/Multiwfn"):
    ret = subprocess.call(shlex.split("tar xvfj Multiwfn.tar.bz2"), cwd="/binaries/")
    if ret != 0:
        raise Exception(f"Got ret {ret}")

    ret = subprocess.call(shlex.split("chmod +x Multiwfn"), cwd="/binaries/")
    if ret != 0:
        raise Exception(f"Got ret {ret}")

    os.remove("/binaries/Multiwfn.tar.bz2")
