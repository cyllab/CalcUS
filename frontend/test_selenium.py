import os
import time
import sys
import glob
import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import datetime

from django.contrib.auth.models import User, Group

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from shutil import copyfile, rmtree

from celery.contrib.testing.worker import start_worker

from calcus.celery import app

from .models import *
from django.core.management import call_command
from .calcusliveserver import CalcusLiveServer

from selenium.webdriver.support.select import Select

dir_path = os.path.dirname(os.path.realpath(__file__))

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(tests_dir, "scr")
RESULTS_DIR = os.path.join(tests_dir, "results")

class InterfaceTests(CalcusLiveServer):
    def test_default_login_page(self):
        self.assertTrue(self.is_on_page_projects())

    def test_goto_projects(self):
        self.lget("/projects/")
        self.assertTrue(self.is_on_page_projects())

    def test_projects_empty(self):
        self.lget("/projects/")
        self.assertEqual(self.get_number_projects(), 0)

    def test_projects_display(self):
        proj = Project.objects.create(name="Test project", author=self.profile)
        self.lget("/projects/")
        self.assertEqual(self.get_number_projects(), 1)

    def test_group_panel_absent(self):
        self.assertRaises(selenium.common.exceptions.NoSuchElementException, self.get_group_panel)

    def test_group_panel_absent2(self):
        self.assertFalse(self.group_panel_present())

    def test_group_panel_appears_as_PI(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 1)

    def test_group_panel_appears_as_PI2(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)
        self.lget("/profile/")
        self.add_user_to_group("Student")
        time.sleep(1)
        self.lget("/projects/")
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

    def test_group_panel_absent_without_adding(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        u = User.objects.create_user(username="Student", password=self.password)
        self.login(self.username, self.password)
        self.lget("/profile/")
        self.assertEqual(self.group_num_members(), 1)

    def test_group_panel_appears_as_student(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)
        self.lget("/profile/")
        self.add_user_to_group("Student")
        self.logout()
        self.login("Student", self.password)
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

    def test_group_panel_appears_everywhere_as_student(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)

        proj = Project.objects.create(name="Test project", author=u.profile)
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)

        self.lget("/profile/")
        self.add_user_to_group("Student")
        self.logout()
        self.login("Student", self.password)

        self.lget("/profile/")
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

        self.lget("/projects/")
        self.driver.implicitly_wait(5)
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

        self.click_project("Test project")
        self.driver.implicitly_wait(5)
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

        self.click_molecule("Test Molecule")
        self.driver.implicitly_wait(5)
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

        self.click_ensemble("Test Ensemble")
        self.driver.implicitly_wait(5)
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

    def test_group_panel_appears_everywhere_as_PI(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)

        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)

        self.lget("/profile/")
        self.add_user_to_group("Student")

        self.lget("/profile/")
        self.driver.implicitly_wait(5)
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

        self.lget("/projects/")
        self.driver.implicitly_wait(5)
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

        self.click_project("Test project")
        self.driver.implicitly_wait(5)
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

        self.click_molecule("Test Molecule")
        self.driver.implicitly_wait(5)
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

        self.click_ensemble("Test Ensemble")
        self.driver.implicitly_wait(5)
        self.assertTrue(self.group_panel_present())
        self.assertEqual(self.group_num_members(), 2)

    def test_group_access_projects_as_PI(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)

        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)

        self.lget("/profile/")
        self.add_user_to_group("Student")
        time.sleep(1)
        self.lget("/projects/")
        self.group_click_member("Student")
        self.assertTrue(self.is_on_page_projects())

    def test_group_access_project_as_PI(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)

        proj = Project.objects.create(name="Test project", author=u.profile)
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)

        self.lget("/profile/")
        self.add_user_to_group("Student")
        time.sleep(1)
        self.lget("/projects/")
        self.group_click_member("Student")
        self.click_project("Test project")
        self.driver.implicitly_wait(4)
        self.assertTrue(self.is_on_page_user_project())

    def test_group_access_molecule_as_PI(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)

        proj = Project.objects.create(name="Test project", author=u.profile)
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)

        self.lget("/profile/")
        self.add_user_to_group("Student")
        time.sleep(1)
        self.lget("/projects/")
        self.group_click_member("Student")
        self.click_project("Test project")
        self.click_molecule("Test Molecule")
        self.assertTrue(self.is_on_page_molecule())

    def test_group_access_ensemble_as_PI(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)

        proj = Project.objects.create(name="Test project", author=u.profile)
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)

        self.lget("/profile/")
        self.add_user_to_group("Student")
        time.sleep(1)
        self.lget("/projects/")
        self.group_click_member("Student")
        self.click_project("Test project")
        self.click_molecule("Test Molecule")
        self.click_ensemble("Test Ensemble")
        self.assertTrue(self.is_on_page_ensemble())

    def test_group_access_projects_as_student(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)

        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)

        self.lget("/profile/")
        self.add_user_to_group("Student")
        self.logout()
        self.login("Student", self.password)
        self.lget("/projects/")
        self.group_click_member(self.username)
        self.assertTrue(self.is_on_page_projects())

    def test_group_access_project_as_student(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)

        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)

        self.lget("/profile/")
        self.add_user_to_group("Student")
        self.logout()
        self.login("Student", self.password)
        self.lget("/projects/")
        self.group_click_member(self.username)
        self.click_project("Test project")
        self.assertTrue(self.is_on_page_user_project())

    def test_group_access_molecule_as_PI(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)

        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)

        self.lget("/profile/")
        self.add_user_to_group("Student")
        self.logout()
        self.login("Student", self.password)
        self.lget("/projects/")
        self.group_click_member(self.username)
        self.click_project("Test project")
        self.click_molecule("Test Molecule")
        self.assertTrue(self.is_on_page_molecule())

    def test_group_access_ensemble_as_PI(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)

        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)

        self.lget("/profile/")
        self.add_user_to_group("Student")
        self.logout()
        self.login("Student", self.password)
        self.lget("/projects/")
        self.group_click_member(self.username)
        self.click_project("Test project")
        self.click_molecule("Test Molecule")
        self.click_ensemble("Test Ensemble")
        self.assertTrue(self.is_on_page_ensemble())

    def test_project_empty(self):
        proj = Project.objects.create(name="Test project", author=self.profile)
        self.lget("/projects/")
        self.click_project("Test project")
        self.assertEqual(self.get_number_molecules(), 1)

    def test_molecule_appears(self):
        proj = Project.objects.create(name="Test project", author=self.profile)
        self.lget("/projects/")
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        self.click_project("Test project")
        self.assertTrue(self.is_on_page_user_project())
        self.assertEqual(self.get_number_molecules(), 2)

    def test_molecule_empty(self):
        proj = Project.objects.create(name="Test project", author=self.profile)
        self.lget("/projects/")
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        self.click_project("Test project")
        self.click_molecule("Test Molecule")
        self.assertTrue(self.is_on_page_molecule())
        self.assertEqual(self.get_number_ensembles(), 0)

    def test_ensemble_appears(self):
        proj = Project.objects.create(name="Test project", author=self.profile)
        self.lget("/projects/")
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)
        self.click_project("Test project")
        self.click_molecule("Test Molecule")
        self.assertEqual(self.get_number_ensembles(), 1)

    def test_ensemble_details(self):
        proj = Project.objects.create(name="Test project", author=self.profile)
        self.lget("/projects/")
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)
        self.click_project("Test project")
        self.click_molecule("Test Molecule")
        self.click_ensemble("Test Ensemble")
        self.assertTrue(self.is_on_page_ensemble())

    def test_basic_delete_project(self):
        def get_proj():
            proj = Project.objects.get(name="Test project", author=self.profile)
            return 0
        proj = Project.objects.create(name="Test project", author=self.profile)
        self.lget("/projects/")

        self.assertEqual(get_proj(), 0)
        self.delete_project("Test project")
        ind = 0
        while ind < 10:
            try:
                get_proj()
            except Project.DoesNotExist:
                break

            time.sleep(1)
            ind += 1

        self.assertRaises(Project.DoesNotExist, get_proj)

    def test_basic_delete_molecule(self):
        def get_mol():
            mol = Molecule.objects.get(name="Test molecule", project=proj)
            return 0
        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test molecule", project=proj)
        self.lget("/projects/")
        self.click_project("Test project")

        self.assertEqual(get_mol(), 0)
        self.delete_molecule("Test molecule")
        ind = 0
        while ind < 10:
            try:
                get_mol()
            except Molecule.DoesNotExist:
                break

            time.sleep(1)
            ind += 1

        self.assertRaises(Molecule.DoesNotExist, get_mol)

    def test_basic_delete_ensemble(self):
        def get_ensemble():
            e = Ensemble.objects.get(name="Test ensemble", parent_molecule=mol)
            return 0
        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test molecule", project=proj)
        e = Ensemble.objects.create(name="Test ensemble", parent_molecule=mol)
        self.lget("/projects/")
        self.click_project("Test project")
        self.click_molecule("Test molecule")

        self.assertEqual(get_ensemble(), 0)
        self.delete_ensemble("Test ensemble")
        ind = 0
        while ind < 10:
            try:
                get_ensemble()
            except Ensemble.DoesNotExist:
                break

            time.sleep(1)
            ind += 1

        self.assertRaises(Ensemble.DoesNotExist, get_ensemble)

    def test_create_empty_project(self):
        self.setup_test_group()
        self.lget("/projects/")

        self.create_empty_project()

        self.driver.implicitly_wait(5)

        self.assertEqual(self.get_number_projects(), 1)
        self.assertEqual(self.get_name_projects()[0], "My Project")

    def test_rename_project(self):
        self.setup_test_group()
        self.lget("/projects/")

        self.create_empty_project()

        self.driver.implicitly_wait(5)

        project = self.get_projects()[0]
        self.rename_project(project, "Test Project")
        self.lget("/projects/")

        self.assertEqual(self.get_number_projects(), 1)
        self.assertEqual(self.get_name_projects()[0], "Test Project")

    def test_rename_project2(self):
        self.setup_test_group()
        self.lget("/projects/")

        self.create_empty_project()

        self.driver.implicitly_wait(5)

        project = self.get_projects()[0]
        self.rename_project2(project, "Test Project")
        self.lget("/projects/")

        self.assertEqual(self.get_number_projects(), 1)
        self.assertEqual(self.get_name_projects()[0], "Test Project")

    def test_rename_molecule(self):
        self.setup_test_group()
        self.lget("/projects/")

        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test molecule", project=proj)
        self.lget("/projects/")
        self.click_project("Test project")

        mol = self.get_molecules()[0]
        self.rename_molecule(mol, "My Molecule")

        self.lget("/projects/")
        self.click_project("Test project")

        self.assertEqual(self.get_number_molecules(), 2)
        self.assertEqual(self.get_name_molecules()[0], "My Molecule")

    def test_rename_molecule2(self):
        self.setup_test_group()
        self.lget("/projects/")

        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test molecule", project=proj)
        self.lget("/projects/")
        self.click_project("Test project")

        mol = self.get_molecules()[0]
        self.rename_molecule2(mol, "My Molecule")

        self.lget("/projects/")
        self.click_project("Test project")

        self.assertEqual(self.get_number_molecules(), 2)
        self.assertEqual(self.get_name_molecules()[0], "My Molecule")

    def test_rename_ensemble(self):
        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test molecule", project=proj)
        e = Ensemble.objects.create(name="Test ensemble", parent_molecule=mol)
        self.lget("/projects/")
        self.click_project("Test project")
        self.click_molecule("Test molecule")

        ensemble = self.get_ensemble_rows()[0]
        self.rename_ensemble(ensemble, "My Ensemble")

        self.lget("/projects/")
        self.click_project("Test project")
        self.click_molecule("Test molecule")

        self.assertEqual(self.get_number_ensembles(), 1)
        self.assertEqual(self.get_name_ensembles()[0], "My Ensemble")

    def test_rename_ensemble2(self):
        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test molecule", project=proj)
        e = Ensemble.objects.create(name="Test ensemble", parent_molecule=mol)
        self.lget("/projects/")
        self.click_project("Test project")
        self.click_molecule("Test molecule")

        ensemble = self.get_ensemble_rows()[0]
        self.rename_ensemble2(ensemble, "My Ensemble")

        self.lget("/projects/")
        self.click_project("Test project")
        self.click_molecule("Test molecule")

        self.assertEqual(self.get_number_ensembles(), 1)
        self.assertEqual(self.get_name_ensembles()[0], "My Ensemble")

    def test_save_preset(self):
        params1 = {
                'software': 'Gaussian',
                'type': 'Frequency Calculation',
                'charge': '+1',
                'solvent': 'Chloroform',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'solvation_model': 'CPCM',
                }
        self.lget("/launch/")
        self.calc_input_params(params1)
        self.save_preset("Test Preset")

        presets = self.get_names_presets()
        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0], "Test Preset")

    def test_delete_preset(self):
        params1 = {
                'software': 'Gaussian',
                'type': 'Frequency Calculation',
                'charge': '+1',
                'solvent': 'Chloroform',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'solvation_model': 'CPCM',
                }
        self.lget("/launch/")
        self.calc_input_params(params1)
        self.save_preset("Test Preset")
        time.sleep(1)
        self.delete_preset("Test Preset")
        time.sleep(1)
        presets = self.get_names_presets()
        self.assertEqual(len(presets), 0)

    def test_load_preset(self):
        params1 = {
                'software': 'Gaussian',
                'type': 'Frequency Calculation',
                'charge': '+1',
                'solvent': 'Chloroform',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'solvation_model': 'CPCM',
                }
        self.lget("/launch/")
        self.calc_input_params(params1)
        self.save_preset("Test Preset")

        self.lget("/launch/")
        time.sleep(5)
        self.load_preset("Test Preset")

        solvent = Select(self.driver.find_element_by_name('calc_solvent'))
        charge = Select(self.driver.find_element_by_name('calc_charge'))
        theory = Select(self.driver.find_element_by_id("calc_theory_level"))
        func = self.driver.find_element_by_id("calc_functional")
        basis_set = self.driver.find_element_by_id("calc_basis_set")
        misc = self.driver.find_element_by_id("calc_misc")
        software = self.driver.find_element_by_id("calc_software")

        self.assertEqual(solvent.first_selected_option.text, params1['solvent'])
        self.assertEqual(charge.first_selected_option.text, params1['charge'])
        self.assertEqual(theory.first_selected_option.text, params1['theory'])
        self.assertEqual(func.get_attribute('value'), params1['functional'])
        self.assertEqual(basis_set.get_attribute('value'), params1['basis_set'])
        self.assertEqual(software.get_attribute('value'), params1['software'])
        self.assertEqual(misc.get_attribute('value'), "")

    def test_project_preset(self):
        proj = Project.objects.create(name="My Project", author=self.profile)
        proj.save()

        params1 = {
                'software': 'Gaussian',
                'type': 'Frequency Calculation',
                'charge': '+1',
                'solvent': 'Chloroform',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'solvation_model': 'CPCM',
                'project': 'My Project',
                }

        self.lget("/launch/")
        self.calc_input_params(params1)
        self.set_project_preset()

        self.lget("/projects")
        self.click_project("My Project")
        self.create_molecule_in_project()

        solvent = Select(self.driver.find_element_by_name('calc_solvent'))
        charge = Select(self.driver.find_element_by_name('calc_charge'))
        theory = Select(self.driver.find_element_by_id("calc_theory_level"))
        func = self.driver.find_element_by_id("calc_functional")
        basis_set = self.driver.find_element_by_id("calc_basis_set")
        misc = self.driver.find_element_by_id("calc_misc")
        software = self.driver.find_element_by_id("calc_software")

        self.assertEqual(solvent.first_selected_option.text, params1['solvent'])
        self.assertEqual(charge.first_selected_option.text, params1['charge'])
        self.assertEqual(theory.first_selected_option.text, params1['theory'])
        self.assertEqual(func.get_attribute('value'), params1['functional'])
        self.assertEqual(basis_set.get_attribute('value'), params1['basis_set'])
        self.assertEqual(software.get_attribute('value'), params1['software'])
        self.assertEqual(misc.get_attribute('value'), "")


