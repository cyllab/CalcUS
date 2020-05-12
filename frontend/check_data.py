import os

from constants import *

PAL = os.environ['OMP_NUM_THREADS'][0]
EBROOTORCA = os.environ['EBROOTORCA']

ORCA_TEMPLATE_BASIS_SET = """!sp {} {}
%pal
nprocs {}
end
*xyz 0 1
H 0.0 0.0 0.0
C 1.2 0.0 0.0
C 2.6 0.0 0.0
H 3.8 0.0 0.0
*"""

main = os.getcwd()
def check_ORCA_basis_sets():
    energies = {}
    for func in SOFTWARE_BASIS_SETS["ORCA"].keys():
        print(func)
        os.chdir(main)
        clean_func = func.replace('(', '_').replace(')', '_')

        os.system("mkdir -p tests/check_ORCA/{}".format(clean_func))
        os.chdir("tests/check_ORCA/{}".format(clean_func))

        with open("in.inp", 'w') as out:
            out.write(ORCA_TEMPLATE_BASIS_SET.format('M062X', func, PAL))
        ret = os.system("{}/orca in.inp > c2h2.out".format(EBROOTORCA))
        if ret == 0:
            with open("c2h2.out") as f:
                lines = f.readlines()
            ind = len(lines) - 1
            while lines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
                ind -= 1
            E = lines[ind].split()[-1]
            if E in energies.values():
                for key in energies.keys():
                    if energies[key] == E:
                        print("---Clash found between {} and {}".format(func, key))
            else:
                energies[func] = E
        else:
            print("---Error with {}".format(func))


if __name__ == "__main__":
    check_ORCA_basis_sets()
