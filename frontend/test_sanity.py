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
from .xtb_calculation import XtbCalculation
from .gen_calc import gen_calc

dir_path = os.path.dirname(os.path.realpath(__file__))

TESTS_DIR = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(TESTS_DIR, "scr")
EBROOTORCA = os.environ['EBROOTORCA']

class GaussianTests(TestCase):

    energies = []

    def setUp(self):
        call_command('init_static_obj')
        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)

        self.user = User.objects.create(username='User')
        self.profile = Profile.objects.get(user=self.user)

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

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

        E = self.run_calc(gaussian)
        self.assertTrue(self.known_energy(E, params))

    def test_sp_SE2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'PM6',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_SE3(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'PM7',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
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

        calc = gen_calc(params, self.profile)
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

        calc = gen_calc(params, self.profile)
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

        calc = gen_calc(params, self.profile)
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
                'solvation_model': 'SMD',
                'solvation_radii': 'SMD18'
                }

        calc = gen_calc(params, self.profile)
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
                'solvation_radii': 'Bondi',
                }

        calc = gen_calc(params, self.profile)
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
                'solvation_radii': 'Bondi',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_HF_PCM_UFF(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '0',
                'solvent': 'Chloroform',
                'solvation_model': 'PCM',
                'solvation_radii': 'UFF',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_HF_CPCM_UFF(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '0',
                'solvent': 'Chloroform',
                'solvation_model': 'CPCM',
                'solvation_radii': 'UFF',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))


    def test_sp_DFT_specifications(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2SVP',
                'charge': '-1',
                'specifications': 'nosymm 5D',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_DFT_specifications2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2SVP',
                'charge': '-1',
                'specifications': 'nosymm 6D',
                }

        calc = gen_calc(params, self.profile)
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

        calc = gen_calc(params, self.profile)
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

        calc = gen_calc(params, self.profile)
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

        calc = gen_calc(params, self.profile)
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

        calc = gen_calc(params, self.profile)
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

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_multiple_genecp_bs1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'TeI2.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'charge': '0',
                'basis_set': 'STO-3G',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_multiple_genecp_bs2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'TeI2.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'charge': '0',
                'basis_set': 'STO-3G',
                'custom_basis_sets': 'I=Def2-TZVPD;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_multiple_genecp_bs3(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'TeI2.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'charge': '0',
                'basis_set': 'STO-3G',
                'custom_basis_sets': 'Te=Def2-TZVPD;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

    def test_multiple_genecp_bs4(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'TeI2.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'charge': '0',
                'basis_set': 'STO-3G',
                'custom_basis_sets': 'Te=Def2-TZVPD;I=Def2-TZVPP;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        E = self.run_calc(gaussian)
        self.assertFalse(self.known_energy(E, params))

class OrcaTests(TestCase):

    energies = []

    def setUp(self):
        call_command('init_static_obj')
        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)

        self.user = User.objects.create(username='User')
        self.profile = Profile.objects.get(user=self.user)


    def tearDown(self):
        rmtree(SCR_DIR)

    def run_calc(self, obj):
        os.chdir(dir_path)
        t = time.time()
        c_dir = os.path.join(SCR_DIR, str(t))

        os.mkdir(c_dir)
        os.chdir(c_dir)

        with open("calc.inp", 'w') as out:
            out.write(obj.input_file)

        with open("calc.out", 'w') as out:
            ret = subprocess.run(shlex.split("{}/orca calc.inp".format(EBROOTORCA)), cwd=c_dir, stdout=out, stderr=out)

        if ret.returncode != 0:
            os.system("tail calc.out")
            return -1

        with open("{}/calc.out".format(c_dir)) as f:
            lines = f.readlines()
            ind = len(lines)-1

        while lines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
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


    def test_sp_SE1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '0',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)
        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

        self.assertTrue(self.known_energy(E, params))

    def test_sp_SE2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'PM3',
                'charge': '0',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_HF(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_HF_SMD(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'I.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'SMD',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_HF_SMD2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'I.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'SMD',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertTrue(self.known_energy(E, params))

    def test_sp_HF_SMD18(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'I.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'SMD',
                'solvation_radii': 'SMD18',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_HF_CPCM(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'CPCM',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))


    def test_gen_bs1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_gen_bs2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'custom_basis_sets': 'O=Def2-TZVPD;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_genecp_bs1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'charge': '+1',
                'basis_set': 'STO-3G',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_genecp_bs2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'charge': '+1',
                'basis_set': 'STO-3G',
                'custom_basis_sets': 'I=Def2-TZVPD;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_genecp_bs3(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'charge': '+1',
                'basis_set': 'STO-3G',
                'custom_basis_sets': 'I=Def2-TZVPD;H=Def2-TZVP;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_multiple_genecp_bs1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'TeI2.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'charge': '0',
                'basis_set': 'STO-3G',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_multiple_genecp_bs2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'TeI2.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'charge': '0',
                'basis_set': 'STO-3G',
                'custom_basis_sets': 'I=Def2-TZVPD;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_multiple_genecp_bs3(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'TeI2.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'charge': '0',
                'basis_set': 'STO-3G',
                'custom_basis_sets': 'Te=Def2-TZVPD;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

    def test_multiple_genecp_bs4(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'TeI2.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'charge': '0',
                'basis_set': 'STO-3G',
                'custom_basis_sets': 'Te=Def2-TZVPD;I=Def2-TZVPP;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        E = self.run_calc(orca)
        self.assertFalse(self.known_energy(E, params))

class CrestTests(TestCase):
    energies = []

    def setUp(self):
        call_command('init_static_obj')
        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)

        self.user = User.objects.create(username='User')
        self.profile = Profile.objects.get(user=self.user)


    def tearDown(self):
        rmtree(SCR_DIR)

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

    def run_calc(self, obj):
        os.chdir(dir_path)
        t = time.time()
        c_dir = os.path.join(SCR_DIR, str(t))

        os.mkdir(c_dir)
        os.chdir(c_dir)

        with open("in.xyz", 'w') as out:
            out.write(obj.calc.structure.xyz_structure)

        with open("calc.out", 'w') as out:
            ret = subprocess.run(shlex.split(obj.command), cwd=c_dir, stdout=out, stderr=out)

        if ret.returncode != 0:
            os.system("tail calc.out")
            return -1

        with open("{}/crest_best.xyz".format(c_dir)) as f:
            lines = f.readlines()

        return float(lines[1])

    def test_gfn2_conf_search(self):
        params = {
                'calc_name': 'test',
                'type': 'Conformational Search',
                'project': 'New Project',
                'software': 'xtb',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.xyz',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        E = self.run_calc(xtb)
        self.assertFalse(self.known_energy(E, params))

    def test_gfnff_conf_search(self):
        params = {
                'calc_name': 'test',
                'type': 'Conformational Search',
                'project': 'New Project',
                'software': 'xtb',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.xyz',
                'specifications': '--gfnff',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        E = self.run_calc(xtb)
        self.assertFalse(self.known_energy(E, params))

    def test_gfnff_conf_search2(self):
        params = {
                'calc_name': 'test',
                'type': 'Conformational Search',
                'project': 'New Project',
                'software': 'xtb',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.xyz',
                'specifications': '--gfnff',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        E = self.run_calc(xtb)
        self.assertTrue(self.known_energy(E, params))

    def test_gfnff_sp_conf_search(self):
        params = {
                'calc_name': 'test',
                'type': 'Conformational Search',
                'project': 'New Project',
                'software': 'xtb',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.xyz',
                'specifications': '--gfn2//gfnff',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        E = self.run_calc(xtb)
        self.assertFalse(self.known_energy(E, params))


class XtbTests(TestCase):
    energies = []

    def setUp(self):
        call_command('init_static_obj')
        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)

        self.user = User.objects.create(username='User')
        self.profile = Profile.objects.get(user=self.user)


    def tearDown(self):
        rmtree(SCR_DIR)

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

    def run_calc(self, obj):
        os.chdir(dir_path)
        t = time.time()
        c_dir = os.path.join(SCR_DIR, str(t))

        os.mkdir(c_dir)
        os.chdir(c_dir)

        with open("in.xyz", 'w') as out:
            out.write(obj.calc.structure.xyz_structure)

        with open("calc.out", 'w') as out:
            ret = subprocess.run(shlex.split(obj.command), cwd=c_dir, stdout=out, stderr=out)

        if ret.returncode != 0:
            os.system("tail calc.out")
            return -1

        with open("calc.out") as f:
            lines = f.readlines()
            ind = len(lines)-1

        while lines[ind].find("TOTAL ENERGY") == -1:
            ind -= 1

        return float(lines[ind].split()[3])

    def test_sp_gfn2(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'software': 'xtb',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.xyz',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        E = self.run_calc(xtb)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_gfn2_explicit(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'software': 'xtb',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.xyz',
                'specifications': '--gfn2',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        E = self.run_calc(xtb)
        self.assertTrue(self.known_energy(E, params))

    def test_sp_gfn1(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'software': 'xtb',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.xyz',
                'specifications': '--gfn1',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        E = self.run_calc(xtb)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_gfn0(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'software': 'xtb',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.xyz',
                'specifications': '--gfn0',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        E = self.run_calc(xtb)
        self.assertFalse(self.known_energy(E, params))

    def test_sp_gfnff(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'software': 'xtb',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.xyz',
                'specifications': '--gfnff',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        E = self.run_calc(xtb)
        self.assertFalse(self.known_energy(E, params))

