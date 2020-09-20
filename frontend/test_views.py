import time

from .models import *
from . import views
from .constants import *
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
                'calc_multiplicity': ['1'],
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

    def test_submit_valid_specifications(self):
        params = self.basic_params
        params['calc_software'] = 'Gaussian'
        params['calc_theory_level'] = 'DFT'
        params['calc_functional'] = 'M06-2X'
        params['calc_basis_set'] = 'Def2-SVP'
        params['calc_specifications'] = 'SCF=XQC;'
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertNotContains(response, "Error while submitting your calculation")

    def test_submit_invalid_specifications(self):
        params = self.basic_params
        params['calc_software'] = 'Gaussian'
        params['calc_theory_level'] = 'DFT'
        params['calc_functional'] = 'M06-2X'
        params['calc_basis_set'] = 'Def2-SVP'
        params['calc_specifications'] = 'SCF=ABC;'
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

class PermissionTestsStudent(TestCase):
    def setUp(self):
        call_command('init_static_obj')
        self.username = "Student"
        self.password = "test1234"

        u = User.objects.create_user(username=self.username, password=self.password)
        u.profile.is_PI = False
        u.save()

        self.profile = Profile.objects.get(user__username=self.username)

        u2 = User.objects.create_user(username="PI", password=self.password)
        u2.profile.is_PI = True
        u2.save()

        self.PI = Profile.objects.get(user__username="PI")

        self.group = ResearchGroup.objects.create(name="Test group", PI=self.PI)
        self.group.save()

        self.client = Client()
        self.client.force_login(u)

    def test_project_public_nonmember(self):
        p = Project.objects.create(name="Public Project", author=self.PI, private=0)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get("/projects/PI")
        self.assertEqual(response.status_code, 404)

        response = self.client.get("/projects/PI/Public Project")
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/molecule/{}".format(m.id))
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/ensemble/{}".format(e.id))
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/download_structures/{}".format(e.id))
        self.assertEqual(response.status_code, 404)

        response = self.client.get("/download_structures/{}/0".format(e.id))
        self.assertEqual(response.status_code, 404)

    def test_project_public(self):
        self.profile.member_of = self.group
        self.profile.save()

        p = Project.objects.create(name="Public Project", author=self.PI, private=0)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get("/projects/PI")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/projects/PI/Public Project")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/molecule/{}".format(m.id))
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/ensemble/{}".format(e.id))
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/download_structures/{}".format(e.id))
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/download_structures/{}/0".format(e.id))
        self.assertEqual(response.status_code, 200)

    def test_project_private(self):
        self.profile.member_of = self.group
        self.profile.save()

        p = Project.objects.create(name="Public Project", author=self.PI, private=1)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get("/projects/PI")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/projects/PI/Public Project")
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/molecule/{}".format(m.id))
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/ensemble/{}".format(e.id))
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/download_structures/{}".format(e.id))
        self.assertEqual(response.status_code, 404)

        response = self.client.get("/download_structures/{}/0".format(e.id))
        self.assertEqual(response.status_code, 404)

