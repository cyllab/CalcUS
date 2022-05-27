"""
This file of part of CalcUS.

Copyright (C) 2020-2022 Raphaël Robidas

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
"""


import os
import unittest

from django.test import TestCase, Client

from .libxyz import *

tests_dir = os.path.join("/".join(__file__.split("/")[:-1]), "tests/")


class XyzTests(TestCase):
    def test_morgan_algorithm1(self):
        xyz = parse_xyz_from_file(os.path.join(tests_dir, "CH4.xyz"))
        REF = [5, 2, 2, 2, 2]
        indices = morgan_numbering(xyz)
        for ind, i in enumerate(REF):
            self.assertEqual(indices[ind], i)

    def test_morgan_algorithm2(self):
        xyz = parse_xyz_from_file(os.path.join(tests_dir, "ethanol.xyz"))
        REF = [54, 23, 23, 23, 57, 24, 24, 32, 15]
        indices = morgan_numbering(xyz)
        for ind, i in enumerate(REF):
            self.assertEqual(indices[ind], i)

    def equivalent_equivalence(self, test, ref):
        test_d = {}
        ref_d = {}

        for eqs in test:
            l = len(eqs)
            if l in test_d.keys():
                test_d[l].append(eqs)
            else:
                test_d[l] = [eqs]

        for eqs in ref:
            l = len(eqs)
            if l in ref_d.keys():
                ref_d[l].append(eqs)
            else:
                ref_d[l] = [eqs]

        if test_d.keys() != ref_d.keys():
            return False

        def one_equivalent(arr_arr, arr):
            for _arr in arr_arr:
                if np.array_equal(_arr, arr):
                    return True
            return False

        for k in test_d.keys():
            if len(test_d[k]) != len(ref_d[k]):
                return False

            for arr in test_d[k]:
                if not one_equivalent(ref_d[k], arr):
                    return False

        return True

    def test_equivalent_atoms1(self):
        xyz = parse_xyz_from_file(os.path.join(tests_dir, "CH4.xyz"))
        eqs = equivalent_atoms(xyz)
        REF = [[1, 2, 3, 4]]
        self.assertTrue(self.equivalent_equivalence(eqs, REF))

    def test_equivalent_atoms2(self):
        xyz = parse_xyz_from_file(os.path.join(tests_dir, "ethanol.xyz"))
        eqs = equivalent_atoms(xyz)
        REF = [[1, 2, 3], [5, 6]]
        self.assertTrue(self.equivalent_equivalence(eqs, REF))

    def test_equivalent_atoms3(self):
        xyz = parse_xyz_from_file(os.path.join(tests_dir, "benzene.xyz"))
        eqs = equivalent_atoms(xyz)
        REF = [[0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11]]
        self.assertTrue(self.equivalent_equivalence(eqs, REF))

    def test_equivalent_atoms4(self):
        xyz = parse_xyz_from_file(os.path.join(tests_dir, "propane.xyz"))
        eqs = equivalent_atoms(xyz)
        REF = [[5, 6], [0, 7], [1, 2, 3, 8, 9, 10]]
        self.assertTrue(self.equivalent_equivalence(eqs, REF))

    def test_equivalent_atoms5(self):
        xyz = parse_xyz_from_file(os.path.join(tests_dir, "Ph2I_cation.xyz"))
        eqs = equivalent_atoms(xyz)
        REF = [
            [4, 12],
            [3, 5, 13, 14],
            [0, 2, 15, 17],
            [1, 19],
            [9, 10, 16, 18],
            [6, 8, 20, 21],
            [7, 22],
        ]
        self.assertTrue(self.equivalent_equivalence(eqs, REF))

    def test_reorder1(self):
        xyz1 = parse_xyz_from_file(os.path.join(tests_dir, "reorder/CHIFBr_A.xyz"))
        xyz2 = parse_xyz_from_file(os.path.join(tests_dir, "reorder/CHIFBr_B.xyz"))

        self.assertNotEqual(xyz1[1][0], xyz2[1][0])

        xyz2_reorder = reorder_xyz(xyz1, xyz2)
