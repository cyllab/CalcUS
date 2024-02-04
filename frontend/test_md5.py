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

from .models import *
from .gen_calc import gen_param
from django.core.management import call_command
from django.test import TestCase, Client


class ParametersMd5Tests(TestCase):
    def setUp(self):
        call_command("init_static_obj")

    def test_basic_same(self):
        params1 = {
            "type": "Single-Point Energy",
            "in_file": "Cl.xyz",
            "software": "Gaussian",
            "theory_level": "Semi-empirical",
            "method": "AM1",
            "charge": "-1",
        }

        p1 = gen_param(params1)
        p2 = gen_param(params1)
        self.assertEqual(p1.md5, p2.md5)

    def test_basic_different(self):
        params1 = {
            "type": "Single-Point Energy",
            "in_file": "Cl.xyz",
            "software": "Gaussian",
            "theory_level": "Semi-empirical",
            "method": "AM1",
            "charge": "-1",
        }
        params2 = {
            "type": "Single-Point Energy",
            "in_file": "Cl.xyz",
            "software": "Gaussian",
            "theory_level": "Semi-empirical",
            "method": "PM3",
            "charge": "-1",
        }

        p1 = gen_param(params1)
        p2 = gen_param(params2)
        self.assertNotEqual(p1.md5, p2.md5)

    def test_different_softwares(self):
        params1 = {
            "type": "Single-Point Energy",
            "in_file": "Cl.xyz",
            "software": "Gaussian",
            "theory_level": "Semi-empirical",
            "method": "AM1",
            "charge": "-1",
        }
        params2 = {
            "type": "Single-Point Energy",
            "in_file": "Cl.xyz",
            "software": "ORCA",
            "theory_level": "Semi-empirical",
            "method": "AM1",
            "charge": "-1",
        }

        p1 = gen_param(params1)
        p2 = gen_param(params2)
        self.assertNotEqual(p1.md5, p2.md5)

    def test_different_structures(self):
        params1 = {
            "type": "Single-Point Energy",
            "in_file": "I.xyz",
            "software": "Gaussian",
            "theory_level": "Semi-empirical",
            "method": "AM1",
            "charge": "-1",
        }
        params2 = {
            "type": "Single-Point Energy",
            "in_file": "Cl.xyz",
            "software": "Gaussian",
            "theory_level": "Semi-empirical",
            "method": "AM1",
            "charge": "-1",
        }

        p1 = gen_param(params1)
        p2 = gen_param(params2)
        self.assertEqual(p1.md5, p2.md5)
