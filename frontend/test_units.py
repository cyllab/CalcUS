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
from .calculation_helper import get_xyz_from_Gaussian_input
from django.core.management import call_command
from django.test import TestCase, Client

class FileProcessingTests(TestCase):
    def setUp(self):
        self.raw_xyz = """C       1.570595      -1.917323      -3.087863
C       1.099934      -1.387944      -0.907839
C       1.186740      -0.013229      -1.614203
C       1.505206      -0.370763      -3.086396
H       2.309444      -2.325650      -3.790366
H       0.588703      -2.332392      -3.368639
H       0.051933      -1.728844      -0.881364
H       1.463755      -1.373787      0.128289
H       0.257419      0.563188      -1.509568
H       1.993015      0.593845      -1.177903
H       0.750607      0.010442      -3.787893
H       2.471929      0.055984      -3.390225
N       1.864226      -2.327415      -1.719803
H       2.857594      -2.183310      -1.540327"""
        self.xyz = "{}\n\n{}".format(len(self.raw_xyz.split('\n')), self.raw_xyz)

    def test_parse_gaussian_com_space(self):
        inp = """%chk=test.chk
                %mem=15000MB
                %nproc=8
                #p opt freq(NoRaman) M062X/Def2TZVP

                Unnecessary header

                0 1
                {}

                """.format(self.raw_xyz)
        parsed_xyz = get_xyz_from_Gaussian_input(inp)
        self.assertEqual(parsed_xyz, self.xyz)

    def test_parse_gaussian_com_nospace(self):
        inp = """%chk=test.chk
                %mem=15000MB
                %nproc=8
                #p opt freq(NoRaman) M062X/Def2TZVP

                Unnecessary header

                0 1
                {}
                """.format(self.raw_xyz)
        parsed_xyz = get_xyz_from_Gaussian_input(inp)
        self.assertEqual(parsed_xyz, self.xyz)

    def test_parse_gaussian_com_nonewline(self):
        inp = """%chk=test.chk
                %mem=15000MB
                %nproc=8
                #p opt freq(NoRaman) M062X/Def2TZVP

                Unnecessary header

                0 1
                {}""".format(self.raw_xyz)
        parsed_xyz = get_xyz_from_Gaussian_input(inp)
        self.assertEqual(parsed_xyz, self.xyz)

    def test_parse_gaussian_com_short_link0(self):
        inp = """%chk=test.chk
                %nproc=8
                #p opt freq(NoRaman) M062X/Def2TZVP

                Unnecessary header

                0 1
                {}

                """.format(self.raw_xyz)
        parsed_xyz = get_xyz_from_Gaussian_input(inp)
        self.assertEqual(parsed_xyz, self.xyz)

    def test_parse_gaussian_com_long_link0(self):
        inp = """%chk=test.chk
                %mem=15000MB
                %nproc=8
                %schk=test.chk
                #p opt freq(NoRaman) M062X/Def2TZVP

                Unnecessary header

                0 1
                {}

                """.format(self.raw_xyz)
        parsed_xyz = get_xyz_from_Gaussian_input(inp)
        self.assertEqual(parsed_xyz, self.xyz)