class PermissionTestsPI(TestCase):
    def setUp(self):
        call_command('init_static_obj')
        self.username = "PI"
        self.password = "test1234"

        u = User.objects.create_user(username=self.username, password=self.password)
        u.profile.is_PI = True
        u.save()

        self.profile = Profile.objects.get(user__username=self.username)

        u2 = User.objects.create_user(username="Student", password=self.password)
        u2.profile.is_PI = False
        u2.save()

        self.student = Profile.objects.get(user__username="Student")

        self.group = ResearchGroup.objects.create(name="Test group", PI=self.profile)
        self.group.save()

        self.client = Client()
        self.client.force_login(u)

    def test_project_public_nonmember(self):
        p = Project.objects.create(name="Public Project", author=self.student, private=0)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get("/projects/Student")
        self.assertEqual(response.status_code, 404)

        response = self.client.get("/projects/Student/Public Project")
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/molecule/{}".format(m.id))
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/ensemble/{}".format(e.id))
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/download_structures/{}".format(e.id))
        self.assertEqual(response.status_code, 404)

        response = self.client.get("/download_structures/{}/0".format(e.id))
        self.assertEqual(response.status_code, 404)

    def test_project_public(self):
        self.student.member_of = self.group
        self.student.save()

        p = Project.objects.create(name="Public Project", author=self.student, private=0)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get("/projects/Student")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/projects/Student/Public Project")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/molecule/{}".format(m.id))
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/ensemble/{}".format(e.id))
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/download_structures/{}".format(e.id))
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/download_structures/{}/0".format(e.id))
        self.assertEqual(response.status_code, 200)

    def test_project_private(self):
        self.student.member_of = self.group
        self.student.save()

        p = Project.objects.create(name="Public Project", author=self.student, private=1)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get("/projects/Student")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/projects/Student/Public Project")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/molecule/{}".format(m.id))
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/ensemble/{}".format(e.id))
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/download_structures/{}".format(e.id))
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/download_structures/{}/0".format(e.id))
        self.assertEqual(response.status_code, 200)

    def test_delete_project_user(self):
        self.student.member_of = self.group
        self.student.save()

        p = Project.objects.create(name="Public Project", author=self.student, private=1)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.post("/delete_project/", {'id': p.id})
        self.assertEqual(response.status_code, 403)

    def test_delete_molecule_user(self):
        self.student.member_of = self.group
        self.student.save()

        p = Project.objects.create(name="Public Project", author=self.student, private=1)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.post("/delete_molecule/", {'id': m.id})
        self.assertEqual(response.status_code, 403)

    def test_delete_ensemble_user(self):
        self.student.member_of = self.group
        self.student.save()

        p = Project.objects.create(name="Public Project", author=self.student, private=1)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.post("/delete_ensemble/", {'id': e.id})
        self.assertEqual(response.status_code, 403)

