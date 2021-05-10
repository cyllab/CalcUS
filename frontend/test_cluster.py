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
from .calcusliveserver import CalcusLiveServer

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

dir_path = os.path.dirname(os.path.realpath(__file__))

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(tests_dir, "scr")
RESULTS_DIR = os.path.join(tests_dir, "results")
KEYS_DIR = os.path.join(tests_dir, "keys")

class ClusterTests(CalcusLiveServer):
    @classmethod
    def setUpClass(cls):
        super().send_slurm_command(cls, "rm -r /home/calcus/scratch")
        super().setUpClass()

    def setUp(self):
        super().setUp()

        self.send_slurm_command("scancel -u slurm")

        if docker:
            connection = redis.Redis(host='redis', port=6379, db=2)
        else:
            connection = redis.Redis(host='localhost', port=6379, db=2)
        connection.flushdb()
        connection.close()

        p = Process(target=self.run_daemon)
        p.start()

    def tearDown(self):
        send_cluster_command("stop\n")
        time.sleep(0.5)# Give time to the daemon to disconnect cleanly
        super().tearDown()

    def run_daemon(self):
        try:
            daemon = ClusterDaemon()
        except SystemExit:
            print("Daemon has exited")
        except:
            traceback.print_exc()

    def test_setup(self):
        self.setup_cluster()
        msg = self.driver.find_element_by_id("test_msg").text
        self.assertEqual(msg, "Connected")

    def setup_cluster(self):
        self.lget("/profile")

        self.add_cluster()

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#owned_accesses > center > table > tbody > tr > th:nth-child(5) > a"))
        )

        self.select_cluster(1)

        self.connect_cluster()

    def test_delete_access(self):
        self.setup_cluster()
        keys = glob.glob("{}/*".format(KEYS_DIR))
        initial_keys = len(keys)

        main_window_handle = None
        while not main_window_handle:
            main_window_handle = self.driver.current_window_handle

        delete_access = self.driver.find_element_by_id("delete_access_button")
        delete_access.click()

        alert = self.driver.switch_to_alert()
        alert.accept()
        self.driver.switch_to_default_content()

        ind = 0
        while len(glob.glob("{}/*".format(KEYS_DIR))) == initial_keys and ind < 5:
            time.sleep(1)
            ind += 1

        keys = glob.glob("{}/*".format(KEYS_DIR))
        self.assertEqual(len(keys), initial_keys-2)

    def test_cluster_settings(self):
        self.lget("/profile")

        adress = self.driver.find_element_by_name("cluster_address")
        adress.send_keys("localhost")

        username = self.driver.find_element_by_name("cluster_username")
        username.send_keys("cluster")

        pal = self.driver.find_element_by_name("cluster_cores")
        pal.clear()
        pal.send_keys("8")

        memory = self.driver.find_element_by_name("cluster_memory")
        memory.clear()
        memory.send_keys("10000")

        password = self.driver.find_element_by_name("cluster_password")
        password.clear()
        password.send_keys("Selenium")

        self.driver.find_element_by_id("add_access_button").click()
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

        adress = self.driver.find_element_by_name("cluster_address")
        adress.send_keys("localhost")

        username = self.driver.find_element_by_name("cluster_username")
        username.send_keys("cluster")

        pal = self.driver.find_element_by_name("cluster_cores")
        pal.clear()
        pal.send_keys("24")

        memory = self.driver.find_element_by_name("cluster_memory")
        memory.clear()
        memory.send_keys("31000")

        password = self.driver.find_element_by_name("cluster_password")
        password.clear()
        password.send_keys("Selenium")

        self.driver.find_element_by_id("add_access_button").click()
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
        msg = self.driver.find_element_by_id("test_msg").text
        self.assertEqual(msg, "Connected")

        self.lget("/profile/")
        manage = self.driver.find_element_by_css_selector("#owned_accesses > center > table > tbody > tr > th:nth-child(5) > a")
        manage.send_keys(Keys.RETURN)

        element = WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element((By.ID, "status_box"), "Connected")
        )
        self.assertNotEqual(self.driver.find_element_by_id("status_box").text.find("Connected"), -1)


    def test_cluster_xtb_crest(self):
        self.setup_cluster()
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

    def test_cluster_constrained_conf_search(self):
        self.setup_cluster()
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

    def test_cluster_xtb_sp(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Single-Point Energy',
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

    def test_cluster_xtb_opt(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
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

    def test_cluster_xtb_freq(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Frequency Calculation',
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

    def test_cluster_scan_distance(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Distance', [1, 4], [3.5, 1.5, 20]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 20)

    def test_cluster_freeze_distance(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Distance', [1, 4]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_cluster_uvvis(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'UV-Vis Calculation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()


    def test_cluster_xtb_ts(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'TS Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'mini_ts.xyz',
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

    def test_cluster_orca_opt(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
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

    def test_cluster_orca_sp(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
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

    def test_cluster_orca_ts(self):
        self.setup_cluster()
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

    def test_cluster_orca_freq(self):
        self.setup_cluster()
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

    def test_cluster_orca_scan(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Angle', [1, 2, 3], [120, 130, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'ORCA',
                'in_file': 'benzene.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_cluster_orca_freeze(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Dihedral', [1, 2, 3, 4]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'ORCA',
                'in_file': 'benzene.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

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
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
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

    def test_cluster_two_connections(self):
        self.setup_test_group()
        self.setup_cluster()
        self.logout()
        self.login("Student", self.password)
        self.setup_cluster()

        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
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

    def test_cluster_gaussian_opt(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
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

    def test_cluster_gaussian_sp(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Single-Point Energy',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
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

    def test_cluster_gaussian_ts(self):
        self.setup_cluster()
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

    def test_cluster_gaussian_freq(self):
        self.setup_cluster()
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

    def test_cluster_gaussian_scan(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Scan', 'Angle', [1, 2, 3], [120, 130, 10]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'Gaussian',
                'in_file': 'benzene.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 11)

    def test_cluster_gaussian_freeze(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Constrained Optimisation',
                'constraints': [['Freeze', 'Dihedral', [1, 2, 3, 4]]],
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'software': 'Gaussian',
                'in_file': 'benzene.mol',
                'theory': 'Semi-empirical',
                'method': 'AM1',
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
        self.wait_latest_calc_running(30)
        time.sleep(5)
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

    def test_relaunch_calc(self):
        self.setup_cluster()
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
        self.assertEqual(self.get_number_unseen_calcs(), 0)
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertEqual(self.get_number_unseen_calcs(), 1)
        self.see_latest_calc()
        self.assertEqual(self.get_number_unseen_calcs(), 0)

    def test_cluster_refetch(self):
        self.setup_cluster()
        params = {
                'mol_name': 'test',
                'type': 'Conformational Search',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'pentane.xyz',
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
        self.wait_latest_calc_running(20)

        self.lget("/profile/")
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
        self.select_cluster(1)
        self.connect_cluster()

        self.lget("/calculations/")
        self.wait_latest_calc_done(300)
        self.assertTrue(self.latest_calc_successful())

    def test_stress_num_calcs(self):
        self.setup_cluster()
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

        self.lget("/projects/")
        n_mol = self.get_number_calcs_in_project("SeleniumProject")

        self.assertEqual(n_mol, 1)

