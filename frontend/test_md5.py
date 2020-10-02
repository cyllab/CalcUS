import os

from .models import *
from django.core.management import call_command
from django.test import TestCase, Client

def gen_params(params):
    step = BasicStep.objects.get(name=params['type'])

    charge = 0
    multiplicity = 1
    solvent = "Vacuum"
    solvation_model = ""
    solvation_radii = ""
    basis_set = ""
    theory_level = ""
    method = ""
    additional_command = ""
    custom_basis_sets = ""
    density_fitting = ""
    specifications = ""

    if 'charge' in params.keys():
        charge = int(params['charge'])

    if 'multiplicity' in params.keys():
        multiplicity = int(params['multiplicity'])

    if 'solvent' in params.keys():
        solvent = params['solvent']

    if 'solvation_model' in params.keys():
        solvation_model = params['solvation_model']
        if 'solvation_radii' in params.keys():
            solvation_radii = params['solvation_radii']
        else:
            if solvation_model == "SMD":
                solvation_radii = "Default"
            if solvation_model in ["PCM", "CPCM"]:
                solvation_radii = "UFF"


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

    if 'additional_command' in params.keys():
        additional_command = params['additional_command']

    if 'specifications' in params.keys():
        specifications = params['specifications']

    software = params['software']

    p = Parameters.objects.create(charge=charge, multiplicity=multiplicity, solvent=solvent, solvation_model=solvation_model, solvation_radii=solvation_radii, basis_set=basis_set, theory_level=theory_level, method=method, additional_command=additional_command, custom_basis_sets=custom_basis_sets, density_fitting=density_fitting, specifications=specifications, software=software)

    return p

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

        p1 = gen_params(params1)
        p2 = gen_params(params1)
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

        p1 = gen_params(params1)
        p2 = gen_params(params2)
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

        p1 = gen_params(params1)
        p2 = gen_params(params2)
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

        p1 = gen_params(params1)
        p2 = gen_params(params2)
        self.assertEqual(p1.md5, p2.md5)

