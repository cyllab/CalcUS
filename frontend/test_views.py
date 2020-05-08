from .models import *
from . import views
from django.core.management import call_command
from django.test import TestCase, Client

class LaunchTests(TestCase):
    def setUp(self):
        call_command('init_static_obj')
        self.username = "Tester"
        self.password = "test1234"

        u = User.objects.create_superuser(username=self.username, password=self.password)
        u.profile.is_PI = True
        u.save()
        self.profile = Profile.objects.get(user__username=self.username)
        self.group = ResearchGroup.objects.create(name="Test group", PI=self.profile)
        self.group.save()
        self.client = Client()
        self.client.force_login(u)

        self.basic_params = {
                'file_structure': [''],
                'calc_name': ['Test'],
                'calc_solvent': ['Vacuum'],
                'calc_charge': ['0'],
                'calc_project': ['New Project'],
                'new_project_name': ['Test'],
                'calc_software': ['xtb'],
                'calc_type': ['Geometrical Optimisation'],
                'constraint_mode_1': ['Freeze'],
                'constraint_type_1': ['Distance'],
                'calc_constraint_1_1': [''],
                'calc_constraint_1_2': [''],
                'calc_constraint_1_3': [''],
                'calc_constraint_1_4': [''],
                'calc_scan_1_1': [''],
                'calc_scan_1_2': [''],
                'calc_scan_1_3': [''],
                'calc_ressource': ['Local'],
                'constraint_num': ['1'],
                'structureB': ['Molecule from ChemDoodle Web Components\r\n\r\nhttp://www.ichemlabs.com\r\n  6  6  0  0  0  0            999 V2000\r\n    0.0000    1.0000    0.0000 C   0  0  0  0  0  0\r\n    0.8660    0.5000    0.0000 C   0  0  0  0  0  0\r\n    0.8660   -0.5000    0.0000 C   0  0  0  0  0  0\r\n    0.0000   -1.0000    0.0000 C   0  0  0  0  0  0\r\n   -0.8660   -0.5000    0.0000 C   0  0  0  0  0  0\r\n   -0.8660    0.5000    0.0000 C   0  0  0  0  0  0\r\n  1  2  1  0  0  0  0\r\n  2  3  2  0  0  0  0\r\n  3  4  1  0  0  0  0\r\n  4  5  2  0  0  0  0\r\n  5  6  1  0  0  0  0\r\n  6  1  2  0  0  0  0\r\nM  END'],
                'test': ['true'],
                }

    def tearDown(self):
        pass

    def test_get_launch_page(self):
        response = self.client.get("/launch/", follow=True)
        self.assertEqual(response.status_code, 200)

    def test_submit_empty(self):
        response = self.client.post("/submit_calculation", data={}, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_correct(self):
        response = self.client.post("/submit_calculation/", data=self.basic_params, follow=True)
        self.assertNotContains(response, "Error while submitting your calculation")

    def test_submit_long_name(self):
        params = self.basic_params
        params['calc_name'] = 'A'*200
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_long_project_name(self):
        params = self.basic_params
        params['calc_project'] = 'A'*200
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_name(self):
        params = self.basic_params
        params['calc_name'] = ''
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_solvent(self):
        params = self.basic_params
        params['calc_solvent'] = ''
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_charge(self):
        params = self.basic_params
        params['calc_charge'] = ''
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_project(self):
        params = self.basic_params
        params['calc_project'] = ''
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_software(self):
        params = self.basic_params
        params['calc_software'] = ''
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_type(self):
        params = self.basic_params
        params['calc_type'] = ''
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_resource(self):
        params = self.basic_params
        params['calc_ressource'] = ''
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_name(self):
        params = self.basic_params
        del params['calc_name']
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_solvent(self):
        params = self.basic_params
        del params['calc_solvent']
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_invalid_solvent(self):
        params = self.basic_params
        params['calc_solvent'] = "Orange Juice"
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_charge(self):
        params = self.basic_params
        del params['calc_charge']
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_project(self):
        params = self.basic_params
        del params['calc_project']
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_software(self):
        params = self.basic_params
        del params['calc_software']
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_type(self):
        params = self.basic_params
        del params['calc_type']
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_resource(self):
        params = self.basic_params
        del params['calc_ressource']
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_resource(self):
        params = self.basic_params
        del params['calc_ressource']
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_no_theory(self):
        params = self.basic_params
        params['calc_software'] = 'ORCA'
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_empty_theory(self):
        params = self.basic_params
        params['calc_software'] = 'ORCA'
        params['calc_theory_level'] = ''
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_DFT_no_functional(self):
        params = self.basic_params
        params['calc_software'] = 'ORCA'
        params['calc_theory_level'] = 'DFT'
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_DFT_no_basis_set(self):
        params = self.basic_params
        params['calc_software'] = 'ORCA'
        params['calc_theory_level'] = 'DFT'
        params['calc_functional'] = 'M06-2X'
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_DFT_empty_functional(self):
        params = self.basic_params
        params['calc_software'] = 'ORCA'
        params['calc_theory_level'] = 'DFT'
        params['calc_functional'] = ''
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_DFT_correct(self):
        params = self.basic_params
        params['calc_software'] = 'ORCA'
        params['calc_theory_level'] = 'DFT'
        params['calc_functional'] = 'M06-2X'
        params['calc_basis_set'] = 'Def2-SVP'
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertNotContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_DFT_empty_basis_set(self):
        params = self.basic_params
        params['calc_software'] = 'ORCA'
        params['calc_theory_level'] = 'DFT'
        params['calc_functional'] = 'M06-2X'
        params['calc_basis_set'] = ''
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

