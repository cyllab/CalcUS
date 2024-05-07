import os
import subprocess
import shlex

if not os.path.isdir("/binaries/xtb"):
    subprocess.call(shlex.split("tar xvfJ xtb_suite.tar.xz"), cwd="/binaries/")
    subprocess.call(
        shlex.split("chmod +x crest stda xtb4stda xtb/bin/xtb"),
        cwd="/binaries/",
    )
    os.remove("/binaries/xtb_suite.tar.xz")
if not os.path.isdir("/binaries/Multiwfn"):
    subprocess.call(shlex.split("tar xvfj Multiwfn.tar.bz2"), cwd="/binaries/")
    subprocess.call(shlex.split("chmod +x Multiwfn"), cwd="/binaries/")
    os.remove("/binaries/Multiwfn.tar.bz2")
