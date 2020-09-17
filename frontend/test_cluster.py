import os
import time
import sys
import glob
import signal
import selenium
import pexpect
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

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

dir_path = os.path.dirname(os.path.realpath(__file__))

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(tests_dir, "scr")
RESULTS_DIR = os.path.join(tests_dir, "results")
CLUSTER_DIR = os.path.join(tests_dir, "cluster")
KEYS_DIR = os.path.join(tests_dir, "keys")

for s in glob.glob("{}/selenium_screenshots/*.png".format(dir_path)):
    os.remove(s)

class ClusterTests(CalcusLiveServer):
    @classmethod
    def setUpClass(cls):
        child = pexpect.spawn('su - calcus')
        child.expect ('Password:')
        child.sendline('clustertest')
        child.expect('\$')
        child.sendline("rm -r /home/calcus/scratch")
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.server_pid = None
        pid = os.fork()
        if not pid:
            return self.run_daemon()
        self.server_pid = pid

    def tearDown(self):
        super().tearDown()
        os.kill(self.server_pid, signal.SIGTERM)

    def run_daemon(self):
        from .cluster_daemon import ClusterDaemon
        daemon = ClusterDaemon()

    def test_setup(self):
        pass

    def gen_key(self):
        key_private_name = "{}_localhost".format(self.profile.username)
        key_public_name = key_private_name + '.pub'

        self.access = ClusterAccess.objects.create(cluster_address="localhost", cluster_username="calcus", private_key_path=key_private_name, public_key_path=key_public_name, owner=self.profile)
        self.access.save()

        key = rsa.generate_private_key(backend=default_backend(), public_exponent=65537, key_size=2048)

        public_key = key.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)

        pem = key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption())
        with open(os.path.join(KEYS_DIR, key_private_name), 'wb') as out:
            out.write(pem)

        with open(os.path.join(KEYS_DIR, key_public_name), 'wb') as out:
            out.write(public_key)
            out.write(b' %b@CalcUS' % bytes(self.username, 'utf-8'))

        child = pexpect.spawn('su - calcus')
        child.expect ('Password:')
        child.sendline('clustertest')
        child.expect('\$')
        child.sendline("echo '{} {}@CalcUS' > /home/calcus/.ssh/authorized_keys".format(public_key.decode('utf-8'), self.username))

    def wait_command_done(self, cmd_id, timeout):
        ind = 0
        while ind < timeout:
            expected_file = os.path.join(CLUSTER_DIR, "done", cmd_id)
            if os.path.isfile(expected_file):
                return True
            ind += 1
            time.sleep(1)
        return False

    def get_command_status(self, cmd_id):
        expected_file = os.path.join(CLUSTER_DIR, "done", cmd_id)
        assert os.path.isfile(expected_file) == True
        with open(expected_file) as f:
            lines = f.readlines()
            return lines[0].strip()


    def test_connection(self):
        self.gen_key()
        cmd = ClusterCommand.objects.create(issuer=self.profile)
        with open(os.path.join(CLUSTER_DIR, 'todo', str(cmd.id)), 'w') as out:
            out.write("access_test\n")
            out.write("{}\n".format(self.access.id))

        ret = self.wait_command_done(str(cmd.id), 10)
        self.assertTrue(ret)
        status = self.get_command_status(str(cmd.id))
        self.assertEqual(status, "Connection successful")


    def setup_cluster(self):
        self.lget("/profile")

        adress = self.driver.find_element_by_name("cluster_address")
        adress.send_keys("localhost")

        username = self.driver.find_element_by_name("cluster_username")
        username.send_keys("calcus")

        pal = self.driver.find_element_by_name("cluster_cores")
        pal.clear()
        pal.send_keys("8")

        memory = self.driver.find_element_by_name("cluster_memory")
        memory.clear()
        memory.send_keys("10000")

        self.driver.find_element_by_css_selector("div.field:nth-child(6) > div:nth-child(1) > button:nth-child(1)").click()


        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "public_key_area"))
        )
        ind = 0
        while ind < 5:
            public_key = self.driver.find_element_by_id("public_key_area").text
            if public_key.strip() != "":
                break
            time.sleep(1)
            ind += 1

        child = pexpect.spawn('su - calcus')
        child.expect ('Password:')
        child.sendline('clustertest')
        child.expect('\$')
        child.sendline("echo '{}' > /home/calcus/.ssh/authorized_keys".format(public_key))

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#owned_accesses > center > table > tbody > tr > th:nth-child(5) > a"))
        )

        manage = self.driver.find_element_by_css_selector("#owned_accesses > center > table > tbody > tr > th:nth-child(5) > a")
        manage.send_keys(Keys.RETURN)
        test_access = self.driver.find_element_by_css_selector("#content_container > div > div:nth-child(3) > div > button")
        test_access.click()
        ind = 0
        while ind < 10:
            time.sleep(1)
            try:
                msg = self.driver.find_element_by_id("test_msg").text
                if msg == "Connection successful":
                    break
            except:
                pass

    def test_delete_access(self):
        self.setup_cluster()
        keys = glob.glob("{}/*".format(KEYS_DIR))
        initial_keys = len(keys)

        delete_access = self.driver.find_element_by_css_selector("a.button:nth-child(3)")
        delete_access.click()

        time.sleep(10)
        keys = glob.glob("{}/*".format(KEYS_DIR))
        self.assertEqual(len(keys), initial_keys-2)

    def test_cluster_settings(self):
        self.lget("/profile")

        adress = self.driver.find_element_by_name("cluster_address")
        adress.send_keys("localhost")

        username = self.driver.find_element_by_name("cluster_username")
        username.send_keys("calcus")

        pal = self.driver.find_element_by_name("cluster_cores")
        pal.clear()
        pal.send_keys("8")

        memory = self.driver.find_element_by_name("cluster_memory")
        memory.clear()
        memory.send_keys("10000")

        self.driver.find_element_by_css_selector("div.field:nth-child(6) > div:nth-child(1) > button:nth-child(1)").click()
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "public_key_area"))
        )
        time.sleep(1)

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
        username.send_keys("calcus")

        pal = self.driver.find_element_by_name("cluster_cores")
        pal.clear()
        pal.send_keys("24")

        memory = self.driver.find_element_by_name("cluster_memory")
        memory.clear()
        memory.send_keys("31000")

        self.driver.find_element_by_css_selector("div.field:nth-child(6) > div:nth-child(1) > button:nth-child(1)").click()
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
        self.assertEqual(msg, "Connection successful")

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

    def test_cluster_xtb_sp(self):
        self.setup_cluster()
        params = {
                'calc_name': 'test',
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
                'calc_name': 'test',
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
                'calc_name': 'test',
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
                'calc_name': 'test',
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
                'calc_name': 'test',
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
                'calc_name': 'test',
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
                'calc_name': 'test',
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

    def test_cluster_orca_opt(self):
        self.setup_cluster()
        params = {
                'calc_name': 'test',
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
                'calc_name': 'test',
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

    def test_cluster_orca_freq(self):
        self.setup_cluster()
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

    def test_cluster_orca_scan(self):
        self.setup_cluster()
        params = {
                'calc_name': 'test',
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
                'calc_name': 'test',
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
                'calc_name': 'test',
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
                'calc_name': 'test',
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
                'calc_name': 'test',
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
                'calc_name': 'test',
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

    def test_cluster_gaussian_freq(self):
        self.setup_cluster()
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

    def test_cluster_gaussian_scan(self):
        self.setup_cluster()
        params = {
                'calc_name': 'test',
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
                'calc_name': 'test',
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

    def test_cancel_calc(self):
        self.setup_cluster()
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
            if s[0] == "Error - Job cancelled":
                break

            time.sleep(1)
            ind += 1

        s = self.get_calculation_statuses()
        self.assertEqual(s[0], "Error - Job cancelled")
