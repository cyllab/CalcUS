import glob
import os
import shutil

KEEP_FILES = [
    "calc.inp",
    "calc.com",
    "calc.out",
    "calc.log",
    "calc.xyz",
    "calc2.xyz",
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
    "in.molden",
    "tda.dat",
    "wfn.xtb",
    "calc2.out",
]

for d in glob.glob("cache/*/"):
    for f in glob.glob(os.path.join(d, "*")):
        fname = os.path.basename(f)
        if fname not in KEEP_FILES:
            if os.path.isfile(f):
                os.remove(f)
            else:
                shutil.rmtree(f)
            print(f)
