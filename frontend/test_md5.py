import os

from .models import *
from .gen_calc import gen_param
from django.core.management import call_command
from django.test import TestCase, Client


class ParametersMd5Tests(TestCase):
    def setUp(self):
        call_command('init_static_obj')

    def test_basic_same(self):
        params1 = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        p1 = gen_param(params1)
        p2 = gen_param(params1)
        self.assertEqual(p1.md5, p2.md5)

    def test_basic_different(self):
        params1 = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }
        params2 = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'PM3',
                'charge': '-1',
                }

        p1 = gen_param(params1)
        p2 = gen_param(params2)
        self.assertNotEqual(p1.md5, p2.md5)

    def test_different_softwares(self):
        params1 = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }
        params2 = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        p1 = gen_param(params1)
        p2 = gen_param(params2)
        self.assertNotEqual(p1.md5, p2.md5)

    def test_different_structures(self):
        params1 = {
                'type': 'Single-Point Energy',
                'in_file': 'I.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }
        params2 = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        p1 = gen_param(params1)
        p2 = gen_param(params2)
        self.assertEqual(p1.md5, p2.md5)

