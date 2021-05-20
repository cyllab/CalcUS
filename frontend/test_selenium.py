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
from .libxyz import *
from django.core.management import call_command
from .calcusliveserver import CalcusLiveServer

from selenium.webdriver.support.select import Select
from unittest import mock

dir_path = os.path.dirname(os.path.realpath(__file__))

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(tests_dir, "scr")
RESULTS_DIR = os.path.join(tests_dir, "results")

class InterfaceTests(CalcusLiveServer):
    @classmethod
    def setUpClass(cls):
        cls.patcher = mock.patch.dict(os.environ, {"CAN_USE_CACHED_LOGS": "true"})
        cls.patcher.start()
        super().setUpClass()

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
        time.sleep(0.1)#Database delay

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
        self.assertEqual(self.get_number_molecules(), 0)

    def test_molecule_appears(self):
        proj = Project.objects.create(name="Test project", author=self.profile)
        self.lget("/projects/")
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        self.click_project("Test project")
        self.assertTrue(self.is_on_page_user_project())
        self.assertEqual(self.get_number_molecules(), 1)

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

        self.wait_for_ajax()

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

        ind = 0
        while ind < 3:
            if self.get_name_projects()[0] == "Test Project":
                break
            ind += 1
            time.sleep(1)
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

        ind = 0
        while ind < 3:
            if self.get_name_projects()[0] == "Test Project":
                break
            ind += 1
            time.sleep(1)

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

        self.assertEqual(self.get_number_molecules(), 1)
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

        self.assertEqual(self.get_number_molecules(), 1)
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

    def test_flag_ensemble(self):
        proj = Project.objects.create(name="Test project", author=self.profile)
        mol = Molecule.objects.create(name="Test molecule", project=proj)
        e = Ensemble.objects.create(name="Test ensemble", parent_molecule=mol)
        self.lget("/projects/")
        self.click_project("Test project")
        self.click_molecule("Test molecule")
        self.click_ensemble("Test ensemble")
        self.flag_ensemble()

        self.driver.refresh()
        self.assertTrue(self.is_ensemble_flagged())

    def test_save_preset(self):
        params = {
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
        self.calc_input_params(params)
        self.save_preset("Test Preset")

        presets = self.get_name_presets()
        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0], "Test Preset")

    def test_delete_preset(self):
        params = {
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
        self.calc_input_params(params)
        self.save_preset("Test Preset")
        time.sleep(1)
        self.delete_preset("Test Preset")
        time.sleep(1)
        presets = self.get_name_presets()
        self.assertEqual(len(presets), 0)

    def test_load_preset(self):
        params = {
                'software': 'Gaussian',
                'type': 'Frequency Calculation',
                'charge': '+1',
                'solvent': 'Chloroform',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'solvation_model': 'CPCM',
                'specifications': 'tightscf',
                }
        self.lget("/launch/")
        self.calc_input_params(params)
        self.save_preset("Test Preset")

        self.lget("/launch/")
        self.wait_for_ajax()

        self.load_preset("Test Preset")

        solvent = self.driver.find_element_by_name('calc_solvent')
        theory = Select(self.driver.find_element_by_id("calc_theory_level"))
        func = self.driver.find_element_by_id("calc_functional")
        basis_set = self.driver.find_element_by_id("calc_basis_set")
        specifications = self.driver.find_element_by_id("calc_specifications")
        software = self.driver.find_element_by_id("calc_software")

        self.assertEqual(solvent.get_attribute('value'), params['solvent'])
        self.assertEqual(theory.first_selected_option.text, params['theory'])
        self.assertEqual(func.get_attribute('value'), params['functional'])
        self.assertEqual(basis_set.get_attribute('value'), params['basis_set'])
        self.assertEqual(software.get_attribute('value'), params['software'])
        self.assertEqual(specifications.get_attribute('value'), "tightscf")

    def test_project_preset(self):
        proj = Project.objects.create(name="My Project", author=self.profile)
        proj.save()

        params = {
                'software': 'Gaussian',
                'type': 'Frequency Calculation',
                'charge': '+1',
                'solvent': 'Chloroform',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'solvation_model': 'CPCM',
                'solvation_radii': 'Bondi',
                'project': 'My Project',
                'specifications': 'nosymm',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.set_project_preset()

        self.lget("/projects")
        self.click_project("My Project")
        self.create_molecule_in_project()

        solvent = self.driver.find_element_by_name('calc_solvent')
        solvation_model = Select(self.driver.find_element_by_name('calc_solvation_model'))
        solvation_radii = Select(self.driver.find_element_by_name('calc_solvation_radii'))
        theory = Select(self.driver.find_element_by_id("calc_theory_level"))
        func = self.driver.find_element_by_id("calc_functional")
        basis_set = self.driver.find_element_by_id("calc_basis_set")
        software = self.driver.find_element_by_id("calc_software")
        specifications = self.driver.find_element_by_id("calc_specifications")

        self.assertEqual(solvent.get_attribute('value'), params['solvent'])
        self.assertEqual(solvation_model.first_selected_option.text, params['solvation_model'])
        self.assertEqual(solvation_radii.first_selected_option.text, params['solvation_radii'])
        self.assertEqual(theory.first_selected_option.text, params['theory'])
        self.assertEqual(func.get_attribute('value'), params['functional'])
        self.assertEqual(basis_set.get_attribute('value'), params['basis_set'])
        self.assertEqual(software.get_attribute('value'), params['software'])
        self.assertEqual(specifications.get_attribute('value'), "nosymm")

    def test_duplicate_project_preset(self):
        proj = Project.objects.create(name="My Project", author=self.profile)
        proj.save()

        params = {
                'software': 'Gaussian',
                'type': 'Frequency Calculation',
                'charge': '+1',
                'solvent': 'Chloroform',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'solvation_model': 'CPCM',
                'solvation_radii': 'Bondi',
                'project': 'My Project',
                'specifications': 'nosymm',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.set_project_preset()
        presets = self.get_name_presets()
        param_count = Parameters.objects.count()
        self.assertEqual(param_count, 1)

        self.lget("/launch/")
        self.calc_input_params(params)
        self.set_project_preset()

        self.lget("/launch/")
        presets = self.get_name_presets()
        self.assertEqual(len(presets), 1)
        param_count = Parameters.objects.count()
        self.assertEqual(param_count, 2)

    def test_project_preset_independance(self):
        proj = Project.objects.create(name="My Project", author=self.profile)
        proj.save()

        params = {
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
        self.calc_input_params(params)
        self.set_project_preset()
        self.delete_preset("My Project Default")
        self.lget("/projects/")
        self.assertEqual(self.get_number_projects(), 1)

    def test_unseen_calc_badge(self):
        self.setup_test_group()
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.assertEqual(self.get_number_unseen_calcs(), 0)

        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

        self.assertEqual(self.get_number_unseen_calcs(), 1)

        self.see_latest_calc()
        self.assertEqual(self.get_number_unseen_calcs(), 0)

    def test_unseen_calc_badge_click(self):
        self.setup_test_group()
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.assertEqual(self.get_number_unseen_calcs(), 0)

        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

        self.assertEqual(self.get_number_unseen_calcs(), 1)

        self.click_latest_calc()
        self.lget("/home")
        ind = 0
        while self.get_number_unseen_calcs() != 0:
            time.sleep(1)
            self.lget("/home")
            ind += 1
            if ind == 3:
                break
        self.assertEqual(self.get_number_unseen_calcs(), 0)

    def test_see_all_unseen(self):
        self.setup_test_group()

        o1 = CalculationOrder.objects.create(author=self.profile, last_seen_status=1)
        c1a = Calculation.objects.create(order=o1, status=2)
        c1b = Calculation.objects.create(order=o1, status=2)

        o2 = CalculationOrder.objects.create(author=self.profile, last_seen_status=1)
        c2a = Calculation.objects.create(order=o2, status=2)

        o1.save()
        c1a.save()
        c1b.save()
        o2.save()
        c2a.save()
        self.profile.unseen_calculations = 2
        self.profile.save()

        for i in range(3):
            self.lget("/calculations/")
            if self.get_number_unseen_calcs() == 2:
                break
            time.sleep(1)
        else:
            raise Exception("No unseen calculations")

        self.assertEqual(self.get_number_unseen_calcs_manually(), 2)

        self.see_all()

        for i in range(3):
            self.lget("/calculations/")
            if self.get_number_unseen_calcs() == 0:
                break
            time.sleep(1)
        else:
            raise Exception("Remaining calculations")

        self.assertEqual(self.get_number_unseen_calcs(), 0)
        self.assertEqual(self.get_number_unseen_calcs_manually(), 0)

    def test_clean_all_successful(self):
        self.setup_test_group()

        o1 = CalculationOrder.objects.create(author=self.profile)
        c1 = Calculation.objects.create(order=o1, status=1)

        o2 = CalculationOrder.objects.create(author=self.profile, last_seen_status=1)
        c2 = Calculation.objects.create(order=o2, status=2)

        o3 = CalculationOrder.objects.create(author=self.profile, last_seen_status=0)
        c3 = Calculation.objects.create(order=o3, status=0)

        o4 = CalculationOrder.objects.create(author=self.profile, last_seen_status=2)
        c4 = Calculation.objects.create(order=o4, status=2)

        o5 = CalculationOrder.objects.create(author=self.profile)
        c5 = Calculation.objects.create(order=o5, status=3)

        o6 = CalculationOrder.objects.create(author=self.profile, last_seen_status=2)
        c6 = Calculation.objects.create(order=o6, status=3)

        o1.save()
        c1.save()
        o2.save()
        c2.save()
        o3.save()
        c3.save()
        o4.save()
        c4.save()
        o5.save()
        c5.save()
        o6.save()
        c6.save()
        o1.last_seen_status = 1
        o5.last_seen_status = 3
        o1.save()
        o5.save()

        self.profile.unseen_calculations = 2
        self.profile.save()

        for i in range(3):
            self.lget("/calculations/")
            if self.get_number_unseen_calcs() == 2:
                break
            time.sleep(1)
        else:
            raise Exception("No unseen calculations")

        self.assertEqual(self.get_number_unseen_calcs_manually(), 2)
        self.assertEqual(self.get_number_calc_orders(), 6)

        self.wait_for_ajax()
        self.clean_all_successful()
        self.wait_for_ajax()

        #Check for frontend removal
        self.assertEqual(self.get_number_unseen_calcs_manually(), 1)
        self.assertEqual(self.get_number_calc_orders(), 4)

        #Check for backend removal
        for i in range(3):
            self.lget("/calculations/")
            if self.get_number_unseen_calcs() == 1:
                break
            time.sleep(1)
        else:
            raise Exception("Remaining calculations")

        self.assertEqual(self.get_number_unseen_calcs_manually(), 1)
        self.assertEqual(self.get_number_calc_orders(), 4)

    def test_clean_all_completed(self):
        self.setup_test_group()

        o1 = CalculationOrder.objects.create(author=self.profile)
        c1 = Calculation.objects.create(order=o1, status=1)

        o2 = CalculationOrder.objects.create(author=self.profile, last_seen_status=1)
        c2 = Calculation.objects.create(order=o2, status=2)

        o3 = CalculationOrder.objects.create(author=self.profile, last_seen_status=0)
        c3 = Calculation.objects.create(order=o3, status=0)

        o4 = CalculationOrder.objects.create(author=self.profile, last_seen_status=2)
        c4 = Calculation.objects.create(order=o4, status=2)

        o5 = CalculationOrder.objects.create(author=self.profile)
        c5 = Calculation.objects.create(order=o5, status=3)

        o6 = CalculationOrder.objects.create(author=self.profile, last_seen_status=2)
        c6 = Calculation.objects.create(order=o6, status=3)

        o1.save()
        c1.save()
        o2.save()
        c2.save()
        o3.save()
        c3.save()
        o4.save()
        c4.save()
        o5.save()
        c5.save()
        o6.save()
        c6.save()
        o1.last_seen_status = 1
        o5.last_seen_status = 3
        o1.save()
        o5.save()

        self.profile.unseen_calculations = 2
        self.profile.save()

        for i in range(3):
            self.lget("/calculations/")
            if self.get_number_unseen_calcs() == 2:
                break
            time.sleep(1)
        else:
            raise Exception("No unseen calculations")

        self.assertEqual(self.get_number_unseen_calcs_manually(), 2)
        self.assertEqual(self.get_number_calc_orders(), 6)

        self.wait_for_ajax()
        self.clean_all_completed()
        self.wait_for_ajax()

        #Check for frontend removal
        self.assertEqual(self.get_number_unseen_calcs_manually(), 0)
        self.assertEqual(self.get_number_calc_orders(), 2)

        #Check for backend removal
        for i in range(3):
            self.lget("/calculations/")
            if self.get_number_unseen_calcs() == 0:
                break
            time.sleep(1)
        else:
            raise Exception("Remaining calculations")

        self.assertEqual(self.get_number_unseen_calcs_manually(), 0)
        self.assertEqual(self.get_number_calc_orders(), 2)

    def test_delete_unseen_calc(self):
        self.setup_test_group()
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.assertEqual(self.get_number_unseen_calcs(), 0)

        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())
        self.lget("/projects/")
        self.delete_project("SeleniumProject")

        self.driver.refresh()
        ind = 0
        while self.get_number_projects() > 0:
            time.sleep(1)
            ind += 1
            if ind == 3:
                break
            self.lget("/projects/")

        self.lget("/calculations/")

        self.assertEqual(self.get_number_unseen_calcs(), 0)
        self.assertEqual(self.get_number_calc_orders(), 0)

    def test_delete_unseen_calc2(self):
        self.setup_test_group()
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.assertEqual(self.get_number_unseen_calcs(), 0)

        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())
        self.lget("/projects/")
        self.click_project("SeleniumProject")
        self.delete_molecule("test")

        self.driver.refresh()
        ind = 0
        while self.get_number_molecules() > 0:
            time.sleep(1)
            ind += 1
            if ind == 3:
                break
            self.driver.refresh()

        self.lget("/calculations/")

        self.assertEqual(self.get_number_unseen_calcs(), 0)
        self.assertEqual(self.get_number_calc_orders(), 0)

    def test_related_calculations(self):
        self.setup_test_group()

        params = {
                'mol_name': 'H2',
                'name': 'H2',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'H2.sdf',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()

        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())

        self.lget("/projects/")
        self.click_project("SeleniumProject")
        self.click_molecule("H2")
        self.click_ensemble("H2")

        calc = Calculation.objects.latest('id')
        order = calc.order

        orders = self.get_related_orders()

        self.assertEqual(len(orders), 1)
        self.assertEqual(int(orders[0].split()[1]), order.id)

        calcs = self.get_related_calculations(order.id)

        self.assertEqual(len(calcs), 1)
        self.assertEqual(int(calcs[0].split()[1]), calc.id)

        with self.assertRaises(Exception):
            calcs2 = self.get_related_calculations(order.id + 1)

    def test_related_calculations_from_structure(self):
        self.setup_test_group()

        params = {
                'mol_name': 'H2',
                'name': 'H2',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'H2.sdf',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()

        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())

        self.lget("/projects/")
        self.click_project("SeleniumProject")
        self.click_molecule("H2")
        self.click_ensemble("H2")
        self.launch_structure_next_step()

        params2 = {
                'type': 'Frequency Calculation',
                }
        self.calc_input_params(params2)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())

        self.lget("/projects/")
        self.click_project("SeleniumProject")
        self.click_molecule("H2")
        self.click_ensemble("H2")

        calc = Calculation.objects.latest('id')
        order = calc.order

        orders = self.get_related_orders()

        self.assertEqual(len(orders), 2)
        self.assertEqual(int(orders[1].split()[1]), order.id)

        calcs = self.get_related_calculations(order.id)

        self.assertEqual(len(calcs), 1)
        self.assertEqual(int(calcs[0].split()[1]), calc.id)

    def test_related_calculations_from_ensemble(self):
        self.setup_test_group()

        params = {
                'mol_name': 'H2',
                'name': 'H2',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'H2.sdf',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()

        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())

        self.lget("/projects/")
        self.click_project("SeleniumProject")
        self.click_molecule("H2")
        self.click_ensemble("H2")
        self.launch_ensemble_next_step()

        params2 = {
                'type': 'Frequency Calculation',
                }
        self.calc_input_params(params2)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())

        self.lget("/projects/")
        self.click_project("SeleniumProject")
        self.click_molecule("H2")
        self.click_ensemble("H2")

        calc = Calculation.objects.latest('id')
        order = calc.order

        orders = self.get_related_orders()

        self.assertEqual(len(orders), 2)
        self.assertEqual(int(orders[1].split()[1]), order.id)

        calcs = self.get_related_calculations(order.id)

        self.assertEqual(len(calcs), 1)
        self.assertEqual(int(calcs[0].split()[1]), calc.id)

    def test_create_empty_folders(self):
        self.setup_test_group()
        proj = Project.objects.create(name="Proj", author=self.profile)
        proj.save()

        self.assertEqual(proj.main_folder.folder_set.count(), 0)
        self.lget("/projects/")
        self.click_icon_folder("Proj")

        self.assertEqual(self.get_number_folders(), 0)
        self.create_empty_folder()

        proj = Project.objects.get(name="Proj", author=self.profile)
        self.assertEqual(proj.main_folder.folder_set.count(), 1)
        self.assertEqual(self.get_number_folders(), 1)
        self.assertEqual(self.get_number_folder_ensembles(), 0)

        self.create_empty_folder()
        self.assertEqual(self.get_number_folders(), 2)

        names = self.get_name_folders()
        self.assertEqual(len(set(names)), 2)

        self.drag_folder_to_folder(names[0], names[1])

        self.assertEqual(self.get_number_folders(), 1)
        self.assertEqual(self.get_name_folders()[0], names[1])
        self.assertEqual(self.get_number_folder_ensembles(), 0)
        self.click_folder(names[1])

        self.assertEqual(self.get_number_folders(), 1)
        self.assertEqual(self.get_name_folders()[0], names[0])
        self.assertEqual(self.get_number_folder_ensembles(), 0)

    def test_folders_ensembles(self):
        self.setup_test_group()

        params = {
                'mol_name': 'H2',
                'name': 'H2',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'Proj',
                'in_file': 'H2.sdf',
                }
        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.click_latest_calc()
        self.flag_ensemble()

        self.lget("/projects/")
        self.click_icon_folder("Proj")

        self.assertEqual(self.get_number_folders(), 0)
        self.assertEqual(self.get_number_folder_ensembles(), 1)

        self.create_empty_folder()
        self.assertEqual(self.get_number_folders(), 1)

        folder_name = self.get_name_folders()[0]

        self.drag_ensemble_to_folder("{} -{}".format(params['mol_name'], params['name']), folder_name)

        self.assertEqual(self.get_number_folders(), 1)
        self.assertEqual(self.get_number_folder_ensembles(), 0)

        self.click_folder(folder_name)

        self.assertEqual(self.get_number_folders(), 0)
        self.assertEqual(self.get_number_folder_ensembles(), 1)

        self.lget("/projects/")
        self.click_project("Proj")
        self.click_molecule("H2")
        self.click_ensemble("H2")
        self.flag_ensemble()

        self.lget("/projects/")
        self.click_icon_folder("Proj")

        self.assertEqual(self.get_number_folders(), 1)
        self.assertEqual(self.get_number_folder_ensembles(), 0)

        self.click_folder(folder_name)
        self.assertEqual(self.get_number_folders(), 0)
        self.assertEqual(self.get_number_folder_ensembles(), 0)


