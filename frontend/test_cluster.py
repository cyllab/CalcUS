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
import time
import sys
import glob
import signal
import selenium
import pexpect
import psutil
import redis
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import datetime
import traceback
from multiprocessing import Process

from django.contrib.auth.models import User, Group

from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from shutil import copyfile, rmtree

from celery.contrib.testing.worker import start_worker

from calcus.celery import app

from .models import *
from .libxyz import *
from .tasks import send_cluster_command
from .cluster_daemon import ClusterDaemon
from .environment_variables import *

from django.core.management import call_command
from .calcusliveserver import CalcusLiveServer, SCR_DIR, RESULTS_DIR, KEYS_DIR

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from unittest import mock


class ClusterTests(CalcusLiveServer):
    @classmethod
    def setUpClass(cls):
        super().send_slurm_command(cls, "rm -r /home/slurm/scratch")
        super().setUpClass()

    def setUp(self):
        super().setUp()

        self.send_slurm_command("scancel -u slurm")

        connection = redis.Redis(host="redis", port=6379, db=2)
        connection.flushdb()
        connection.close()

        # p = Process(target=self.run_daemon)
        # p.start()

    def tearDown(self):
        time.sleep(0.5)  # Give time to the daemon to disconnect cleanly
        super().tearDown()
        send_cluster_command("stop\n")

    def run_daemon(self):
        try:
            daemon = ClusterDaemon()
        except SystemExit:
            print("Daemon has exited")
        except:
            traceback.print_exc()

    def test_setup(self):
        self.setup_cluster()
        msg = self.driver.find_element(By.ID, "test_msg").text
        self.assertEqual(msg, "Connected")

    def setup_cluster(self):
        self.lget("/profile")

        try:
            access = self.driver.find_element(
                By.CSS_SELECTOR,
                "#owned_accesses > center > table > tbody > tr > th:nth-child(3) > a",
            )
        except selenium.common.exceptions.NoSuchElementException:
            pass
        else:
            return

        self.add_cluster()

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.ID,
                    "public_key_area",
                )
            )
        )

        self.select_cluster(1)

        self.connect_cluster()

    def test_delete_access(self):
        self.setup_cluster()
        keys = glob.glob(f"{KEYS_DIR}/*")
        initial_keys = len(keys)

        main_window_handle = None
        while not main_window_handle:
            main_window_handle = self.driver.current_window_handle

        delete_access = self.driver.find_element(By.ID, "delete_access_button")
        delete_access.click()

        alert = Alert(self.driver)
        alert.accept()

        ind = 0
        while len(glob.glob(f"{KEYS_DIR}/*")) == initial_keys and ind < 5:
            time.sleep(1)
            ind += 1

        keys = glob.glob(f"{KEYS_DIR}/*")
        self.assertEqual(len(keys), initial_keys - 2)

    def test_cluster_settings(self):
        self.lget("/profile")

        adress = self.driver.find_element(By.NAME, "cluster_address")
        adress.send_keys("localhost")

        username = self.driver.find_element(By.NAME, "cluster_username")
        username.send_keys("cluster")

        pal = self.driver.find_element(By.NAME, "cluster_cores")
        pal.clear()
        pal.send_keys("8")

        memory = self.driver.find_element(By.NAME, "cluster_memory")
        memory.clear()
        memory.send_keys("10000")

        password = self.driver.find_element(By.NAME, "cluster_password")
        password.clear()
        password.send_keys("Selenium")

        self.driver.find_element(By.ID, "add_access_button").click()
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "public_key_area"))
        )
        time.sleep(2)

        acc = ClusterAccess.objects.all()
        self.assertEqual(len(acc), 1)
        access = acc[0]
        self.assertEqual(access.memory, 10000)
        self.assertEqual(access.pal, 8)

    def test_cluster_settings2(self):
        self.lget("/profile")

        adress = self.driver.find_element(By.NAME, "cluster_address")
        adress.send_keys("localhost")

        username = self.driver.find_element(By.NAME, "cluster_username")
        username.send_keys("cluster")

        pal = self.driver.find_element(By.NAME, "cluster_cores")
        pal.clear()
        pal.send_keys("24")

        memory = self.driver.find_element(By.NAME, "cluster_memory")
        memory.clear()
        memory.send_keys("31000")

        password = self.driver.find_element(By.NAME, "cluster_password")
        password.clear()
        password.send_keys("Selenium")

        self.driver.find_element(By.ID, "add_access_button").click()
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "public_key_area"))
        )
        time.sleep(1)

        acc = ClusterAccess.objects.all()
        self.assertEqual(len(acc), 1)
        access = acc[0]
        self.assertEqual(access.memory, 31000)
        self.assertEqual(access.pal, 24)

    def test_connection_gui(self):
        self.setup_cluster()
        msg = self.driver.find_element(By.ID, "test_msg").text
        self.assertEqual(msg, "Connected")

        self.lget("/profile/")
        manage = self.driver.find_element(
            By.CSS_SELECTOR,
            "#owned_accesses > center > table > tbody > tr > th:nth-child(3) > a",
        )
        manage.send_keys(Keys.RETURN)

        element = WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element((By.ID, "status_box"), "Connected")
        )
        self.assertNotEqual(
            self.driver.find_element(By.ID, "status_box").text.find("Connected"), -1
        )

    def test_autoselect_resource_remote(self):
        g = ResearchGroup.objects.create(name="Test Group", PI=self.profile)
        g.save()
        self.profile.is_PI = True
        self.profile.save()

        self.setup_cluster()
        params = {
            "mol_name": "test",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "ethanol.sdf",
            "resource": "slurm",
        }

        self.lget("/launch/")

        resources = self.driver.find_elements(
            By.CSS_SELECTOR, "#calc_resource > option"
        )
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].text, "Local")
        self.assertTrue(resources[0].is_selected())

        self.assertEqual(resources[1].text, "slurm")
        self.assertFalse(resources[1].is_selected())

        self.calc_input_params(params)

        resources = self.driver.find_elements(
            By.CSS_SELECTOR, "#calc_resource > option"
        )
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].text, "Local")
        self.assertFalse(resources[0].is_selected())

        self.assertEqual(resources[1].text, "slurm")
        self.assertTrue(resources[1].is_selected())

        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

        self.click_latest_calc()
        self.launch_ensemble_next_step()
        self.wait_for_ajax()

        resources = self.driver.find_elements(
            By.CSS_SELECTOR, "#calc_resource > option"
        )
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].text, "Local")
        self.assertFalse(resources[0].is_selected())

        self.assertEqual(resources[1].text, "slurm")
        self.assertTrue(resources[1].is_selected())

    def test_autoselect_resource_local(self):
        g = ResearchGroup.objects.create(name="Test Group", PI=self.profile)
        g.save()
        self.profile.is_PI = True
        self.profile.save()

        self.setup_cluster()
        params = {
            "mol_name": "test",
            "type": "Single-Point Energy",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "ethanol.sdf",
            "resource": "Local",
        }

        self.lget("/launch/")

        resources = self.driver.find_elements(
            By.CSS_SELECTOR, "#calc_resource > option"
        )
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].text, "Local")
        self.assertTrue(resources[0].is_selected())

        self.assertEqual(resources[1].text, "slurm")
        self.assertFalse(resources[1].is_selected())

        self.calc_input_params(params)

        resources = self.driver.find_elements(
            By.CSS_SELECTOR, "#calc_resource > option"
        )
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].text, "Local")
        self.assertTrue(resources[0].is_selected())

        self.assertEqual(resources[1].text, "slurm")
        self.assertFalse(resources[1].is_selected())

        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

        self.click_latest_calc()
        self.launch_ensemble_next_step()
        self.wait_for_ajax()

        resources = self.driver.find_elements(
            By.CSS_SELECTOR, "#calc_resource > option"
        )
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].text, "Local")
        self.assertTrue(resources[0].is_selected())

        self.assertEqual(resources[1].text, "slurm")
        self.assertFalse(resources[1].is_selected())

    def test_cluster_xtb_crest(self):
        self.setup_cluster()
        params = {
            "mol_name": "test",
            "type": "Conformational Search",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "ethanol.sdf",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

    def test_cluster_orca_mo(self):
        self.setup_cluster()
        params = {
            "mol_name": "test",
            "type": "MO Calculation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "carbo_cation.mol",
            "charge": "+1",
            "software": "ORCA",
            "theory": "HF",
            "basis_set": "Def2-SVP",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.wait_for_ajax()

        self.assertEqual(self.get_number_conformers(), 1)
        self.click_calc_method_not_geom()
        self.assertTrue(self.is_loaded_mo())

    def test_add_cluster_student(self):
        self.setup_test_group()
        self.logout()
        self.login("Student", self.password)
        self.setup_cluster()

    def test_cluster_xtb_student(self):
        self.setup_test_group()
        self.logout()
        self.login("Student", self.password)
        self.setup_cluster()

        params = {
            "mol_name": "test",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "ethanol.sdf",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

    def test_cluster_two_connections(self):
        self.setup_test_group()
        self.setup_cluster()
        self.logout()
        self.login("Student", self.password)
        self.setup_cluster()

        params = {
            "mol_name": "test",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "ethanol.sdf",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

    def test_cluster_gaussian_sp(self):
        self.setup_cluster()
        params = {
            "mol_name": "test",
            "type": "Single-Point Energy",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "benzene.mol",
            "software": "Gaussian",
            "theory": "HF",
            "basis_set": "Def2-SVP",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_gaussian_parse_cancelled_calc(self):
        self.setup_cluster()
        params = {
            "mol_name": "test",
            "type": "Constrained Optimisation",
            "constraints": [["Scan", "Angle", [1, 2, 3], [120, 160, 1000]]],
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "software": "Gaussian",
            "in_file": "CH4.xyz",
            "theory": "Semi-empirical",
            "method": "AM1",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_running(30)
        time.sleep(3)
        self.details_latest_order()
        self.cancel_all_calc()

        self.lget("/calculations/")
        self.wait_latest_calc_error(10)
        time.sleep(5)

        self.click_latest_calc()
        self.assertGreaterEqual(self.get_number_conformers(), 1)

    def test_cancel_calc(self):
        self.setup_cluster()
        params = {
            "mol_name": "test",
            "type": "Conformational Search",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "pentane.mol",
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
            if s[0] == "Error - Job cancelled":
                break

            time.sleep(1)
            ind += 1

        s = self.get_calculation_statuses()
        self.assertEqual(s[0], "Error - Job cancelled")

    @mock.patch.dict(os.environ, {"CACHE_POST_WAIT": "15"})
    def test_relaunch_calc(self):
        self.setup_cluster()
        params = {
            "mol_name": "test",
            "type": "Single-Point Energy",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "ethanol.xyz",
            "software": "Gaussian",
            "theory": "HF",
            "basis_set": "Def2-TZVP",
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

        self.assertEqual(self.get_number_unseen_calcs(), 1)
        time.sleep(2)
        self.relaunch_all_calc()

        self.lget("/calculations/")
        self.assertEqual(self.get_number_unseen_calcs(), 0)
        self.wait_latest_calc_done(300)
        self.assertEqual(self.get_number_unseen_calcs(), 1)
        self.assertTrue(self.latest_calc_successful())

    def test_cluster_unseen_calc(self):
        self.setup_cluster()
        params = {
            "mol_name": "test",
            "type": "Single-Point Energy",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
            "software": "Gaussian",
            "theory": "HF",
            "basis_set": "Def2-SVP",
        }

        self.lget("/launch/")
        self.assertEqual(self.get_number_unseen_calcs(), 0)
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.wait_for_ajax()
        self.assertEqual(self.get_number_unseen_calcs(), 1)
        self.see_latest_calc()
        self.assertEqual(self.get_number_unseen_calcs(), 0)

    def test_cluster_refetch(self):
        self.setup_cluster()
        params = {
            "mol_name": "test",
            "type": "Conformational Search",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "pentane.xyz",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertEqual(self.get_number_unseen_calcs(), 1)
        self.click_latest_calc()
        num = self.get_number_conformers()

        self.lget("/calculations/")
        self.details_latest_order()
        self.refetch_all_calc()
        time.sleep(5)

        self.lget("/calculations/")
        self.assertEqual(self.get_number_unseen_calcs(), 0)
        self.click_latest_calc()
        self.assertEqual(num, self.get_number_conformers())

    def test_cluster_disconnect(self):
        self.setup_cluster()
        params = {
            "mol_name": "test",
            "type": "Conformational Search",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "pentane.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_running(20)

        self.lget("/profile/")
        self.wait_for_ajax()
        self.select_cluster(1)
        self.disconnect_cluster()

        self.lget("/calculations/")

        for i in range(5):
            statuses = self.get_status_calc_orders()
            self.assertEqual(len(statuses), 1)
            self.assertEqual(statuses[0], 1)
            time.sleep(2)
            self.driver.refresh()

        self.lget("/profile/")
        self.wait_for_ajax()
        self.select_cluster(1)
        self.connect_cluster()

        self.lget("/calculations/")
        self.wait_latest_calc_done(300)
        self.assertTrue(self.latest_calc_successful())

    def test_stress_num_calcs(self):
        self.setup_cluster()
        files = [f"batch/benzene{i:02d}.xyz" for i in range(1, 11)]
        params = {
            "mol_name": "test",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_files": files,
            "software": "xtb",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.assertEqual(self.get_number_calc_orders(), 1)
        self.wait_latest_calc_done(600)
        self.assertTrue(self.latest_calc_successful())

        self.lget("/projects/")
        n_mol = self.get_number_calcs_in_project("SeleniumProject")

        self.assertEqual(n_mol, 1)