class AnalysisTests(TestCase):
    def setUp(self):
        call_command('init_static_obj')
        self.username = "Student"
        self.password = "test1234"

        u = User.objects.create_user(username=self.username, password=self.password)
        u.profile.is_PI = False
        u.save()

        self.profile = Profile.objects.get(user__username=self.username)

        u2 = User.objects.create_user(username="PI", password=self.password)
        u2.profile.is_PI = True
        u2.save()

        self.PI = Profile.objects.get(user__username="PI")

        self.group = ResearchGroup.objects.create(name="Test group", PI=self.PI)
        self.group.save()

        self.client = Client()
        self.client.force_login(u)

    def test_boltzmann_weighing_Ha(self):
        self.profile.pref_units = 2#Hartree
        self.profile.save()

        proj = Project.objects.create(name="TestProj", author=self.profile)
        mol = Molecule.objects.create(name="Mol1", project=proj)
        e = Ensemble.objects.create(name="Confs", parent_molecule=mol)

        structs = [[-16.82945685, 9], [-16.82855278, 36], [-16.82760256, 7], [-16.82760254, 9], [-16.82760156, 2], [-16.82558904, 33], [-16.82495672, 1]]#From CREST (GFN2-xTB)
        rel_energies = [i[0] + 16.82945685 for i in structs]

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs):
            s = Structure.objects.create(parent_ensemble=e, number=ind+1, degeneracy=structs[ind][1])
            prop = Property.objects.create(parameters=params, energy=structs[ind][0], parent_structure=s)
            prop.save()
            s.save()
        e.save()
        proj.save()
        mol.save()
        ref_weights = [0.34724, 0.53361, 0.03796, 0.04880, 0.01082, 0.02125, 0.00033]

        response = self.client.post("/download_project/", {'id': proj.id, 'data': 'summary', 'scope': 'all', 'details': 'full'})
        csv = response.content.decode('utf-8')

        lines = csv.split('\n')
        ind = 0
        while lines[ind].find(",,Confs") == -1:
            ind += 1
        ind += 1

        while lines[ind].strip() != '':
            *_, num, degeneracy, energy, rel_energy, weight, free_energy = lines[ind].split(',')

            self.assertTrue(np.isclose(float(energy), structs[int(num)-1][0], atol=0.0001))
            self.assertTrue(np.isclose(float(weight), ref_weights[int(num)-1], atol=0.001))
            self.assertTrue(np.isclose(float(rel_energy), rel_energies[int(num)-1], atol=0.0001))
            self.assertEqual(float(free_energy), 0.0)
            ind += 1

    def test_boltzmann_weighing_kJ(self):
        self.profile.pref_units = 0#kJ/mol
        self.profile.save()

        proj = Project.objects.create(name="TestProj", author=self.profile)
        mol = Molecule.objects.create(name="Mol1", project=proj)
        e = Ensemble.objects.create(name="Confs", parent_molecule=mol)

        structs = [[-16.82945685, 9], [-16.82855278, 36], [-16.82760256, 7], [-16.82760254, 9], [-16.82760156, 2], [-16.82558904, 33], [-16.82495672, 1]]#From CREST (GFN2-xTB)
        rel_energies = [i[0] + 16.82945685 for i in structs]

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs):
            s = Structure.objects.create(parent_ensemble=e, number=ind+1, degeneracy=structs[ind][1])
            prop = Property.objects.create(parameters=params, energy=structs[ind][0], parent_structure=s)
            prop.save()
            s.save()
        e.save()
        proj.save()
        mol.save()
        ref_weights = [0.34724, 0.53361, 0.03796, 0.04880, 0.01082, 0.02125, 0.00033]

        response = self.client.post("/download_project/", {'id': proj.id, 'data': 'summary', 'scope': 'all', 'details': 'full'})
        csv = response.content.decode('utf-8')

        lines = csv.split('\n')
        ind = 0
        while lines[ind].find(",,Confs") == -1:
            ind += 1
        ind += 1

        while lines[ind].strip() != '':
            *_, num, degeneracy, energy, rel_energy, weight, free_energy = lines[ind].split(',')

            self.assertTrue(np.isclose(float(energy), structs[int(num)-1][0]*HARTREE_FVAL, atol=0.1))
            self.assertTrue(np.isclose(float(weight), ref_weights[int(num)-1], atol=0.001))
            self.assertTrue(np.isclose(float(rel_energy), rel_energies[int(num)-1]*HARTREE_FVAL, atol=0.1))
            self.assertEqual(float(free_energy), 0.0)

            ind += 1

    def test_boltzmann_weighing_kcal(self):
        self.profile.pref_units = 1#kcal/mol
        self.profile.save()

        proj = Project.objects.create(name="TestProj", author=self.profile)
        mol = Molecule.objects.create(name="Mol1", project=proj)
        e = Ensemble.objects.create(name="Confs", parent_molecule=mol)

        structs = [[-16.82945685, 9], [-16.82855278, 36], [-16.82760256, 7], [-16.82760254, 9], [-16.82760156, 2], [-16.82558904, 33], [-16.82495672, 1]]#From CREST (GFN2-xTB)
        rel_energies = [i[0] + 16.82945685 for i in structs]

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs):
            s = Structure.objects.create(parent_ensemble=e, number=ind+1, degeneracy=structs[ind][1])
            prop = Property.objects.create(parameters=params, energy=structs[ind][0], parent_structure=s)
            prop.save()
            s.save()
        e.save()
        proj.save()
        mol.save()
        ref_weights = [0.34724, 0.53361, 0.03796, 0.04880, 0.01082, 0.02125, 0.00033]

        response = self.client.post("/download_project/", {'id': proj.id, 'data': 'summary', 'scope': 'all', 'details': 'full'})
        csv = response.content.decode('utf-8')

        lines = csv.split('\n')
        ind = 0
        while lines[ind].find(",,Confs") == -1:
            ind += 1
        ind += 1

        while lines[ind].strip() != '':
            *_, num, degeneracy, energy, rel_energy, weight, free_energy = lines[ind].split(',')

            self.assertTrue(np.isclose(float(energy), structs[int(num)-1][0]*HARTREE_TO_KCAL_F, atol=0.001))
            self.assertTrue(np.isclose(float(weight), ref_weights[int(num)-1], atol=0.001))
            self.assertTrue(np.isclose(float(rel_energy), rel_energies[int(num)-1]*HARTREE_TO_KCAL_F, atol=0.01))
            self.assertEqual(float(free_energy), 0.0)

            ind += 1

    def test_boltzmann_weighing_missing_structures(self):
        self.profile.pref_units = 2#Hartree
        self.profile.save()

        proj = Project.objects.create(name="TestProj", author=self.profile)
        mol = Molecule.objects.create(name="Mol1", project=proj)
        e = Ensemble.objects.create(name="Confs", parent_molecule=mol)

        structs = [[-16.82945685, 9], [-16.82855278, 36], [-16.82760256, 7], [-16.82760254, 9], [-16.82760156, 2], [-16.82558904, 33], [-16.82495672, 1]]#From CREST (GFN2-xTB)
        rel_energies = [i[0] + 16.82945685 for i in structs]

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs[:-3]):
            s = Structure.objects.create(parent_ensemble=e, number=ind+1, degeneracy=structs[ind][1])
            prop = Property.objects.create(parameters=params, energy=structs[ind][0], parent_structure=s)
            prop.save()
            s.save()

        for ind, _s in enumerate(structs[-3:]):
            s = Structure.objects.create(parent_ensemble=e, number=ind+5, degeneracy=structs[ind][1])
            s.save()

        e.save()
        proj.save()
        mol.save()
        ref_weights = [0.359, 0.551, 0.039, 0.050]#Generated by working code

        response = self.client.post("/download_project/", {'id': proj.id, 'data': 'summary', 'scope': 'all', 'details': 'full'})
        csv = response.content.decode('utf-8')

        lines = csv.split('\n')
        ind = 0
        while lines[ind].find(",,Confs") == -1:
            ind += 1
        ind += 1

        while lines[ind].strip() != '':
            *_, num, degeneracy, energy, rel_energy, weight, free_energy = lines[ind].split(',')
            self.assertTrue(np.isclose(float(energy), structs[int(num)-1][0], atol=0.0001))
            self.assertTrue(np.isclose(float(weight), ref_weights[int(num)-1], atol=0.001))
            self.assertTrue(np.isclose(float(rel_energy), rel_energies[int(num)-1], atol=0.0001))
            self.assertEqual(float(free_energy), 0.0)
            ind += 1

    def test_summary(self):
        self.profile.pref_units = 2
        self.profile.save()

        proj = Project.objects.create(name="TestProj", author=self.profile)
        mol = Molecule.objects.create(name="Mol1", project=proj)
        e = Ensemble.objects.create(name="Confs", parent_molecule=mol)

        structs = [[-16.82945685, 9], [-16.82855278, 36], [-16.82760256, 7], [-16.82760254, 9], [-16.82760156, 2], [-16.82558904, 33], [-16.82495672, 1]]#From CREST (GFN2-xTB)
        ref_w_e = -16.82871

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs):
            s = Structure.objects.create(parent_ensemble=e, number=ind+1, degeneracy=structs[ind][1])
            prop = Property.objects.create(parameters=params, energy=structs[ind][0], parent_structure=s)
            prop.save()
            s.save()

        response = self.client.post("/download_project/", {'id': proj.id, 'data': 'summary', 'scope': 'all', 'details': 'summary'})

        csv = response.content.decode('utf-8')

        lines = csv.split('\n')
        ind = 0
        while lines[ind].find(",,Confs") == -1:
            ind += 1

        *_, w_e, w_f_e = lines[ind].split(',')
        self.assertTrue(np.isclose(float(w_e), ref_w_e, atol=0.0001))