class UserPermissionsTests(CalcusLiveServer):
    def test_launch_without_group(self):
        params = {
                'mol_name': 'test',
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
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations")
        self.assertEqual(self.get_number_calc_orders(), 1)

    def test_private_project_invisible_to_others(self):
        self.setup_test_group()

        self.lget("/projects/")
        self.create_empty_project()

        self.assertEqual(self.get_number_projects(), 1)
        self.click_icon_shield("My Project")

        self.assertEqual(self.get_number_projects(), 1)

        self.logout()
        self.login("Student", self.password)

        self.lget("/projects/{}".format(self.username))

        self.assertEqual(self.get_number_projects(), 0)

    def test_private_project_invisible_to_others2(self):
        self.setup_test_group()

        self.logout()
        self.login("Student", self.password)

        self.lget("/projects/")
        self.create_empty_project()

        self.assertEqual(self.get_number_projects(), 1)
        self.click_icon_shield("My Project")

        self.assertEqual(self.get_number_projects(), 1)

        self.logout()
        self.login(self.username, self.password)

        self.lget("/projects/Student")

        self.assertEqual(self.get_number_projects(), 0)

class XtbCalculationTestsPI(CalcusLiveServer):

    @classmethod
    def setUpClass(cls):
        cls.patcher = mock.patch.dict(os.environ, {"CAN_USE_CACHED_LOGS": "true"})
        cls.patcher.start()
        super().setUpClass()

    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.profile)
        g.save()
        self.profile.is_PI = True
        self.profile.save()

        self.login(self.username, self.password)

    def test_opt(self):
        params = {
                'mol_name': 'test',
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
                'mol_name': 'test',
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
                'mol_name': 'test',
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
                'mol_name': 'test',
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

    def test_freq_solv_GBSA(self):
        params = {
                'mol_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'solvent': 'Chloroform',
                'solvation_model': 'GBSA',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()

    def test_freq_solv_ALPB(self):
        params = {
                'mol_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'solvent': 'Chloroform',
                'solvation_model': 'ALPB',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()

    def test_invalid_solvent(self):
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.sdf',
                'solvent': 'dichloroethane',
                'solvation_model': 'ALPB',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertFalse(self.latest_calc_successful())

        self.details_latest_order()
        msg = self.get_error_messages()
        self.assertEqual(len(msg), 1)
        self.assertTrue("invalid solvent" in msg[0].lower())


    def test_conf_search(self):
        params = {
                'mol_name': 'test',
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

    def test_conf_search_gfnff(self):
        params = {
                'mol_name': 'test',
                'type': 'Conformational Search',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.sdf',
                'specifications': '--gfnff',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

    def test_conf_search_invalid_specification(self):
        params = {
                'mol_name': 'test',
                'type': 'Conformational Search',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.sdf',
                'specifications': '--gfn2-ff',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertFalse(self.latest_calc_successful())

    def test_conf_search_gfnff_sp(self):
        params = {
                'mol_name': 'test',
                'type': 'Conformational Search',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.sdf',
                'specifications': '--gfn2//gfnff',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

    def test_ts(self):
        params = {
                'mol_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ts.xyz',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())

    def test_scan_distance(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_scan_angle(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_scan_dihedral(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_freeze_distance(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.driver.implicitly_wait(5)
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_distance2(self):
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Distance', [1, 4]], ['Freeze', 'Distance', [2, 3]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.driver.implicitly_wait(5)
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_angle(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_dihedral(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_ensemble_second_step(self):
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.xyz',
                'charge': '+1'
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
                #project and charge implicit
                }
        self.calc_input_params(params2)

        charge = Select(self.driver.find_element_by_name('calc_charge'))
        self.assertEqual(charge.first_selected_option.text, params['charge'])

        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_structure_second_step(self):
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.xyz',
                'charge': '+1',
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
                #project and charge implicit
                }

        charge = Select(self.driver.find_element_by_name('calc_charge'))
        self.assertEqual(charge.first_selected_option.text, params['charge'])

        self.calc_input_params(params2)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_multiple_structures_second_step(self):
        in_files = ["batch/benzene{:02d}.xyz".format(i) for i in range(1, 5)]
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_files': in_files,
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()

        self.select_conformers([2, 3])

        self.launch_structure_next_step()

        params2 = {
                'type': 'Single-Point Energy',
                }

        self.calc_input_params(params2)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(100)

        self.details_latest_order()
        num = self.get_number_calc_in_order()
        self.assertEqual(num, 2)

        order = CalculationOrder.objects.latest('id')
        calcs = order.calculation_set.all()
        self.assertIn(calcs[0].structure.number, [2, 3])
        self.assertIn(calcs[1].structure.number, [2, 3])
        self.assertNotEqual(calcs[0].structure.number, calcs[1].structure.number)

    def test_NEB_from_file(self):
        params = {
                'mol_name': 'test',
                'type': 'Minimum Energy Path',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'xtb',
                'in_file': 'elimination_substrate.xyz',
                'aux_file': 'elimination_product.xyz',
                'charge': '-1',
                'specifications': '--nimages 3',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 5)

    def test_NEB_from_structure(self):
        params = {
                'mol_name': 'elimination_substrate',
                'name': 'start',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Distance', [1, 4], [1.1, 3.5, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'xtb',
                'in_file': 'elimination_substrate.xyz',
                'charge': '-1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.launch_structure_next_step()

        params = {
                'name': 'test',
                'type': 'Minimum Energy Path',
                'project': 'SeleniumProject',
                'software': 'xtb',
                'aux_structure': ['elimination_substrate', 'elimination_substrate', 4],
                'specifications': '--nimages 3',
                }

        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())

    def test_NEB_hybrid(self):
        params = {
                'mol_name': 'elimination_substrate',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Distance', [1, 4], [1.1, 3.5, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'xtb',
                'in_file': 'elimination_substrate.xyz',
                'charge': '-1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())

        self.lget("/launch/")
        params = {
                'name': 'test',
                'type': 'Minimum Energy Path',
                'project': 'SeleniumProject',
                'software': 'xtb',
                'aux_structure': ['elimination_substrate', 'elimination_substrate', 4],
                'in_file': 'elimination_substrate.xyz',
                'specifications': '--nimages 3',
                'charge': '-1',
                }

        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())

    def test_constrained_conf_search(self):
        params = {
                'mol_name': 'test',
                'type': 'Constrained Conformational Search',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'pentane.mol',
                'constraints': [['Freeze', 'Angle', [1, 5, 8]]],
                }

        self.lget("/launch/")

        xyz = parse_xyz_from_file(os.path.join(tests_dir, 'pentane.xyz'))
        ang0 = get_angle(xyz, 1, 5, 8)

        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())

        e = Ensemble.objects.latest('id')
        for s in e.structure_set.all():
            s_xyz = parse_xyz_from_text(s.xyz_structure)
            ang = get_angle(xyz, 1, 5, 8)
            self.assertTrue(np.isclose(ang, ang0, atol=0.5))


class XtbCalculationTestsStudent(CalcusLiveServer):
    @classmethod
    def setUpClass(cls):
        cls.patcher = mock.patch.dict(os.environ, {"CAN_USE_CACHED_LOGS": "true"})
        cls.patcher.start()
        super().setUpClass()

    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.profile)
        g.save()

        u = User.objects.create_user(username="Student", password=self.password)
        u.save()

        p = Profile.objects.get(user__username="Student")
        p.member_of = g
        p.save()

        self.profile.is_PI = True
        self.profile.save()

        self.login("Student", self.password)

    def test_opt(self):
        params = {
                'mol_name': 'test',
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
                'mol_name': 'test',
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

    @mock.patch.dict(os.environ, {'CAN_USE_CACHED_CALCULATIONS': 'false'})
    def test_parse_cancelled_calc(self):
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Angle', [5, 2, 13], [90, 180, 200]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'Ph2I_cation.mol',
                'charge': '+1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_running(5)
        time.sleep(5)
        self.details_latest_order()
        self.cancel_all_calc()

        self.lget("/calculations/")
        self.wait_latest_calc_error(10)

        self.click_latest_calc()
        self.wait_for_ajax()
        self.assertGreaterEqual(self.get_number_conformers(), 1)

    def test_default_settings_from_ensemble(self):
        params = {
                'mol_name': 'test',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'xtb',
                'type': 'Geometrical Optimisation',
                'charge': '+1',
                'solvent': 'dcm',
                'solvation_model': 'GBSA',
                'project': 'New Project',
                'new_project_name': 'Proj',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()

        self.lget("/calculations")
        self.wait_latest_calc_done(120)
        self.click_latest_calc()

        self.launch_ensemble_next_step()

        solvent = self.driver.find_element_by_name('calc_solvent')
        charge = self.driver.find_element_by_name('calc_charge')
        solvation_model = Select(self.driver.find_element_by_name('calc_solvation_model'))
        software = self.driver.find_element_by_id("calc_software")

        self.assertEqual(solvent.get_attribute('value'), params['solvent'])
        self.assertEqual(charge.get_attribute('value'), params['charge'])
        self.assertEqual(solvation_model.first_selected_option.text, params['solvation_model'])
        self.assertEqual(software.get_attribute('value'), params['software'])

    def test_default_settings_from_structure(self):
        params = {
                'mol_name': 'test',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'xtb',
                'type': 'Geometrical Optimisation',
                'charge': '+1',
                'solvent': 'dcm',
                'solvation_model': 'GBSA',
                'project': 'New Project',
                'new_project_name': 'Proj',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()

        self.lget("/calculations")
        self.wait_latest_calc_done(120)
        self.click_latest_calc()

        self.launch_structure_next_step()

        solvent = self.driver.find_element_by_name('calc_solvent')
        charge = self.driver.find_element_by_name('calc_charge')
        solvation_model = Select(self.driver.find_element_by_name('calc_solvation_model'))
        software = self.driver.find_element_by_id("calc_software")

        self.assertEqual(solvent.get_attribute('value'), params['solvent'])
        self.assertEqual(charge.get_attribute('value'), params['charge'])
        self.assertEqual(solvation_model.first_selected_option.text, params['solvation_model'])
        self.assertEqual(software.get_attribute('value'), params['software'])

    def test_default_settings_from_frame(self):
        params = {
                'mol_name': 'test',
                'in_file': 'Ph2I_cation.xyz',
                'software': 'xtb',
                'type': 'Geometrical Optimisation',
                'charge': '+1',
                'solvent': 'dcm',
                'solvation_model': 'GBSA',
                'project': 'New Project',
                'new_project_name': 'Proj',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()

        self.lget("/calculations")
        self.wait_latest_calc_done(120)
        self.details_latest_order()
        self.details_first_calc()
        self.launch_frame_next_step()

        solvent = self.driver.find_element_by_name('calc_solvent')
        charge = self.driver.find_element_by_name('calc_charge')
        solvation_model = Select(self.driver.find_element_by_name('calc_solvation_model'))
        software = self.driver.find_element_by_id("calc_software")

        self.assertEqual(solvent.get_attribute('value'), params['solvent'])
        self.assertEqual(charge.get_attribute('value'), params['charge'])
        self.assertEqual(solvation_model.first_selected_option.text, params['solvation_model'])
        self.assertEqual(software.get_attribute('value'), params['software'])

class OrcaCalculationTestsPI(CalcusLiveServer):
    @classmethod
    def setUpClass(cls):
        cls.patcher = mock.patch.dict(os.environ, {"CAN_USE_CACHED_LOGS": "true"})
        cls.patcher.start()
        super().setUpClass()

    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.profile)
        g.save()
        self.profile.is_PI = True
        self.profile.save()

        self.login(self.username, self.password)

    def test_sp_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_HF(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_HF_CPCM(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT2(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_RIMP2(self):
        params = {
                'mol_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'H2.sdf',
                'software': 'ORCA',
                'theory': 'RI-MP2',
                'basis_set': 'cc-pVDZ',
                'specifications': 'cc-pVDZ/C',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(300)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_HF(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_DFT(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_DFT_single_atom(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_RIMP2(self):
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'H2.sdf',
                'software': 'ORCA',
                'theory': 'RI-MP2',
                'basis_set': 'cc-pVDZ',
                'specifications': 'cc-pVDZ/C',
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
                'mol_name': 'test',
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
                'mol_name': 'test',
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
                'mol_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'PW92',
                'basis_set': 'Def2-SVP',
                'specifications': 'NUMFREQ',
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
                'mol_name': 'test',
                'type': 'Frequency Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'RI-MP2',
                'basis_set': 'cc-pVDZ',
                'specifications': 'cc-pVDZ/C NUMFREQ',
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
                'mol_name': 'test',
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
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_ts_HF(self):
        params = {
                'mol_name': 'test',
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
                'mol_name': 'test',
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
                'mol_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'mini_ts.xyz',
                'software': 'ORCA',
                'theory': 'RI-MP2',
                'basis_set': 'cc-pVDZ',
                'specifications': 'cc-pVDZ/C',
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
                'mol_name': 'test',
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
                'mol_name': 'test',
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
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 5)

    def test_scan_angle_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(250)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_scan_dihedral_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(250)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_freeze_distance_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_distance_SE2(self):
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Distance', [1, 4]], ['Freeze', 'Distance', [2, 3]]],
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_angle_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_dihedral_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_nmr_DFT(self):
        params = {
                'mol_name': 'test',
                'type': 'NMR Prediction',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'Def2/JK',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(60)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_DFT_loose(self):
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'looseopt',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_DFT_grid6(self):
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'grid6',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_DFT_default_pop(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        prop = Property.objects.latest('id')
        self.assertIn("Mulliken:", prop.charges)
        self.assertIn("Loewdin:", prop.charges)

    def test_DFT_hirshfeld_pop(self):
        params = {
                'mol_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'P_Hirshfeld',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        prop = Property.objects.latest('id')
        self.assertIn("Hirshfeld:", prop.charges)

class GaussianCalculationTestsPI(CalcusLiveServer):
    @classmethod
    def setUpClass(cls):
        cls.patcher = mock.patch.dict(os.environ, {"CAN_USE_CACHED_LOGS": "true"})
        cls.patcher.start()
        super().setUpClass()

    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.profile)
        g.save()
        self.profile.is_PI = True
        self.profile.save()

        self.login(self.username, self.password)

    def test_sp_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_HF(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT_SMD18(self):
        params = {
                'mol_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'solvation_method': 'SMD',
                'solvation_radii': 'SMD18',
                'solvent': 'Methanol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT_PCM(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT_CPCM(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_sp_DFT2(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)


    def test_opt_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_HF(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_DFT(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_opt_DFT_single_atom(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)


    def test_freq_SE(self):
        params = {
                'mol_name': 'test',
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
                'mol_name': 'test',
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
                'mol_name': 'test',
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
                'mol_name': 'test',
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
                'mol_name': 'test',
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
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_ts_HF(self):
        params = {
                'mol_name': 'test',
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
                'mol_name': 'test',
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
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 11)

    def test_scan_angle_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 11)

    def test_scan_dihedral_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 11)

    def test_freeze_distance_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_angle_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_dihedral_SE(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_dihedral_SE2(self):
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Dihedral', [1, 2, 3, 4]], ['Freeze', 'Dihedral', [2, 3, 4, 5]]],
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_nmr_DFT(self):
        params = {
                'mol_name': 'test',
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

    def test_DFT_pop(self):
        params = {
                'mol_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'pop(nbo)'
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        prop = Property.objects.latest('id')
        self.assertIn("NBO:", prop.charges)

    def test_DFT_pop_opt(self):
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'pop(nbo)'
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

        prop = Property.objects.latest('id')
        self.assertIn("NBO:", prop.charges)

    def test_DFT_not_pop(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

        prop = Property.objects.latest('id')
        self.assertNotIn("NBO:", prop.charges)

    def test_DFT_multiple_pop(self):
        params = {
                'mol_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'pop(nbo, hirshfeld)'
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

        prop = Property.objects.latest('id')
        self.assertIn("NBO:", prop.charges)
        self.assertIn("Hirshfeld:", prop.charges)
        self.assertIn("CM5:", prop.charges)

    def test_DFT_pop_ESP(self):
        params = {
                'mol_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'pop(esp)'
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

        prop = Property.objects.latest('id')
        self.assertIn("ESP:", prop.charges)

    def test_DFT_pop_HLY(self):
        params = {
                'mol_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'pop(hly)'
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

        prop = Property.objects.latest('id')
        self.assertIn("HLY:", prop.charges)

    def test_DFT_max_step(self):
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'opt(maxstep=5)'
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

        self.click_latest_calc()
        self.click_calc_method(1)

        specs = self.get_confirmed_specifications()
        self.assertEqual(specs, 'opt(maxstep=5)')

    def test_scan_distance_pop(self):
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Distance', [1, 2], [3.5, 5.0, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'Gaussian',
                'in_file': 'CH4.mol',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'pop(nbo)',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 11)
        self.click_calc_method(1)

        specs = self.get_confirmed_specifications()
        self.assertEqual(specs, 'pop(nbo)')

    @mock.patch.dict(os.environ, {'CAN_USE_CACHED_CALCULATIONS': 'false'})
    def test_parse_cancelled_calc(self):
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Angle', [1, 2, 3], [120, 160, 1000]]],
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
        self.wait_latest_calc_running(5)
        time.sleep(5)
        self.details_latest_order()
        self.cancel_all_calc()

        self.lget("/calculations/")
        self.wait_latest_calc_error(10)

        self.click_latest_calc()
        self.assertGreaterEqual(self.get_number_conformers(), 1)

class MiscCalculationTests(CalcusLiveServer):

    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.profile)
        g.save()
        self.profile.is_PI = True
        self.profile.save()

        self.login(self.username, self.password)


    def test_cancel_calc(self):
        params = {
                'mol_name': 'test',
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

        for i in range(10):
            self.driver.refresh()
            s = self.get_calculation_statuses()
            self.assertEqual(len(s), 1)
            if s[0] == "Error - Job cancelled":
                break

            time.sleep(1)

        s = self.get_calculation_statuses()
        self.assertEqual(s[0], "Error - Job cancelled")

    def test_input_file_present(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.details_latest_order()
        self.details_first_calc()

        input_file = self.driver.find_element_by_css_selector(".textarea")
        assert len(input_file.text) > 10

    def test_sp_from_frame(self):
        params = {
                'mol_name': 'test',
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
        self.wait_latest_calc_done(150)
        self.details_latest_order()
        self.details_first_calc()

        self.launch_frame_next_step()
        params = {
                'name': 'test',
                'type': 'Single-Point Energy',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-TZVP',
                }

        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())

    def test_calc_from_extracted_frame(self):
        params = {
                'mol_name': 'CH4',
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
        self.wait_latest_calc_done(150)
        self.details_latest_order()
        self.details_first_calc()

        self.launch_frame_next_step()
        params = {
                'name': 'test',
                'type': 'Single-Point Energy',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-TZVP',
                }

        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)

        self.lget("/projects")
        self.click_project("SeleniumProject")
        self.click_molecule("CH4")
        self.click_ensemble("Extracted frame 1")
        self.launch_ensemble_next_step()

        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)

        self.assertTrue(self.latest_calc_successful())

    def test_multiple_files(self):
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_files': ['CH4.mol', 'H2.mol2', 'H2.sdf', 'ethanol.xyz'],
                'software': 'xtb',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.assertEqual(self.get_number_calc_orders(), 3)
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())

        calcs = Calculation.objects.all()
        for c in calcs:
            self.assertEqual(c.status, 2)

    def test_multiple_files2(self):
        proj = Project.objects.create(name="MyProj", author=self.profile)
        proj.save()
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'MyProj',
                'in_files': ['CH4.mol', 'H2.mol2', 'H2.sdf', 'ethanol.xyz'],
                'software': 'xtb',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.assertEqual(self.get_number_calc_orders(), 3)
        self.wait_all_calc_done(150)
        self.assertTrue(self.all_calc_successful())

        calcs = Calculation.objects.all()
        for c in calcs:
            self.assertEqual(c.status, 2)

    def test_multiple_files_combine(self):
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_files': ['CH4.mol', 'H2.mol2', 'H2.sdf', 'ethanol.xyz'],
                'software': 'xtb',
                'combine': True,
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.assertEqual(self.get_number_calc_orders(), 1)
        self.wait_all_calc_done(150)
        self.assertTrue(self.all_calc_successful())


    def test_many_same_files(self):
        files = ["batch/benzene{:02d}.xyz".format(i) for i in range(1, 11)]
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_files': files,
                'software': 'xtb',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.assertEqual(self.get_number_calc_orders(), 1)
        self.wait_latest_calc_done(600)
        self.assertTrue(self.latest_calc_successful())

        calcs = Calculation.objects.all()
        for c in calcs:
            self.assertEqual(c.status, 2)

    def test_conformer_table1(self):
        proj = Project.objects.create(name="TestProj", author=self.profile)
        mol = Molecule.objects.create(project=proj, name="TestMol")
        e = Ensemble.objects.create(parent_molecule=mol, name="TestEnsemble")

        proj.save()
        mol.save()
        e.save()

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

        self.lget("/ensemble/{}".format(e.id))
        data = self.get_conformer_data()

        for ind, line in enumerate(data):
            self.assertEqual(line[0], str(ind+1))
            self.assertEqual(line[1], "{:.6f}".format(structs[ind][0]))
            self.assertEqual(line[3], str(structs[ind][1]))
            self.assertEqual(line[4], "{:.2f}".format(ref_weights[ind]))

    def test_conformer_table2(self):
        proj = Project.objects.create(name="TestProj", author=self.profile)
        mol = Molecule.objects.create(project=proj, name="TestMol")
        e = Ensemble.objects.create(parent_molecule=mol, name="TestEnsemble")

        proj.save()
        mol.save()
        e.save()

        structs = [[-16.82945685, 9], [-16.82855278, 36], [-16.82760256, 7], [-16.82760254, 9], [-16.82760156, 2], [-16.82558904, 33], [-16.82495672, 1]]#From CREST (GFN2-xTB)
        rel_energies = [i[0] + 16.82945685 for i in structs]

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in reversed(list(enumerate(structs))):
            s = Structure.objects.create(parent_ensemble=e, number=ind+1, degeneracy=structs[ind][1])
            prop = Property.objects.create(parameters=params, energy=structs[ind][0], parent_structure=s)
            prop.save()
            s.save()
        e.save()
        proj.save()
        mol.save()

        ref_weights = [0.34724, 0.53361, 0.03796, 0.04880, 0.01082, 0.02125, 0.00033]

        self.lget("/ensemble/{}".format(e.id))
        data = self.get_conformer_data()

        for ind, line in enumerate(data):
            self.assertEqual(line[0], str(ind+1))
            self.assertEqual(line[1], "{:.6f}".format(structs[ind][0]))
            self.assertEqual(line[3], str(structs[ind][1]))
            self.assertEqual(line[4], "{:.2f}".format(ref_weights[ind]))

    def test_confirmed_specifications(self):
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'CH4.mol',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'freq(NoRaman)',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.click_latest_calc()
        self.click_calc_method(1)

        specs = self.get_confirmed_specifications()
        self.assertEqual(specs, '')

    def test_combine_molecule(self):
        params = {
                'mol_name': 'Test',
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
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())

        self.lget("/projects")
        self.click_project("SeleniumProject")
        self.assertEqual(self.get_number_molecules(), 1)

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())

        self.lget("/projects")
        self.click_project("SeleniumProject")
        self.assertEqual(self.get_number_molecules(), 1)

    def setup_propane_ensemble(self):
        proj = Project.objects.create(name="TestProj", author=self.profile)
        mol = Molecule.objects.create(project=proj, name="TestMol")
        e = Ensemble.objects.create(parent_molecule=mol, name="TestEnsemble")

        proj.save()
        mol.save()
        e.save()

        structs = [[-16.82945685, 9], [-16.82855278, 36], [-16.82760256, 7], [-16.82760254, 9], [-16.82760156, 2], [-16.82558904, 33], [-16.82495672, 1]]#From CREST (GFN2-xTB)
        rel_energies = [i[0] + 16.82945685 for i in structs]

        with open(os.path.join(tests_dir, "propane.xyz")) as f:
            xyz_structure = ''.join(f.readlines())

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs):
            s = Structure.objects.create(parent_ensemble=e, number=ind+1, degeneracy=structs[ind][1], xyz_structure=xyz_structure)
            prop = Property.objects.create(parameters=params, energy=structs[ind][0], parent_structure=s)
            prop.save()
            s.save()
        e.save()
        proj.save()
        mol.save()

    def test_filter_ensemble_energy(self):
        self.setup_propane_ensemble()

        self.lget("/projects/")
        self.click_project("TestProj")
        self.click_molecule("TestMol")
        self.click_ensemble("TestEnsemble")
        self.launch_ensemble_next_step()

        params = {
                'type': 'Geometrical Optimisation',
                'filter': 'By Relative Energy',
                'filter_value': '5',
                }

        self.calc_input_params(params)
        self.calc_launch()

        self.wait_latest_calc_done(300)
        self.assertTrue(self.latest_calc_successful())
        self.details_latest_order()
        self.assertEqual(self.get_number_calc_in_order(), 5)

    def test_filter_ensemble_weight(self):
        self.setup_propane_ensemble()

        self.lget("/projects/")
        self.click_project("TestProj")
        self.click_molecule("TestMol")
        self.click_ensemble("TestEnsemble")
        self.launch_ensemble_next_step()

        params = {
                'type': 'Geometrical Optimisation',
                'filter': 'By Boltzmann Weight',
                'filter_value': '0.05',
                }

        self.calc_input_params(params)
        self.calc_launch()

        self.wait_latest_calc_done(300)
        self.assertTrue(self.latest_calc_successful())
        self.details_latest_order()
        self.assertEqual(self.get_number_calc_in_order(), 2)

class ComplexCalculationTests(CalcusLiveServer):

    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.profile)
        g.save()
        self.profile.is_PI = True
        self.profile.save()

        self.login(self.username, self.password)


    def test_selective_delete(self):

        self.assertTrue(self.try_assert_number_unseen_calcs(0, 3))
        params = {
                'mol_name': 'H2',
                'name': 'H2',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'H2.sdf',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(60)

        self.assertTrue(self.try_assert_number_unseen_calcs(1, 3))
        self.assertTrue(self.get_number_unseen_calcs_manually(), 1)
        self.click_latest_calc()
        self.launch_ensemble_next_step()

        params = {
                'type': 'Frequency Calculation',
                'project': 'SeleniumProject',
                }
        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(60)

        self.assertTrue(self.try_assert_number_unseen_calcs(1, 3))
        self.assertEqual(self.get_number_unseen_calcs_manually(), 1)

        self.lget("/launch/")
        params = {
                'mol_name': 'Ethanol',
                'name': 'Ethanol',
                'type': 'Geometrical Optimisation',
                'project': 'SeleniumProject',
                'in_file': 'ethanol.xyz',
                }
        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(150)
        self.assertEqual(self.get_number_calc_orders(), 3)
        self.assertTrue(self.try_assert_number_unseen_calcs(2, 3))
        self.assertEqual(self.get_number_unseen_calcs_manually(), 2)

        self.lget("/projects/")
        n_mol = self.get_number_calcs_in_project("SeleniumProject")

        self.assertEqual(n_mol, 2)

        self.click_project("SeleniumProject")

        n_e = self.get_number_calcs_in_molecule("H2")

        self.assertEqual(n_e, 2)

        n_e = self.get_number_calcs_in_molecule("Ethanol")

        self.assertEqual(n_e, 2)

        self.delete_molecule("Ethanol")
        self.lget("/calculations/")
        ind = 0
        while ind < 5:
            if self.get_number_calc_orders() == 2:
                break
            ind += 1
            time.sleep(1)
            self.lget("/calculations/")
        self.assertEqual(self.get_number_calc_orders(), 2)

        self.lget("/projects/")
        self.assertEqual(self.get_number_projects(), 1)
        self.assertTrue(self.try_assert_number_unseen_calcs(1, 3))

        n_mol = self.get_number_calcs_in_project("SeleniumProject")
        self.assertEqual(n_mol, 1)

        self.click_project("SeleniumProject")
        self.assertEqual(self.get_number_molecules(), 1)

        n_e = self.get_number_calcs_in_molecule("H2")
        self.assertEqual(n_e, 2)

        self.click_molecule("H2")
        self.assertEqual(self.get_number_ensembles(), 2)

        self.lget("/launch/")
        params = {
                'mol_name': 'Methane',
                'type': 'Geometrical Optimisation',
                'project': 'SeleniumProject',
                'in_file': 'CH4.xyz',
                }
        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(150)
        self.assertEqual(self.get_number_calc_orders(), 3)

        self.assertTrue(self.try_assert_number_unseen_calcs(2, 3))
        self.assertEqual(self.get_number_unseen_calcs_manually(), 2)

        self.lget("/launch/")
        params = {
                'mol_name': 'Ammonia',
                'name': 'NH3',
                'type': 'Geometrical Optimisation',
                'project': 'SeleniumProject',
                'in_file': 'NH3.mol',
                }
        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(150)
        self.assertEqual(self.get_number_calc_orders(), 4)
        self.assertTrue(self.try_assert_number_unseen_calcs(3, 3))
        self.assertEqual(self.get_number_unseen_calcs_manually(), 3)

        self.lget("/projects/")
        n_mol = self.get_number_calcs_in_project("SeleniumProject")

        self.assertEqual(n_mol, 3)

        self.click_project("SeleniumProject")
        self.click_molecule("Ammonia")
        self.delete_ensemble("NH3")
        self.driver.refresh()
        self.assertEqual(self.get_number_ensembles(), 1)
        self.delete_ensemble("File Upload")#Should not delete molecule

        self.lget("/calculations/")

        self.assertEqual(self.get_number_calc_orders(), 3)
        self.assertTrue(self.try_assert_number_unseen_calcs(2, 3))
        self.assertEqual(self.get_number_unseen_calcs_manually(), 2)

        self.lget("/projects/")
        self.delete_project("SeleniumProject")
        time.sleep(2)
        self.lget("/projects/")
        self.assertTrue(self.try_assert_number_unseen_calcs(0, 3))

    def test_advanced_nmr_analysis(self):
        params = {
                'mol_name': 'test',
                'type': 'NMR Prediction',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.sdf',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M062X',
                'basis_set': 'Def2-SVP',
                'specifications': 'Def2/JK',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(60)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.click_calc_method(2)
        self.click_advanced_nmr_analysis()
        self.click_get_shifts()

        shifts = self.get_nmr_shifts()
        self.assertEqual(shifts[1], shifts[2])
        self.assertEqual(shifts[1], shifts[3])
        self.assertNotEqual(shifts[1], shifts[4])
        self.assertNotEqual(shifts[6], shifts[1])

        prop = Property.objects.latest('id')
        calc_shifts = [float(i.split()[2]) for i in prop.simple_nmr.split('\n') if i.strip() != '']
        self.assertEqual(shifts[1], "{:.3f}".format(np.mean(calc_shifts[1:4])))


