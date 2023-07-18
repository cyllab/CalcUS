import glob
import os
import shutil

KEEP_FILES = [
    "calc.inp",
    "calc.com",
    "calc.out",
    "calc.log",
    "calc.xyz",
    "calc.allxyz",
    "calc.relaxscanact.dat",
    "in.xyz",
    "xtbopt.xyz",
    "xtbopt.log",
    "calc_trj.xyz",
    "calc_MEP_trj.xyz",
    "xtbscan.log",
    "input",
    "g98.out",
    "crest_conformers.xyz",
    "vibspectrum",
    "struct.xyz",
    "struct2.xyz",
    "in-HOMO.cube",
    "in-LUMO.cube",
    "in-LUMOA.cube",
    "in-LUMOB.cube",
]

for d in glob.glob("cache/*/"):
    for f in glob.glob(os.path.join(d, "*")):
        fname = os.path.basename(f)
        if fname in KEEP_FILES and os.path.getsize(f) == 0:
            print(f"Empty file: {f}")
