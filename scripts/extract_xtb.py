import os
import subprocess
import shlex

if not os.path.isdir("/calcus/binaries/xtb/xtb"):
    subprocess.call(
        shlex.split("tar xvfJ xtb_suite.tar.xz"), cwd="/calcus/binaries/xtb/"
    )
    subprocess.call(
        shlex.split("chmod +x crest stda xtb4stda xtb/bin/xtb"),
        cwd="/calcus/binaries/xtb/",
    )
    os.remove("/calcus/binaries/xtb/xtb_suite.tar.xz")
if not os.path.isdir("/calcus/binaries/xtb/Multiwfn"):
    subprocess.call(
        shlex.split("tar xvfj Multiwfn.tar.bz2"), cwd="/calcus/binaries/xtb/"
    )
    subprocess.call(shlex.split("chmod +x Multiwfn"), cwd="/calcus/binaries/xtb/")
    os.remove("/calcus/binaries/xtb/Multiwfn.tar.bz2")
