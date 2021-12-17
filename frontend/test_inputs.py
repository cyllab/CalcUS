'''
This file of part of CalcUS.

Copyright (C) 2020-2021 Raphaël Robidas

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''


import os

from .models import *
from django.core.management import call_command
from django.test import TestCase, Client
from .Gaussian_calculation import GaussianCalculation
from .ORCA_calculation import OrcaCalculation
from .xtb_calculation import XtbCalculation
from .gen_calc import gen_calc

TESTS_DIR = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")

BLUE = '\033[94m'
GREEN = '\033[92m'
END = '\033[0m'

def blue(msg):
    print("{}{} {}".format(BLUE, msg, END))

def green(msg):
    print("{}{} {}".format(GREEN, msg, END))


class GaussianTests(TestCase):
    def setUp(self):
        call_command('init_static_obj')
        self.user = User.objects.create(username='User')
        self.profile = Profile.objects.get(user=self.user)

    def is_equivalent(self, ref, res):
        ref_lines = [i.strip() for i in ref.split('\n')]
        res_lines = [i.strip() for i in res.split('\n')]

        ind = 0
        while ref_lines[ind].find("#p") == -1:
            ind += 1

        ref_lines = ref_lines[ind:]

        ind = 0
        while res_lines[ind].find("#p") == -1:
            ind += 1

        res_lines = res_lines[ind:]

        if len(ref_lines) != len(res_lines):
            print("Different number of lines: {} and {}".format(len(ref_lines), len(res_lines)))
            print("----")
            blue(ref)
            print("----")
            green(res)
            print("----")
            return False

        for line1, line2 in zip(ref_lines, res_lines):
            if line1 != line2:
                print("")
                print("Difference found:")
                blue(line1)
                green(line2)
                print("")
                return False

        return True

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

        REF = """
        #p sp AM1

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

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

        REF = """
        #p sp HF/3-21G

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_HF_SMD(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'SMD',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(SMD, Solvent=chloroform)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

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
                'solvation_radii': 'SMD18',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(SMD, Solvent=chloroform, Read)

        CalcUS

        -1 1
        I 0.0 0.0 0.0

        modifysph

        Br 2.60
        I 2.74

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_HF_PCM_Bondi(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'chloroform',
                'solvation_model': 'PCM',
                'solvation_radii': 'Bondi',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(PCM, Solvent=chloroform, Read)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        Radii=Bondi

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_HF_PCM_UFF(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'PCM',
                'solvation_radii': 'UFF',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(PCM, Solvent=chloroform)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_HF_CPCM_Bondi(self):
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

        REF = """
        #p sp HF/3-21G SCRF(CPCM, Solvent=chloroform, Read)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        Radii=Bondi

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_HF_CPCM_UFF(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'CPCM',
                'solvation_radii': 'UFF',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(CPCM, Solvent=chloroform)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_solvent_synonyms1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'chcl3',
                'solvation_model': 'CPCM',
                'solvation_radii': 'UFF',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(CPCM, Solvent=chloroform)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_solvent_synonyms2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'meoh',
                'solvation_model': 'CPCM',
                'solvation_radii': 'UFF',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(CPCM, Solvent=methanol)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_invalid_solvation(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'ABC',
                }

        calc = gen_calc(params, self.profile)
        with self.assertRaises(Exception):
            gaussian = GaussianCalculation(calc)

    def test_sp_DFT(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp M062X/Def2SVP

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_DFT_specifications(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'nosymm 5D',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp M062X/Def2SVP nosymm 5d

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_superfluous_specifications(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'opt(loose)',
                }

        calc = gen_calc(params, self.profile)

        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp M062X/Def2SVP

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))
        self.assertEqual(gaussian.confirmed_specifications.strip(), '')


    def test_superfluous_specifications2(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'freq(noraman)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt M062X/Def2SVP

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))
        self.assertEqual(gaussian.confirmed_specifications.strip(), '')

    def test_duplicate_specifications(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'NoSymm NoSymm',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt M062X/Def2SVP nosymm

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_duplicate_specifications2(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'NoSymm NOSYMM',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt M062X/Def2SVP nosymm

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_opt_SE(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt AM1

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_opt_HF(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt HF/3-21G

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_opt_DFT(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt B3LYP/6-31+G(d,p)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))
        self.assertEqual(gaussian.confirmed_specifications.strip(), '')

    def test_freq_SE(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p freq AM1

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_freq_HF(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p freq HF/3-21G

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_freq_DFT(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p freq B3LYP/6-31+G(d,p)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    #opt mod SE and HF

    def test_scan_bond_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_1.4_10/1_2;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        B 1 2 S 10 0.03

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_scan_angle_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_90_10/2_1_3;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        A 2 1 3 S 10 -1.95

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_scan_dihedral_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_0_10/4_1_5_8;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        D 4 1 5 8 S 10 -17.99

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_scan_dihedral_DFT2(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_2_0_10/2_1_5_8;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        D 2 1 5 8 S 10 -5.99

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_scan_dihedral_DFT3(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_2_0_10/3_1_5_8;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        D 3 1 5 8 S 10 6.01

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_freeze_bond_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze/1_2;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        B 1 2 F

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_freeze_angle_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze/2_1_3;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        A 2 1 3 F

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_invalid_opt_mod(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': '',
                }

        calc = gen_calc(params, self.profile)
        with self.assertRaises(Exception):
            gaussian = GaussianCalculation(calc)

    def test_no_method(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': '',
                'basis_set': '6-31+G(d,p)',
                'constraints': '',
                }

        calc = gen_calc(params, self.profile)
        with self.assertRaises(Exception):
            gaussian = GaussianCalculation(calc)

    def test_freeze_dihedral_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze/4_1_5_8;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        D 4 1 5 8 F

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_freeze_dihedral_DFT2(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze/4_1_5_8;Freeze/1_2_3_4;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        D 4 1 5 8 F
        D 1 2 3 4 F

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_nmr_DFT(self):
        params = {
                'type': 'NMR Prediction',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p nmr B3LYP/6-31+G(d,p)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_ts_DFT(self):
        params = {
                'type': 'TS Optimisation',
                'in_file': 'mini_ts.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(ts, NoEigenTest, CalcFC) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        N   1.08764072053386     -0.33994563112543     -0.00972525479568
        H   1.99826836912112      0.05502842705407      0.00651240826058
        H   0.59453997172323     -0.48560162159600      0.83949232123172
        H   0.66998093862168     -0.58930117433261     -0.87511947469677

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_ts_DFT_df(self):
        params = {
                'type': 'TS Optimisation',
                'in_file': 'mini_ts.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': 'Def2SVP',
                'density_fitting': 'W06',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(ts, NoEigenTest, CalcFC) B3LYP/Def2SVP/W06

        CalcUS

        0 1
        N   1.08764072053386     -0.33994563112543     -0.00972525479568
        H   1.99826836912112      0.05502842705407      0.00651240826058
        H   0.59453997172323     -0.48560162159600      0.83949232123172
        H   0.66998093862168     -0.58930117433261     -0.87511947469677

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

        #combination tests

    def test_td_DFT(self):
        params = {
                'type': 'UV-Vis Calculation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p td M062X/Def2SVP

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_gen_bs(self):
        params = {
                'type': 'Geometrical Optimisation',
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

        REF = """
        #p opt B3LYP/Gen

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        C H 0
        6-31+G(d,p)
        ****
        O     0
        S    6   1.00
          27032.3826310              0.21726302465D-03
           4052.3871392              0.16838662199D-02
            922.32722710             0.87395616265D-02
            261.24070989             0.35239968808D-01
             85.354641351            0.11153519115
             31.035035245            0.25588953961
        S    2   1.00
             12.260860728            0.39768730901
              4.9987076005           0.24627849430
        S    1   1.00
              1.1703108158           1.0000000
        S    1   1.00
              0.46474740994          1.0000000
        S    1   1.00
              0.18504536357          1.0000000
        S    1   1.00
              0.70288026270D-01      1.0000000
        P    4   1.00
             63.274954801            0.60685103418D-02
             14.627049379            0.41912575824D-01
              4.4501223456           0.16153841088
              1.5275799647           0.35706951311
        P    1   1.00
              0.52935117943           .44794207502
        P    1   1.00
              0.17478421270           .24446069663
        P    1   1.00
              0.51112745706D-01      1.0000000
        D    1   1.00
              2.31400000             1.0000000
        D    1   1.00
              0.64500000             1.0000000
        D    1   1.00
              0.14696477366          1.0000000
        F    1   1.00
              1.42800000             1.0000000
        ****

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_irrelevant_gen_bs(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'custom_basis_sets': 'Cl=Def2-TZVPD;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_genecp_bs(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '+1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'custom_basis_sets': 'I=Def2-TZVPD;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt B3LYP/GenECP

        CalcUS

        1 1
        C         -3.06870       -2.28540        0.00000
        C         -1.67350       -2.28540        0.00000
        C         -0.97600       -1.07770        0.00000
        C         -1.67360        0.13090       -0.00120
        C         -3.06850        0.13080       -0.00170
        C         -3.76610       -1.07740       -0.00070
        H         -3.61840       -3.23770        0.00040
        H         -1.12400       -3.23790        0.00130
        H          0.12370       -1.07760        0.00060
        H         -1.12340        1.08300       -0.00130
        H         -4.86570       -1.07720       -0.00090
        I         -4.11890        1.94920       -0.00350
        C         -4.64360        2.85690       -1.82310
        C         -3.77180        3.76300       -2.42740
        C         -5.86360        2.55380       -2.42750
        C         -4.12020        4.36650       -3.63560
        H         -2.81040        4.00240       -1.95030
        C         -6.21180        3.15650       -3.63650
        H         -6.55070        1.83950       -1.95140
        C         -5.34050        4.06290       -4.24060
        H         -3.43340        5.08120       -4.11170
        H         -7.17360        2.91710       -4.11310
        H         -5.61500        4.53870       -5.19320

        C H 0
        6-31+G(d,p)
        ****
        I     0
        S    5   1.00
           5899.5791533              0.24188269271D-03
            898.54238765             0.15474041742D-02
            200.37237912             0.42836684457D-02
             31.418053840           -0.39417936275D-01
             15.645987838            0.96086691992
        S    2   1.00
             11.815741857            0.75961524091
              6.4614458287           0.42495501835
        S    1   1.00
              2.3838067579           1.0000000
        S    1   1.00
              1.1712089662           1.0000000
        S    1   1.00
              0.32115875757          1.0000000
        S    1   1.00
              0.12387919364          1.0000000
        S    1   1.00
              0.43491550641D-01      1.0000000
        P    3   1.00
            197.30030547             0.73951226905D-03
             20.061411349            0.66168450008D-01
              9.7631460485          -0.28554662348
        P    4   1.00
             12.984316904           -0.49096186164D-01
              3.6199503008           0.38914432482
              2.0232273090           0.65610817262
              1.0367490559           0.31803551647
        P    1   1.00
              0.45937816000          1.0000000
        P    1   1.00
              0.19116532928          1.0000000
        P    1   1.00
              0.74878813023D-01      1.0000000
        P    1   1.00
              0.21653491846D-01      1.0000000
        D    6   1.00
            119.12671745             0.82596039573D-03
             33.404240134            0.68377675770D-02
             17.805918203           -0.10308158997D-01
              4.8990510353           0.22670457658
              2.4516753106           0.44180113937
              1.1820693432           0.36775472225
        D    1   1.00
              0.52923110068          1.0000000
        D    1   1.00
              0.17000000000          1.0000000
        D    1   1.00
              0.61341708807D-01      1.0000000
        F    1   1.00
              2.1800000              1.0000000
        F    1   1.00
              0.44141808             1.0000000
        ****

        I     0
        I-ECP     3     28
        f potential
          4
        2     19.45860900           -21.84204000
        2     19.34926000           -28.46819100
        2      4.82376700            -0.24371300
        2      4.88431500            -0.32080400
        s-f potential
          7
        2     40.01583500            49.99429300
        2     17.42974700           281.02531700
        2      9.00548400            61.57332600
        2     19.45860900            21.84204000
        2     19.34926000            28.46819100
        2      4.82376700             0.24371300
        2      4.88431500             0.32080400
        p-f potential
          8
        2     15.35546600            67.44284100
        2     14.97183300           134.88113700
        2      8.96016400            14.67505100
        2      8.25909600            29.37566600
        2     19.45860900            21.84204000
        2     19.34926000            28.46819100
        2      4.82376700             0.24371300
        2      4.88431500             0.32080400
        d-f potential
          10
        2     15.06890800            35.43952900
        2     14.55532200            53.17605700
        2      6.71864700             9.06719500
        2      6.45639300            13.20693700
        2      1.19177900             0.08933500
        2      1.29115700             0.05238000
        2     19.45860900            21.84204000
        2     19.34926000            28.46819100
        2      4.82376700             0.24371300
        2      4.88431500             0.32080400

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_genecp_bs_multiple_atoms(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '+1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'custom_basis_sets': 'I=Def2-TZVPD;H=Def2-TZVPD;C=Def2-TZVPD;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt B3LYP/GenECP

        CalcUS

        1 1
        C         -3.06870       -2.28540        0.00000
        C         -1.67350       -2.28540        0.00000
        C         -0.97600       -1.07770        0.00000
        C         -1.67360        0.13090       -0.00120
        C         -3.06850        0.13080       -0.00170
        C         -3.76610       -1.07740       -0.00070
        H         -3.61840       -3.23770        0.00040
        H         -1.12400       -3.23790        0.00130
        H          0.12370       -1.07760        0.00060
        H         -1.12340        1.08300       -0.00130
        H         -4.86570       -1.07720       -0.00090
        I         -4.11890        1.94920       -0.00350
        C         -4.64360        2.85690       -1.82310
        C         -3.77180        3.76300       -2.42740
        C         -5.86360        2.55380       -2.42750
        C         -4.12020        4.36650       -3.63560
        H         -2.81040        4.00240       -1.95030
        C         -6.21180        3.15650       -3.63650
        H         -6.55070        1.83950       -1.95140
        C         -5.34050        4.06290       -4.24060
        H         -3.43340        5.08120       -4.11170
        H         -7.17360        2.91710       -4.11310
        H         -5.61500        4.53870       -5.19320

        I     0
        S    5   1.00
           5899.5791533              0.24188269271D-03
            898.54238765             0.15474041742D-02
            200.37237912             0.42836684457D-02
             31.418053840           -0.39417936275D-01
             15.645987838            0.96086691992
        S    2   1.00
             11.815741857            0.75961524091
              6.4614458287           0.42495501835
        S    1   1.00
              2.3838067579           1.0000000
        S    1   1.00
              1.1712089662           1.0000000
        S    1   1.00
              0.32115875757          1.0000000
        S    1   1.00
              0.12387919364          1.0000000
        S    1   1.00
              0.43491550641D-01      1.0000000
        P    3   1.00
            197.30030547             0.73951226905D-03
             20.061411349            0.66168450008D-01
              9.7631460485          -0.28554662348
        P    4   1.00
             12.984316904           -0.49096186164D-01
              3.6199503008           0.38914432482
              2.0232273090           0.65610817262
              1.0367490559           0.31803551647
        P    1   1.00
              0.45937816000          1.0000000
        P    1   1.00
              0.19116532928          1.0000000
        P    1   1.00
              0.74878813023D-01      1.0000000
        P    1   1.00
              0.21653491846D-01      1.0000000
        D    6   1.00
            119.12671745             0.82596039573D-03
             33.404240134            0.68377675770D-02
             17.805918203           -0.10308158997D-01
              4.8990510353           0.22670457658
              2.4516753106           0.44180113937
              1.1820693432           0.36775472225
        D    1   1.00
              0.52923110068          1.0000000
        D    1   1.00
              0.17000000000          1.0000000
        D    1   1.00
              0.61341708807D-01      1.0000000
        F    1   1.00
              2.1800000              1.0000000
        F    1   1.00
              0.44141808             1.0000000
        ****
        H     0
        S    3   1.00
             34.0613410              0.60251978D-02
              5.1235746              0.45021094D-01
              1.1646626              0.20189726
        S    1   1.00
              0.32723041             1.0000000
        S    1   1.00
              0.10307241             1.0000000
        P    1   1.00
              0.8000000              1.0000000
        P    1   1.00
              0.95774129632D-01      1.0000000
        ****
        C     0
        S    6   1.00
          13575.3496820              0.22245814352D-03
           2035.2333680              0.17232738252D-02
            463.22562359             0.89255715314D-02
            131.20019598             0.35727984502D-01
             42.853015891            0.11076259931
             15.584185766            0.24295627626
        S    2   1.00
              6.2067138508           0.41440263448
              2.5764896527           0.23744968655
        S    1   1.00
              0.57696339419          1.0000000
        S    1   1.00
              0.22972831358          1.0000000
        S    1   1.00
              0.95164440028D-01      1.0000000
        S    1   1.00
              0.48475401370D-01      1.0000000
        P    4   1.00
             34.697232244            0.53333657805D-02
              7.9582622826           0.35864109092D-01
              2.3780826883           0.14215873329
              0.81433208183          0.34270471845
        P    1   1.00
              0.28887547253           .46445822433
        P    1   1.00
              0.10056823671           .24955789874
        D    1   1.00
              1.09700000             1.0000000
        D    1   1.00
              0.31800000             1.0000000
        D    1   1.00
              0.90985336424D-01      1.0000000
        F    1   1.00
              0.76100000             1.0000000
        ****

        I     0
        I-ECP     3     28
        f potential
          4
        2     19.45860900           -21.84204000
        2     19.34926000           -28.46819100
        2      4.82376700            -0.24371300
        2      4.88431500            -0.32080400
        s-f potential
          7
        2     40.01583500            49.99429300
        2     17.42974700           281.02531700
        2      9.00548400            61.57332600
        2     19.45860900            21.84204000
        2     19.34926000            28.46819100
        2      4.82376700             0.24371300
        2      4.88431500             0.32080400
        p-f potential
          8
        2     15.35546600            67.44284100
        2     14.97183300           134.88113700
        2      8.96016400            14.67505100
        2      8.25909600            29.37566600
        2     19.45860900            21.84204000
        2     19.34926000            28.46819100
        2      4.82376700             0.24371300
        2      4.88431500             0.32080400
        d-f potential
          10
        2     15.06890800            35.43952900
        2     14.55532200            53.17605700
        2      6.71864700             9.06719500
        2      6.45639300            13.20693700
        2      1.19177900             0.08933500
        2      1.29115700             0.05238000
        2     19.45860900            21.84204000
        2     19.34926000            28.46819100
        2      4.82376700             0.24371300
        2      4.88431500             0.32080400

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_multiple_ecp(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'AuI.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'custom_basis_sets': 'I=Def2-TZVPD;Au=Def2-TZVPD;',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt B3LYP/GenECP

        CalcUS

        0 1
        Au        -9.27600       -1.06330        0.00000
        I         -6.60600       -1.06330        0.00000

        I     0
        S    5   1.00
        5899.5791533              0.24188269271D-03
        898.54238765             0.15474041742D-02
        200.37237912             0.42836684457D-02
        31.418053840           -0.39417936275D-01
        15.645987838            0.96086691992
        S    2   1.00
        11.815741857            0.75961524091
        6.4614458287           0.42495501835
        S    1   1.00
        2.3838067579           1.0000000
        S    1   1.00
        1.1712089662           1.0000000
        S    1   1.00
        0.32115875757          1.0000000
        S    1   1.00
        0.12387919364          1.0000000
        S    1   1.00
        0.43491550641D-01      1.0000000
        P    3   1.00
        197.30030547             0.73951226905D-03
        20.061411349            0.66168450008D-01
        9.7631460485          -0.28554662348
        P    4   1.00
        12.984316904           -0.49096186164D-01
        3.6199503008           0.38914432482
        2.0232273090           0.65610817262
        1.0367490559           0.31803551647
        P    1   1.00
        0.45937816000          1.0000000
        P    1   1.00
        0.19116532928          1.0000000
        P    1   1.00
        0.74878813023D-01      1.0000000
        P    1   1.00
        0.21653491846D-01      1.0000000
        D    6   1.00
        119.12671745             0.82596039573D-03
        33.404240134            0.68377675770D-02
        17.805918203           -0.10308158997D-01
        4.8990510353           0.22670457658
        2.4516753106           0.44180113937
        1.1820693432           0.36775472225
        D    1   1.00
        0.52923110068          1.0000000
        D    1   1.00
        0.17000000000          1.0000000
        D    1   1.00
        0.61341708807D-01      1.0000000
        F    1   1.00
        2.1800000              1.0000000
        F    1   1.00
        0.44141808             1.0000000
        ****
        Au     0
        S    3   1.00
        30.000000000            0.20749231108
        27.000000000           -0.33267893394
        14.746824331            0.38302817958
        S    1   1.00
        5.6017248938           1.0000000
        S    1   1.00
        1.3874162443           1.0000000
        S    1   1.00
        0.62923031957          1.0000000
        S    1   1.00
        0.14027517613          1.0000000
        S    1   1.00
        0.49379413761D-01      1.0000000
        P    4   1.00
        15.500000000            0.15001711880
        14.000000000           -0.23609813183
        6.4227368205           0.31458896948
        1.6595601681          -0.57279670446
        P    1   1.00
        0.79402913993          1.0000000
        P    1   1.00
        0.35125155397          1.0000000
        P    1   1.00
        0.11801737494          1.0000000
        P    1   1.00
        0.45000000000D-01      1.0000000
        D    4   1.00
        9.5524098656           0.40145559502D-01
        7.2698886937          -0.93690906606D-01
        1.7746496789           0.31746282317
        0.79960541055          0.46795192483
        D    1   1.00
        0.33252279372          1.0000000
        D    1   1.00
        0.12445133105          1.0000000
        F    1   1.00
        0.7248200              1.0000000
        ****

        I     0
        I-ECP     3     28
        f potential
        4
        2     19.45860900           -21.84204000
        2     19.34926000           -28.46819100
        2      4.82376700            -0.24371300
        2      4.88431500            -0.32080400
        s-f potential
        7
        2     40.01583500            49.99429300
        2     17.42974700           281.02531700
        2      9.00548400            61.57332600
        2     19.45860900            21.84204000
        2     19.34926000            28.46819100
        2      4.82376700             0.24371300
        2      4.88431500             0.32080400
        p-f potential
        8
        2     15.35546600            67.44284100
        2     14.97183300           134.88113700
        2      8.96016400            14.67505100
        2      8.25909600            29.37566600
        2     19.45860900            21.84204000
        2     19.34926000            28.46819100
        2      4.82376700             0.24371300
        2      4.88431500             0.32080400
        d-f potential
        10
        2     15.06890800            35.43952900
        2     14.55532200            53.17605700
        2      6.71864700             9.06719500
        2      6.45639300            13.20693700
        2      1.19177900             0.08933500
        2      1.29115700             0.05238000
        2     19.45860900            21.84204000
        2     19.34926000            28.46819100
        2      4.82376700             0.24371300
        2      4.88431500             0.32080400
        AU     0
        AU-ECP     3     60
        f potential
        2
        2      4.78982000            30.49008890
        2      2.39491000             5.17107381
        s-f potential
        4
        2     13.20510000           426.84667920
        2      6.60255000            37.00708285
        2      4.78982000           -30.49008890
        2      2.39491000            -5.17107381
        p-f potential
        4
        2     10.45202000           261.19958038
        2      5.22601000            26.96249604
        2      4.78982000           -30.49008890
        2      2.39491000            -5.17107381
        d-f potential
        4
        2      7.85110000           124.79066561
        2      3.92555000            16.30072573
        2      4.78982000           -30.49008890
        2      2.39491000            -5.17107381

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_global_specification(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'SCF(Tight)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp M062X/Def2SVP scf(tight)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))
        self.assertEqual(gaussian.confirmed_specifications.strip(), 'scf(tight)')

    def test_multiple_global_specification(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'SCF(Tight) SCF(XQC)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp M062X/Def2SVP scf(tight,xqc)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))
        self.assertEqual(gaussian.confirmed_specifications.strip(), 'scf(tight,xqc)')

    def test_multiple_global_specification2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'SCF(Tight,XQC)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp M062X/Def2SVP scf(tight,xqc)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))
        self.assertEqual(gaussian.confirmed_specifications.strip(), 'scf(tight,xqc)')

    def test_multiple_global_specification3(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'SCF(Tight, XQC)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp M062X/Def2SVP scf(tight,xqc)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))
        self.assertEqual(gaussian.confirmed_specifications.strip(), 'scf(tight,xqc)')


    def test_cmd_specification(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'opt(MaxStep=5)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(maxstep=5) M062X/Def2SVP

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_multiple_cmd_specifications(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'opt(MaxStep=5) opt(Tight)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(maxstep=5, tight) M062X/Def2SVP

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_both_specifications(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'opt(MaxStep=5) SCF(Tight)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(maxstep=5) M062X/Def2SVP scf(tight)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_specifications_mixed(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'opt(MaxStep=5) opt(Tight) nosymm 5D',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(maxstep=5, tight) M062X/Def2SVP nosymm 5d

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_specifications_mixed2(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'opt(MaxStep=5,Tight) nosymm 5D',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(maxstep=5, tight) M062X/Def2SVP nosymm 5d

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_default_append1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                }

        user = User.objects.create(username='tmp')
        profile = Profile.objects.get(user=user)
        profile.default_gaussian = "Int(UltraFineGrid)"
        profile.save()

        calc = gen_calc(params, profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp M062X/Def2SVP int(ultrafinegrid)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_default_append2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                }

        user = User.objects.create(username='tmp')
        profile = Profile.objects.get(user=user)
        profile.default_gaussian = "Int(UltraFineGrid) SCF(Tight)"
        profile.save()

        calc = gen_calc(params, profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp M062X/Def2SVP int(ultrafinegrid) scf(tight)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_default_append_bis(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                }

        user = User.objects.create(username='tmp')
        profile = Profile.objects.get(user=user)
        profile.default_gaussian = "Int(UltraFineGrid)"
        profile.save()

        calc = gen_calc(params, profile)
        gaussian = GaussianCalculation(calc)
        _ = gaussian.input_file

        REF = """
        #p sp M062X/Def2SVP int(ultrafinegrid)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_default_append_default_redundant(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'Int(ultrafinegrid) nosymm',
                }

        user = User.objects.create(username='tmp')
        profile = Profile.objects.get(user=user)
        profile.default_gaussian = "Int(UltraFineGrid) NOSYMM"
        profile.save()

        calc = gen_calc(params, profile)
        gaussian = GaussianCalculation(calc)
        _ = gaussian.input_file

        REF = """
        #p sp M062X/Def2SVP nosymm int(ultrafinegrid)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_default_append_and_specification(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'opt(MaxStep=5)',
                }

        user = User.objects.create(username='tmp')
        profile = Profile.objects.get(user=user)
        profile.default_gaussian = "Int(UltraFineGrid) SCF(Tight)"
        profile.save()

        calc = gen_calc(params, profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(maxstep=5) M062X/Def2SVP int(ultrafinegrid) scf(tight)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_invalid_specification(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'opt(MaxStep=5,Tight nosymm 5D',
                }

        calc = gen_calc(params, self.profile)
        with self.assertRaises(Exception):
            gaussian = GaussianCalculation(calc)

    def test_special_char(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': '!#',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt M062X/Def2SVP

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_confirmed_specification_not_step(self):
        params = {
                'type': 'Constrained Optimisation',
                'constraints': 'Freeze/1_2_3;',
                'in_file': 'CH4.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '0',
                'specifications': 'pop(nbo)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        self.assertEqual(gaussian.confirmed_specifications, 'pop(nbo)')

    def test_cmd_specification_td(self):
        params = {
                'type': 'UV-Vis Calculation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'td(NStates=5)',
                }

        calc = gen_calc(params, self.profile)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p td(nstates=5) M062X/Def2SVP

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))


class OrcaTests(TestCase):
    def setUp(self):
        call_command('init_static_obj')
        self.user = User.objects.create(username='User')
        self.profile = Profile.objects.get(user=self.user)

    def is_equivalent(self, ref, res):
        ref_lines = [i.strip() for i in ref.split('\n')]
        res_lines = [i.strip() for i in res.split('\n')]

        ind = 0
        while ref_lines[ind].strip() == '':
            ind += 1

        ind2 = len(ref_lines) - 1
        while ref_lines[ind2].strip() == '':
            ind2 -= 1

        ref_lines = ref_lines[ind:ind2+1]

        ind = 0
        while res_lines[ind].strip() == '':
            ind += 1

        res_lines = res_lines[ind:]

        if len(ref_lines) != len(res_lines):
            print("Different number of lines: {} and {}".format(len(ref_lines), len(res_lines)))
            print("----")
            blue(ref)
            print("----")
            green(res)
            print("----")
            return False

        for line1, line2 in zip(ref_lines, res_lines):
            if line1 != line2:
                if line1.find("nprocs") != -1:
                    pass
                else:
                    print("")
                    print("Difference found:")
                    blue(line1)
                    green(line2)
                    print("")
                    return False

        return True

    def test_sp_SE(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP AM1
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

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

        REF = """
        !SP HF 3-21G
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_sp_HF_SMD(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'SMD',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP HF 3-21G
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        %cpcm
        smd true
        SMDsolvent "chloroform"
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

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

        REF = """
        !SP HF 3-21G
        *xyz -1 1
        I 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        %cpcm
        smd true
        SMDsolvent "chloroform"
        radius[53] 2.74
        radius[35] 2.60
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))


    def test_solvation_octanol_smd(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'octanol',
                'solvation_model': 'SMD',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP HF 3-21G
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        %cpcm
        smd true
        SMDsolvent "1-octanol"
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

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

        REF = """
        !SP HF 3-21G CPCM(chloroform)
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_solvent_synonym(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'CHCL3',
                'solvation_model': 'SMD',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP HF 3-21G
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        %cpcm
        smd true
        SMDsolvent "chloroform"
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))


    def test_solvation_octanol_cpcm1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'octanol',
                'solvation_model': 'CPCM',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP HF 3-21G CPCM(octanol)
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_solvation_octanol_cpcm2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': '1-octanol',
                'solvation_model': 'CPCM',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP HF 3-21G CPCM(octanol)
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_invalid_solvation(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'ABC',
                }

        calc = gen_calc(params, self.profile)
        with self.assertRaises(Exception):
            orca = OrcaCalculation(calc)

    def test_sp_DFT(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP M062X Def2-SVP
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_sp_DFT_specifications(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'TightSCF',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP M062X Def2-SVP tightscf
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_sp_DFT_multiple_specifications(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'TightSCF GRID6',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP M062X Def2-SVP tightscf grid6
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_sp_DFT_duplicate_specifications(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'tightscf TightSCF GRID6',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP M062X Def2-SVP tightscf grid6
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_default_append1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                }

        user = User.objects.create(username='tmp')
        profile = Profile.objects.get(user=user)
        profile.default_orca = "TightSCF Grid6"
        profile.save()

        calc = gen_calc(params, profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP M062X Def2-SVP tightscf grid6
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_duplicate_specifications_profile(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'tightscf grid6',
                }

        user = User.objects.create(username='tmp')
        profile = Profile.objects.get(user=user)
        profile.default_orca = "TightSCF Grid6"
        profile.save()

        calc = gen_calc(params, profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP M062X Def2-SVP tightscf grid6
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_sp_MP2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'RI-MP2',
                'basis_set': 'cc-pVTZ',
                'charge': '-1',
                'specifications': 'cc-pVTZ/C',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP RI-MP2 cc-pVTZ cc-pvtz/c
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_opt_SE(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT AM1
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_opt_HF(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT HF 3-21G
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_opt_DFT(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_freq_SE(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !FREQ AM1
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_freq_HF(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !FREQ HF 3-21G
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_freq_DFT(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !FREQ B3LYP 6-31+G(d,p)
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    #opt mod SE and HF

    def test_scan_bond_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_1.4_10/1_2;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Scan
        B 0 1 = 9, 1.4, 10
        end
        end
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_invalid_opt_mod(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': '',
                }

        calc = gen_calc(params, self.profile)
        with self.assertRaises(Exception):
            orca = OrcaCalculation(calc)

    def test_no_method(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': '',
                'basis_set': '6-31+G(d,p)',
                'constraints': '',
                }

        calc = gen_calc(params, self.profile)
        with self.assertRaises(Exception):
            orca = OrcaCalculation(calc)

    def test_scan_angle_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_90_10/2_1_3;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Scan
        A 1 0 2 = 9, 90, 10
        end
        end
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_scan_dihedral_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_0_10/4_1_5_8;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Scan
        D 3 0 4 7 = 9, 0, 10
        end
        end
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_freeze_bond_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze/1_2;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Constraints
        { B 0 1 C }
        end
        end
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_freeze_angle_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze/2_1_3;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Constraints
        { A 1 0 2 C }
        end
        end
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))


    def test_freeze_dihedral_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze/4_1_5_8;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Constraints
        { D 3 0 4 7 C }
        end
        end
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_nmr_DFT(self):
        params = {
                'type': 'NMR Prediction',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !NMR B3LYP 6-31+G(d,p)
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_irrelevant_gen_bs(self):
        params = {
                'type': 'NMR Prediction',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'custom_basis_sets': 'N=Def2-SVP;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !NMR B3LYP 6-31+G(d,p)
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_ts_DFT(self):
        params = {
                'type': 'TS Optimisation',
                'in_file': 'mini_ts.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPTTS B3LYP 6-31+G(d,p)
        *xyz 0 1
        N   1.08764072053386     -0.33994563112543     -0.00972525479568
        H   1.99826836912112      0.05502842705407      0.00651240826058
        H   0.59453997172323     -0.48560162159600      0.83949232123172
        H   0.66998093862168     -0.58930117433261     -0.87511947469677
        *
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

        #combination tests

    def test_ts_DFT_custom_bs(self):
        params = {
                'type': 'TS Optimisation',
                'in_file': 'mini_ts.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'custom_basis_sets': 'N=Def2-SVP;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPTTS B3LYP 6-31+G(d,p)
        *xyz 0 1
        N   1.08764072053386     -0.33994563112543     -0.00972525479568
        H   1.99826836912112      0.05502842705407      0.00651240826058
        H   0.59453997172323     -0.48560162159600      0.83949232123172
        H   0.66998093862168     -0.58930117433261     -0.87511947469677
        *
        %basis
        newgto N
        S   5
        1      1712.8415853             -0.53934125305E-02
        2       257.64812677            -0.40221581118E-01
        3        58.458245853           -0.17931144990
        4        16.198367905           -0.46376317823
        5         5.0052600809          -0.44171422662
        S   1
        1         0.58731856571          1.0000000
        S   1
        1         0.18764592253          1.0000000
        P   3
        1        13.571470233           -0.40072398852E-01
        2         2.9257372874          -0.21807045028
        3         0.79927750754         -0.51294466049
        P   1
        1         0.21954348034          1.0000000
        D   1
        1         1.0000000              1.0000000
        end
        end
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_opt_DFT_custom_bs_ecp(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '+1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'custom_basis_sets': 'I=Def2-TZVPD;',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 1 1
        C         -3.06870       -2.28540        0.00000
        C         -1.67350       -2.28540        0.00000
        C         -0.97600       -1.07770        0.00000
        C         -1.67360        0.13090       -0.00120
        C         -3.06850        0.13080       -0.00170
        C         -3.76610       -1.07740       -0.00070
        H         -3.61840       -3.23770        0.00040
        H         -1.12400       -3.23790        0.00130
        H          0.12370       -1.07760        0.00060
        H         -1.12340        1.08300       -0.00130
        H         -4.86570       -1.07720       -0.00090
        I         -4.11890        1.94920       -0.00350
        C         -4.64360        2.85690       -1.82310
        C         -3.77180        3.76300       -2.42740
        C         -5.86360        2.55380       -2.42750
        C         -4.12020        4.36650       -3.63560
        H         -2.81040        4.00240       -1.95030
        C         -6.21180        3.15650       -3.63650
        H         -6.55070        1.83950       -1.95140
        C         -5.34050        4.06290       -4.24060
        H         -3.43340        5.08120       -4.11170
        H         -7.17360        2.91710       -4.11310
        H         -5.61500        4.53870       -5.19320
        *
        %basis
        newgto I
        S   5
        1      5899.5791533              0.24188269271E-03
        2       898.54238765             0.15474041742E-02
        3       200.37237912             0.42836684457E-02
        4        31.418053840           -0.39417936275E-01
        5        15.645987838            0.96086691992
        S   2
        1        11.815741857            0.75961524091
        2         6.4614458287           0.42495501835
        S   1
        1         2.3838067579           1.0000000
        S   1
        1         1.1712089662           1.0000000
        S   1
        1         0.32115875757          1.0000000
        S   1
        1         0.12387919364          1.0000000
        S   1
        1         0.43491550641E-01      1.0000000
        P   3
        1       197.30030547             0.73951226905E-03
        2        20.061411349            0.66168450008E-01
        3         9.7631460485          -0.28554662348
        P   4
        1        12.984316904           -0.49096186164E-01
        2         3.6199503008           0.38914432482
        3         2.0232273090           0.65610817262
        4         1.0367490559           0.31803551647
        P   1
        1         0.45937816000          1.0000000
        P   1
        1         0.19116532928          1.0000000
        P   1
        1         0.74878813023E-01      1.0000000
        P   1
        1         0.21653491846E-01      1.0000000
        D   6
        1       119.12671745             0.82596039573E-03
        2        33.404240134            0.68377675770E-02
        3        17.805918203           -0.10308158997E-01
        4         4.8990510353           0.22670457658
        5         2.4516753106           0.44180113937
        6         1.1820693432           0.36775472225
        D   1
        1         0.52923110068          1.0000000
        D   1
        1         0.17000000000          1.0000000
        D   1
        1         0.61341708807E-01      1.0000000
        F   1
        1         2.1800000              1.0000000
        F   1
        1         0.44141808             1.0000000
        end

        NewECP I
          N_core 28
          lmax f
          s 7
           1     40.01583500    49.99429300 2
           2     17.42974700   281.02531700 2
           3      9.00548400    61.57332600 2
           4     19.45860900    21.84204000 2
           5     19.34926000    28.46819100 2
           6      4.82376700     0.24371300 2
           7      4.88431500     0.32080400 2
          p 8
           1     15.35546600    67.44284100 2
           2     14.97183300   134.88113700 2
           3      8.96016400    14.67505100 2
           4      8.25909600    29.37566600 2
           5     19.45860900    21.84204000 2
           6     19.34926000    28.46819100 2
           7      4.82376700     0.24371300 2
           8      4.88431500     0.32080400 2
          d 10
           1     15.06890800    35.43952900 2
           2     14.55532200    53.17605700 2
           3      6.71864700     9.06719500 2
           4      6.45639300    13.20693700 2
           5      1.19177900     0.08933500 2
           6      1.29115700     0.05238000 2
           7     19.45860900    21.84204000 2
           8     19.34926000    28.46819100 2
           9      4.82376700     0.24371300 2
           10     4.88431500     0.32080400 2
          f 4
           1     19.45860900   -21.84204000 2
           2     19.34926000   -28.46819100 2
           3      4.82376700    -0.24371300 2
           4      4.88431500    -0.32080400 2
        end

        end
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_NEB(self):
        params = {
                'type': 'Minimum Energy Path',
                'in_file': 'elimination_substrate.xyz',
                'auxiliary_file': 'elimination_product.xyz',
                'software': 'xtb',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        INPUT = """!NEB
        *xyz 0 1
        C         -0.74277        0.14309        0.12635
        C          0.71308       -0.12855       -0.16358
        Cl         0.90703       -0.47793       -1.61303
        H         -0.84928        0.38704        1.20767
        H         -1.36298       -0.72675       -0.06978
        H         -1.11617        0.99405       -0.43583
        H          1.06397       -0.95639        0.44985
        H          1.30839        0.75217        0.07028
        O         -0.91651        0.74066        3.00993
        H         -1.82448        0.94856        3.28105
        *
        %neb
        neb_end_xyzfile "struct2.xyz"
        nimages 8
        end
        %pal
        nprocs 8
        end

        """
        self.assertTrue(self.is_equivalent(INPUT, orca.input_file))

    def test_NEB2(self):
        params = {
                'type': 'Minimum Energy Path',
                'in_file': 'elimination_substrate.xyz',
                'auxiliary_file': 'elimination_product.xyz',
                'software': 'xtb',
                'specifications': '--nimages 12',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        INPUT = """!NEB
        *xyz 0 1
        C         -0.74277        0.14309        0.12635
        C          0.71308       -0.12855       -0.16358
        Cl         0.90703       -0.47793       -1.61303
        H         -0.84928        0.38704        1.20767
        H         -1.36298       -0.72675       -0.06978
        H         -1.11617        0.99405       -0.43583
        H          1.06397       -0.95639        0.44985
        H          1.30839        0.75217        0.07028
        O         -0.91651        0.74066        3.00993
        H         -1.82448        0.94856        3.28105
        *
        %neb
        neb_end_xyzfile "struct2.xyz"
        nimages 12
        end
        %pal
        nprocs 8
        end

        """
        self.assertTrue(self.is_equivalent(INPUT, orca.input_file))

    def test_hirshfeld_pop(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'specifications': 'phirshfeld',
                }

        calc = gen_calc(params, self.profile)
        orca = OrcaCalculation(calc)

        REF = """
        !SP M062X Def2-SVP
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %output
        Print[ P_Hirshfeld] 1
        end
        %pal
        nprocs 8
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

class XtbTests(TestCase):
    def setUp(self):
        call_command('init_static_obj')
        self.user = User.objects.create(username='User')
        self.profile = Profile.objects.get(user=self.user)

    def is_equivalent(self, ref, res):
        ref_lines = [i.strip() for i in ref.split('\n')]
        res_lines = [i.strip() for i in res.split('\n')]

        if len(ref_lines) != len(res_lines):
            print("Different number of lines: {} and {}".format(len(ref_lines), len(res_lines)))
            print("----")
            blue(ref)
            print("----")
            green(res)
            print("----")
            return False

        for line1, line2 in zip(ref_lines, res_lines):
            if line1 != line2:
                print("")
                print("Difference found:")
                blue(line1)
                green(line2)
                print("")
                return False

        return True

    def test_sp_basic(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_sp_charge(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'xtb',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --chrg -1"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_sp_multiplicity(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'xtb',
                'multiplicity': '2',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --uhf 2"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_sp_charge_multiplicity(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'xtb',
                'multiplicity': '3',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --chrg -1 --uhf 3"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_opt_charge(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'xtb',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --opt tight --chrg -1"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_freq_charge(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'xtb',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --hess --chrg -1"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_solvent(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'xtb',
                'solvation_model': 'GBSA',
                'solvent': 'chcl3',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --hess -g chcl3 --chrg -1"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_solvent_ALPB(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'xtb',
                'solvent': 'chcl3',
                'solvation_model': 'ALPB',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --hess --alpb chcl3 --chrg -1"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_solvent_synonym(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'xtb',
                'solvent': 'chloroform',
                'solvation_model': 'GBSA',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --hess -g chcl3 --chrg -1"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_solvent_invalid(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'xtb',
                'solvent': 'octanol',
                'charge': '-1',
                }

        calc = gen_calc(params, self.profile)

        with self.assertRaises(Exception):
            xtb = XtbCalculation(calc)

        calc = Calculation.objects.get(pk=calc.id)

        self.assertIn('invalid solvent', calc.error_message.lower())

    def test_scan(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'constraints': 'Scan_9_1.4_10/1_2;',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --opt tight --input input"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

        INPUT = """$constrain
        force constant=1.0
        distance: 1, 2, auto
        $scan
        1: 9, 1.4, 10
        """
        self.assertTrue(self.is_equivalent(INPUT, xtb.option_file))

    def test_freeze(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'constraints': 'Freeze/1_2;',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --opt tight --input input"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

        INPUT = """$constrain
        force constant=1.0
        distance: 1, 2, auto
        """
        self.assertTrue(self.is_equivalent(INPUT, xtb.option_file))

    def test_freeze_soft(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'constraints': 'Freeze/1_2;',
                'specifications': '--forceconstant 0.1',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --opt tight --input input"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

        INPUT = """$constrain
        force constant=0.1
        distance: 1, 2, auto
        """
        self.assertTrue(self.is_equivalent(INPUT, xtb.option_file))

    def test_duplicate_specifications(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'constraints': 'Freeze/1_2;',
                'specifications': '--forceconstant 0.1 --forceconstant 0.2',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --opt tight --input input"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

        INPUT = """$constrain
        force constant=0.2
        distance: 1, 2, auto
        """
        self.assertTrue(self.is_equivalent(INPUT, xtb.option_file))

    def test_conformational_search(self):
        params = {
                'type': 'Conformational Search',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "crest in.xyz -rthr 0.6 -ewin 6"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

        self.assertEqual('', xtb.option_file)

    def test_conformational_search_specs(self):
        params = {
                'type': 'Conformational Search',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'specifications': '--rthr 0.8 --ewin 8',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "crest in.xyz -rthr 0.8 -ewin 8"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

        self.assertEqual('', xtb.option_file)

    def test_conformational_search_nci(self):
        params = {
                'type': 'Conformational Search',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'specifications': '--rthr 0.8 --nci',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "crest in.xyz -nci -rthr 0.8 -ewin 6"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

        self.assertEqual('', xtb.option_file)

    def test_constrained_conformational_search1(self):
        params = {
                'type': 'Constrained Conformational Search',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'constraints': 'Freeze/1_2;',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "crest in.xyz -cinp input -rthr 0.6 -ewin 6"
        self.assertTrue(self.is_equivalent(REF, xtb.command))

        INPUT = """$constrain
        force constant=1.0
        reference=in.xyz
        distance: 1, 2, auto
        atoms: 1,2
        $metadyn
        atoms: 3-9
        """
        self.assertTrue(self.is_equivalent(INPUT, xtb.option_file))

    def test_constrained_conformational_search2(self):
        params = {
                'type': 'Constrained Conformational Search',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'constraints': 'Freeze/1_4;Freeze/6_8;',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "crest in.xyz -cinp input -rthr 0.6 -ewin 6"
        self.assertTrue(self.is_equivalent(REF, xtb.command))

        INPUT = """$constrain
        force constant=1.0
        reference=in.xyz
        distance: 1, 4, auto
        distance: 6, 8, auto
        atoms: 1,4,6,8
        $metadyn
        atoms: 2-3,5,7,9
        """
        self.assertTrue(self.is_equivalent(INPUT, xtb.option_file))

    def test_constrained_conformational_search3(self):
        params = {
                'type': 'Constrained Conformational Search',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'constraints': 'Freeze/2_3;',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "crest in.xyz -cinp input -rthr 0.6 -ewin 6"
        self.assertTrue(self.is_equivalent(REF, xtb.command))

        INPUT = """$constrain
        force constant=1.0
        reference=in.xyz
        distance: 2, 3, auto
        atoms: 2,3
        $metadyn
        atoms: 1,4-9
        """
        self.assertTrue(self.is_equivalent(INPUT, xtb.option_file))

    def test_constrained_conformational_search4(self):
        params = {
                'type': 'Constrained Conformational Search',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'constraints': 'Freeze/2_3;',
                'specifications': '--force_constant 2.0',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "crest in.xyz -cinp input -rthr 0.6 -ewin 6"
        self.assertTrue(self.is_equivalent(REF, xtb.command))

        INPUT = """$constrain
        force constant=2.0
        reference=in.xyz
        distance: 2, 3, auto
        atoms: 2,3
        $metadyn
        atoms: 1,4-9
        """
        self.assertTrue(self.is_equivalent(INPUT, xtb.option_file))

    def test_constrained_conformational_search_equals(self):
        params = {
                'type': 'Constrained Conformational Search',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'constraints': 'Freeze/2_3;',
                'specifications': '--force_constant=2.0',
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "crest in.xyz -cinp input -rthr 0.6 -ewin 6"
        self.assertTrue(self.is_equivalent(REF, xtb.command))

        INPUT = """$constrain
        force constant=2.0
        reference=in.xyz
        distance: 2, 3, auto
        atoms: 2,3
        $metadyn
        atoms: 1,4-9
        """
        self.assertTrue(self.is_equivalent(INPUT, xtb.option_file))

    def test_invalid_specification(self):
        params = {
                'type': 'Constrained Conformational Search',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'constraints': 'Freeze/2_3;',
                'specifications': '--force 2.0',
                }

        calc = gen_calc(params, self.profile)
        with self.assertRaises(Exception):
            xtb = XtbCalculation(calc)

    def test_invalid_specification2(self):
        params = {
                'type': 'Constrained Conformational Search',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'constraints': 'Freeze/2_3;',
                'specifications': '-force_constant 2.0',
                }

        calc = gen_calc(params, self.profile)
        with self.assertRaises(Exception):
            xtb = XtbCalculation(calc)

    def test_invalid_specification3(self):
        params = {
                'type': 'Conformational Search',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'specifications': '-rthr 0.8 --ewin 8',
                }

        calc = gen_calc(params, self.profile)
        with self.assertRaises(Exception):
            xtb = XtbCalculation(calc)

    def test_gfn0(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'specifications': '--gfn 0'
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --gfn 0"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_gfn0_2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'specifications': '--gfn0'
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --gfn 0"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_gfn1(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'specifications': '--gfn 0'
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --gfn 0"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_gfn2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'specifications': '--gfn 2'
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

    def test_gfnff(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'ethanol.xyz',
                'software': 'xtb',
                'specifications': '--gfnff'
                }

        calc = gen_calc(params, self.profile)
        xtb = XtbCalculation(calc)

        REF = "xtb in.xyz --gfnff"

        self.assertTrue(self.is_equivalent(REF, xtb.command))

