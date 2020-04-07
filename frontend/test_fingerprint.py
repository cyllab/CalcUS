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

from rdkit import Chem

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
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

        mol = ''.join(write_mol(xyz))

        with open(os.path.join(tests_dir, "ts.mol")) as f:
            lines2 = f.readlines()
        mol2 = ''.join(lines2)
        self.assertEqual(mol, mol2)

    def test_fingerprint(self):
        with open(os.path.join(tests_dir, "ts.xyz")) as f:
            lines = f.readlines()

        xyz = []
        for line in lines[2:]:
            a, x, y, z = line.strip().split()
            xyz.append([a, float(x), float(y), float(z)])

        mol = ''.join(write_mol(xyz))
        m = Chem.MolFromMolBlock(mol)
        fingerprint = Chem.inchi.MolToInchi(m)
        print(fingerprint)