class UserPermissionsTests(CalcusLiveServer):
    def test_launch_without_group(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()

        self.lget("/calculations")
        self.assertEqual(self.get_number_calc_orders(), 0)

    def test_request_PI(self):
        self.lget('/profile/')
        self.apply_PI("Test group")
        self.assertTrue(self.driver.find_element_by_id("PI_application_message").text.find("Your request has been received") != -1)

    def test_manage_PI_request(self):
        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)

        self.lget('/launch/')

        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations")
        self.assertEqual(self.get_number_calc_orders(), 1)


class XtbCalculationTestsPI(CalcusLiveServer):

    def setUp(self):
        super().setUp()

        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)


    def test_opt(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_sp(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_proj(self):
        proj = Project.objects.create(author=self.profile, name="TestProj")
        proj.save()

        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'TestProj',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_freq(self):
        params = {
                'calc_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()

    def test_freq_solv(self):
        params = {
                'calc_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'solvent': 'Chloroform',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()

    def test_conf_search(self):
        params = {
                'calc_name': 'test',
                'type': 'Conformational Search',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.sdf',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

    def test_ts(self):
        params = {
                'calc_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ts.xyz',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(20)
        self.assertTrue(self.latest_calc_successful())

    def test_ensemble_second_step(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.launch_ensemble_next_step()

        params2 = {
                'type': 'Frequency Calculation',
                #project implicit
                }
        self.calc_input_params(params2)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_structure_second_step(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.launch_structure_next_step()

        params2 = {
                'type': 'Frequency Calculation',
                #project implicit
                }
        self.calc_input_params(params2)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

class XtbCalculationTestsStudent(CalcusLiveServer):
    def setUp(self):
        super().setUp()

        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)
        u = User.objects.create_user(username="Student", password=self.password)
        self.lget("/profile/")
        self.add_user_to_group("Student")
        self.logout()
        self.login("Student", self.password)


    def test_opt(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_proj(self):
        student = Profile.objects.get(user__username="Student")
        proj = Project.objects.create(author=student, name="TestProj")
        proj.save()

        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'TestProj',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_freq(self):
        params = {
                'calc_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_conf_search(self):
        params = {
                'calc_name': 'test',
                'type': 'Conformational Search',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.sdf',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertGreater(self.get_number_conformers(), 0)

    def test_ts(self):
        params = {
                'calc_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'small_ts.xyz',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(20)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_scan_distance(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Distance', [1, 2], [1.5, 2.0, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_scan_distance_not_converged(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Distance', [1, 2], [0.01, 3.5, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertFalse(self.latest_calc_successful())

    def test_scan_angle(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Angle', [1, 2, 3], [120, 130, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_scan_dihedral(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Dihedral', [1, 2, 3, 4], [0, 10, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_freeze_distance(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Distance', [1, 4]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.driver.implicitly_wait(5)
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_angle(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Angle', [1, 2, 3]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_dihedral(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Dihedral', [1, 2, 3, 4]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_uvvis(self):
        params = {
                'calc_name': 'test',
                'type': 'UV-Vis Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()

        #test if it loads

    def test_ensemble_second_step(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

        self.launch_ensemble_next_step()

        params2 = {
                'type': 'Frequency Calculation',
                #project implicit
                }
        self.calc_input_params(params2)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_structure_second_step(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

        self.launch_structure_next_step()


        params2 = {
                'type': 'Frequency Calculation',
                #project implicit
                }
        self.calc_input_params(params2)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

class OrcaCalculationTestsPI(CalcusLiveServer):

    def setUp(self):
        super().setUp()

        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)

    def test_sp_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_HF(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'H2.mol2',
                'software': 'ORCA',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_HF_CPCM(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'H2.mol2',
                'software': 'ORCA',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                'solvation_method': 'CPCM',
                'solvent': 'Methanol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT2(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M06-2X',
                'basis_set': 'Def2SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_RIMP2(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'H2.sdf',
                'software': 'ORCA',
                'theory': 'RI-MP2',
                'basis_set': 'cc-pVDZ',
                'misc': 'cc-pVDZ/C',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(60)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_HF(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_DFT(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_DFT_single_atom(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_RIMP2(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'H2.sdf',
                'software': 'ORCA',
                'theory': 'RI-MP2',
                'basis_set': 'cc-pVDZ',
                'misc': 'cc-pVDZ/C',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(60)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freq_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'software': 'ORCA',
                'theory': 'Semi-empirical',
                'method': 'PM3',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

        self.click_calc_method(2)
        self.assertTrue(self.is_loaded_frequencies())

    def test_freq_HF(self):
        params = {
                'calc_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'software': 'ORCA',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

        self.click_calc_method(2)
        self.assertTrue(self.is_loaded_frequencies())

    '''
    def test_freq_DFT(self):
        params = {
                'calc_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'PW92',
                'basis_set': 'Def2-SVP',
                'misc': 'NUMFREQ',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertTrue(self.is_on_page_molecule())

        self.click_ensemble("File Upload")
        self.assertEqual(self.get_number_conformers(), 0)
        self.click_calc_method(2)
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freq_RIMP2(self):
        params = {
                'calc_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'RI-MP2',
                'basis_set': 'cc-pVDZ',
                'misc': 'cc-pVDZ/C NUMFREQ',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(60)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertTrue(self.is_on_page_molecule())

        self.click_ensemble("File Upload")
        self.assertEqual(self.get_number_conformers(), 0)
        self.click_calc_method(2)
        self.assertEqual(self.get_number_conformers(), 1)
    '''

    def test_ts_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'mini_ts.xyz',
                'software': 'ORCA',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(20)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_ts_HF(self):
        params = {
                'calc_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'mini_ts.xyz',
                'software': 'ORCA',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(200)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_ts_DFT(self):
        params = {
                'calc_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'mini_ts.xyz',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(600)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_ts_RIMP2(self):
        params = {
                'calc_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'mini_ts.xyz',
                'software': 'ORCA',
                'theory': 'RI-MP2',
                'basis_set': 'cc-pVDZ',
                'misc': 'cc-pVDZ/C',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(1000)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_mo_HF(self):
        params = {
                'calc_name': 'test',
                'type': 'MO Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'software': 'ORCA',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)
        self.click_calc_method(2)
        self.assertTrue(self.is_loaded_mo())

    def test_mo_DFT(self):
        params = {
                'calc_name': 'test',
                'type': 'MO Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)
        self.click_calc_method(2)
        self.assertTrue(self.is_loaded_mo())

    def test_scan_distance_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Distance', [1, 2], [3.5, 1.5, 5]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'ORCA',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 5)

    def test_scan_angle_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Angle', [1, 2, 3], [120, 130, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'ORCA',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_scan_dihedral_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Dihedral', [1, 2, 3, 4], [0, 10, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'ORCA',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_freeze_distance_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Distance', [1, 4]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'ORCA',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_angle_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Angle', [1, 2, 3]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'ORCA',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_dihedral_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Dihedral', [1, 2, 3, 4]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'ORCA',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_nmr_DFT(self):
        params = {
                'calc_name': 'test',
                'type': 'NMR Prediction',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'misc': 'Def2/JK',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(60)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

class GaussianCalculationTestsPI(CalcusLiveServer):

    def setUp(self):
        super().setUp()

        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)

    def test_sp_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_HF(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT_PCM(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'solvation_method': 'PCM',
                'solvent': 'Methanol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT_CPCM(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'solvation_method': 'CPCM',
                'solvent': 'Methanol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT2(self):
        params = {
                'calc_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M06-2X',
                'basis_set': 'Def2SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)


    def test_opt_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_HF(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_DFT(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_DFT_single_atom(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)


    def test_freq_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'software': 'Gaussian',
                'theory': 'Semi-empirical',
                'method': 'PM3',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)
        self.click_calc_method(2)
        self.assertTrue(self.is_loaded_frequencies())

    def test_freq_HF(self):
        params = {
                'calc_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'software': 'Gaussian',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)
        self.click_calc_method(2)
        self.assertTrue(self.is_loaded_frequencies())

    def test_freq_DFT(self):
        params = {
                'calc_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freq_DFT_single_atom(self):
        params = {
                'calc_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'Cl.xyz',
                'charge': '-1',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)


    def test_ts_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'mini_ts.xyz',
                'software': 'Gaussian',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(20)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_ts_HF(self):
        params = {
                'calc_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'mini_ts.xyz',
                'software': 'Gaussian',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(200)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_ts_DFT(self):
        params = {
                'calc_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'mini_ts.xyz',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(600)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)


    def test_scan_distance_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Distance', [1, 2], [3.5, 5.0, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'Gaussian',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 11)

    def test_scan_angle_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Angle', [1, 2, 3], [120, 130, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'Gaussian',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 11)

    def test_scan_dihedral_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Dihedral', [1, 2, 3, 4], [0, 10, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'Gaussian',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 11)

    def test_freeze_distance_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Distance', [1, 2]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'Gaussian',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_angle_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Angle', [1, 2, 3]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'Gaussian',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_dihedral_SE(self):
        params = {
                'calc_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Dihedral', [1, 2, 3, 4]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'Gaussian',
                'in_file': 'CH4.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(30)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_nmr_DFT(self):
        params = {
                'calc_name': 'test',
                'type': 'NMR Prediction',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(60)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

class MiscCalculationTests(CalcusLiveServer):

    def setUp(self):
        super().setUp()

        self.lget('/profile/')

        self.apply_PI("Test group")
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')

        self.accept_PI_request()
        self.logout()

        self.login(self.username, self.password)


    def test_cancel_calc(self):
        params = {
                'calc_name': 'test',
                'type': 'Conformational Search',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'pentane.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.details_latest_order()
        self.cancel_all_calc()

        ind = 0
        while ind < 10:
            self.driver.refresh()
            s = self.get_calculation_statuses()
            self.assertEqual(len(s), 1)
            if s[0] == "Error":
                break

            time.sleep(1)
            ind += 1

        s = self.get_calculation_statuses()
        self.assertEqual(s[0], "Error")
