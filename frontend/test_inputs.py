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

