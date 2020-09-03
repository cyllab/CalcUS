import os
import time
from shutil import rmtree
import subprocess
import shlex

from .models import *
from django.core.management import call_command
from django.test import TestCase, Client
from .Gaussian_calculation import GaussianCalculation
from .ORCA_calculation import OrcaCalculation

dir_path = os.path.dirname(os.path.realpath(__file__))

TESTS_DIR = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(TESTS_DIR, "scr")

def gen_calc(params):
    step = BasicStep.objects.get(name=params['type'])

    charge = 0
    multiplicity = 1
    solvent = "Vacuum"
    solvation_model = ""
    basis_set = ""
    theory_level = ""
    method = ""
    misc = ""
    custom_basis_sets = ""
    density_fitting = ""

    if 'charge' in params.keys():
        charge = int(params['charge'])

    if 'multiplicity' in params.keys():
        multiplicity = int(params['multiplicity'])

    if 'solvent' in params.keys():
        solvent = params['solvent']

    if 'solvation_model' in params.keys():
        solvation_model = params['solvation_model']

    if 'basis_set' in params.keys():
        basis_set = params['basis_set']

    if 'custom_basis_sets' in params.keys():
        custom_basis_sets = params['custom_basis_sets']

    if 'density_fitting' in params.keys():
        density_fitting = params['density_fitting']

    if 'theory_level' in params.keys():
        theory_level = params['theory_level']

    if 'method' in params.keys():
        method = params['method']

    if 'misc' in params.keys():
        misc = params['misc']

    software = params['software']

    p = Parameters.objects.create(charge=charge, multiplicity=multiplicity, solvent=solvent, solvation_model=solvation_model, basis_set=basis_set, theory_level=theory_level, method=method, misc=misc, custom_basis_sets=custom_basis_sets, density_fitting=density_fitting)
    with open(os.path.join(TESTS_DIR, params['in_file'])) as f:
        lines = f.readlines()
        xyz_structure = ''.join(lines)

    s = Structure.objects.create(xyz_structure=xyz_structure)

    dummy = CalculationOrder.objects.create()
    calc = Calculation.objects.create(structure=s, step=step, parameters=p, order=dummy)

    if 'constraints' in params.keys():
        calc.constraints = params['constraints']

    return calc

class GaussianTests(TestCase):

    energies = []

    def setUp(self):
        call_command('init_static_obj')
        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)

    def tearDown(self):
        rmtree(SCR_DIR)

    def run_calc(self, obj):
        os.chdir(dir_path)
        t = time.time()
        c_dir = os.path.join(SCR_DIR, str(t))

        os.mkdir(c_dir)
        os.chdir(c_dir)

        with open("calc.com", 'w') as out:
            out.write(obj.input_file)

        ret = subprocess.run(shlex.split("g16 calc.com"), cwd=c_dir)

        if ret.returncode != 0:
            os.system("tail calc.log")
            return -1

        with open("{}/calc.log".format(c_dir)) as f:
            lines = f.readlines()
            ind = len(lines)-1

        while lines[ind].find("SCF Done") == -1:
            ind -= 1
        E = lines[ind].split()[4].strip()
        return E

    def known_energy(self, E, params):
        if E == -1:
            raise Exception("Invalid calculation")
        for entry in self.energies:
            if entry[1] == E:
                print("")
                print("Clash detected:")
                print(entry[0])
                print(params)
                print("")
                return True

        self.energies.append([params, E])
        return False


    def test_sp_SE(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

        self.assertTrue(self.known_energy(E, params))

    def test_sp_SE(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'PM6',
                'charge': '-1',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_SE(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'PM7',
                'charge': '-1',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_HF(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_HF_SMD(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'I.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'SMD',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_HF_SMD2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'I.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'SMD',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertTrue(self.known_energy(E, params))

    def test_sp_HF_SMD18(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'I.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'SMD18',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_HF_PCM(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'PCM',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_HF_CPCM(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'CPCM',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_DFT_misc(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2SVP',
                'charge': '-1',
                'misc': 'nosymm 5D',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_DFT_misc2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2SVP',
                'charge': '-1',
                'misc': 'nosymm 6D',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_gen_bs1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_gen_bs2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'custom_basis_sets': 'O=Def2-TZVPD;',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_genecp_bs1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'charge': '+1',
                'basis_set': 'STO-3G',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_genecp_bs2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'charge': '+1',
                'basis_set': 'STO-3G',
                'custom_basis_sets': 'I=Def2-TZVPD;',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_genecp_bs3(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'charge': '+1',
                'basis_set': 'STO-3G',
                'custom_basis_sets': 'I=Def2-TZVPD;H=Def2-TZVP;',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

