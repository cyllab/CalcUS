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


import glob
import os
import time
import unittest

from django.http import HttpResponse, HttpResponseRedirect
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import *
from django.contrib.auth.models import User
from shutil import copyfile, rmtree
from .tasks import write_mol, gen_fingerprint

tests_dir = os.path.join("/".join(__file__.split("/")[:-1]), "tests/")
SCR_DIR = os.path.join(tests_dir, "scr")
RESULTS_DIR = os.path.join(tests_dir, "results")


class JobTestCase(TestCase):
    def test_mol_conversion(self):
        with open(os.path.join(tests_dir, "ts.xyz")) as f:
            lines = f.readlines()

        xyz = []
        for line in lines[2:]:
            a, x, y, z = line.strip().split()
            xyz.append([a, float(x), float(y), float(z)])

        mol = "".join(write_mol(xyz))

        with open(os.path.join(tests_dir, "ts.mol")) as f:
            lines2 = f.readlines()
        mol2 = "".join(lines2)
        self.assertEqual(mol, mol2)

    def test_fingerprint(self):
        with open(os.path.join(tests_dir, "ts.xyz")) as f:
            lines = f.readlines()

        s = Structure.objects.create(xyz_structure="".join(lines))
        inchi = gen_fingerprint(s).strip()
        self.assertEqual(
            inchi,
            "1S/C18H15IO/c1-4-10-16(11-5-1)19(17-12-6-2-7-13-17)20-18-14-8-3-9-15-18/h1-15H",
        )
