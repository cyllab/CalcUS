'''
This file of part of CalcUS.

Copyright (C) 2020-2021 Raphaël Robidas

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
'''


import os
import time
import sys
import glob
import selenium
import datetime
import pexpect
import socket
from unittest import mock

from selenium import webdriver
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.action_chains import ActionChains
from shutil import copyfile, rmtree

from celery.contrib.testing.worker import start_worker
from celery.contrib.abortable import AbortableAsyncResult

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from django.contrib.auth.models import User, Group
from .models import *
from .environment_variables import *

dir_path = os.path.dirname(os.path.realpath(__file__))

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(tests_dir, "scr")
RESULTS_DIR = os.path.join(tests_dir, "results")
CLUSTER_DIR = os.path.join(tests_dir, "cluster")
KEYS_DIR = os.path.join(tests_dir, "keys")

HEADLESS = os.getenv("CALCUS_HEADLESS")

from calcus.celery import app
from frontend import tasks

base_cwd = os.getcwd()

class CalcusLiveServer(StaticLiveServerTestCase):

    host = '0.0.0.0'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.host = socket.gethostbyname(socket.gethostname())

        if docker:
            cls.driver = webdriver.Remote(
                    command_executor='http://selenium:4444/wd/hub',
                    desired_capabilities=DesiredCapabilities.CHROME,
            )
            cls.driver.set_window_size(1920, 1080)
        else:
            chrome_options = Options()
            if HEADLESS is not None and HEADLESS.lower() == "true":
                from pyvirtualdisplay import Display

                display = Display(visible=0, size=(1920, 1080))
                display.start()

            cls.driver = webdriver.Chrome(chrome_options=chrome_options)
            cls.driver.set_window_size(1920, 1080)

        tasks.REMOTE = False
        app.loader.import_module('celery.contrib.testing.tasks')

        cls.celery_worker = start_worker(app, perform_ping_check=False)
        cls.celery_worker.__enter__()

        if os.path.isdir(SCR_DIR):
            rmtree(SCR_DIR)
        if os.path.isdir(RESULTS_DIR):
            rmtree(RESULTS_DIR)
        if os.path.isdir(KEYS_DIR):
            rmtree(KEYS_DIR)

        os.mkdir(SCR_DIR)
        os.mkdir(RESULTS_DIR)
        os.mkdir(KEYS_DIR)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        cls.celery_worker.__exit__(None, None, None)
        os.chdir(base_cwd)#Prevent coverage.py crash
        super().tearDownClass()

    def run(self, result=None):
        self.full_test_name = self.id()
        self.m_name = self._testMethodName
        self._testMethodName = "_test_wrapper"
        super(StaticLiveServerTestCase, self).run(result)
        self._testMethodName = self.m_name

    def _test_wrapper(self):
        m = getattr(self, self.m_name)

        num = 1
        MAX_ATTEMPTS = 3

        exc = None

        print("Running {}".format(self.m_name))
        while True:
            try:
                m()
            except Exception as e:
                if exc is None:
                    exc = e
                if num == MAX_ATTEMPTS:
                    raise exc
                else:
                    num += 1
                print("Test failed, trying again (attempt {}/{})".format(num, MAX_ATTEMPTS))
                time.sleep(3)
            else:
                break

    def setUp(self):
        self.addCleanup(self.cleanupCalculations)
        os.chdir(base_cwd)
        call_command('init_static_obj')
        self.username = "Selenium"
        self.password = "test1234"

        u = User.objects.create_user(username=self.username, password=self.password)
        u.save()
        self.login(self.username, self.password)
        self.profile = Profile.objects.get(user__username=self.username)
        time.sleep(0.1)#Reduces glitches (I think?)

        self.name_patcher = mock.patch.dict(os.environ, {"TEST_NAME": self.full_test_name})
        self.name_patcher.start()


    def cleanupCalculations(self):
        for c in Calculation.objects.all():
            res = AbortableAsyncResult(c.task_id)
            res.abort()

    def login(self, username, password):
        self.lget('/accounts/login/')

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "id_username"))
        )
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "id_password"))
        )

        username_f = self.driver.find_element_by_id('id_username')
        password_f = self.driver.find_element_by_id('id_password')
        submit = self.driver.find_element_by_css_selector('input.control')
        username_f.send_keys(username)
        password_f.send_keys(password)
        submit.send_keys(Keys.RETURN)

        self.lget("/projects")
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "projects_list"))
        )

    def logout(self):
        self.driver.get('{}/accounts/logout/?next=/'.format(self.live_server_url))

    def lget(self, url):
        self.driver.get('{}{}'.format(self.live_server_url, url))

        # Try to wait until everything is loaded
        # This hopefully reduces the overall flakiness of Selenium integration tests
        for i in range(10):
            try:
                self.wait_for_ajax()
            except selenium.common.exceptions.JavascriptException:
                # JQuery not loaded
                time.sleep(0.1)
            else:
                break

    def calc_input_params(self, params):
        self.wait_for_ajax()

        if 'mol_name' in params.keys():
            element = WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located((By.NAME, "calc_mol_name"))
            )
            name_input = self.driver.find_element_by_name('calc_mol_name')
            name_input.clear()
            name_input.send_keys(params['mol_name'])

        if 'name' in params.keys():
            element = WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located((By.NAME, "calc_name"))
            )
            name_input = self.driver.find_element_by_name('calc_name')
            name_input.clear()
            name_input.send_keys(params['name'])

        element = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.NAME, "calc_solvent"))
        )

        element = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.NAME, "calc_project"))
        )

        try:
            upload_input = self.driver.find_element_by_name('file_structure')
        except selenium.common.exceptions.NoSuchElementException:
            pass

        if 'solvent' in params.keys():
            solvent_input = self.driver.find_element_by_name('calc_solvent')
            solvent_input.send_keys(params['solvent'])

        if 'charge' in params.keys():
            charge_input = self.driver.find_element_by_name('calc_charge')
            charge_input.clear()
            charge_input.send_keys(params['charge'])

        if 'multiplicity' in params.keys():
            mult_input = self.driver.find_element_by_name('calc_multiplicity')
            mult_input.clear()
            mult_input.send_keys(params['multiplicity'])

        if 'software' in params.keys():
            select = self.driver.find_element_by_id("calc_software")
            self.driver.execute_script("showDropdown = function (element) {var event; event = document.createEvent('MouseEvents'); event.initMouseEvent('mousedown', true, true, window); element.dispatchEvent(event); }; showDropdown(arguments[0]);",select)
            time.sleep(0.1)
            select.find_element_by_xpath("option[text()='{}']".format(params['software'])).click()

            self.wait_for_ajax()

        if 'type' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_type']/option[text()='{}']".format(params['type'])).click()

        if 'project' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_project']/option[text()='{}']".format(params['project'])).click()

        if 'solvation_method' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_solvation_model']/option[text()='{}']".format(params['solvation_method'])).click()

        if 'solvation_radii' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_solvation_radii']/option[text()='{}']".format(params['solvation_radii'])).click()

        if 'new_project_name' in params.keys():
            new_project_input = self.driver.find_element_by_name('new_project_name')
            new_project_input.send_keys(params['new_project_name'])

        if 'in_file' in params.keys():
            upload_input.send_keys("{}/tests/{}".format(dir_path, params['in_file']))

        if 'in_files' in params.keys():
            for f in params['in_files']:
                upload_input.send_keys("{}/tests/{}".format(dir_path, f))
            if 'combine' in params.keys() and params['combine'] == True:
                combine_box = self.driver.find_element_by_id("calc_combine_files");
                combine_box.click()

        if 'aux_file' in params.keys():
            aux_upload = self.driver.find_element_by_name('aux_file_structure')
            aux_upload.send_keys("{}/tests/{}".format(dir_path, params['aux_file']))

        if 'aux_structure' in params.keys():
            aux_mol, aux_e, aux_s = params['aux_structure']
            mol_select = self.driver.find_element_by_id("aux_mol")
            mol_select.find_element_by_xpath("option[text()='{}']".format(aux_mol)).click()

            self.wait_for_ajax()

            for i in range(2):
                try:
                    e_select = self.driver.find_element_by_id("aux_ensemble")
                    e_select.find_element_by_xpath("option[text()='{}']".format(aux_e)).click()
                except selenium.common.exceptions.NoSuchElementException:
                    time.sleep(1)
                else:
                    break

            self.wait_for_ajax()
            for i in range(2):
                try:
                    s_select = self.driver.find_element_by_id("aux_struct")
                    s_select.find_element_by_xpath("option[text()='{}']".format(aux_s)).click()
                except selenium.common.exceptions.NoSuchElementException:
                    time.sleep(1)
                else:
                    break

        if 'constraints' in params.keys():
            assert params['type'] in ['Constrained Optimisation', 'Constrained Conformational Search']

            def handle_constraint(constraint, ind):
                c_mode = constraint[0]
                select = self.driver.find_element_by_id("constraint_mode_{}".format(ind))
                self.driver.execute_script("showDropdown = function (element) {var event; event = document.createEvent('MouseEvents'); event.initMouseEvent('mousedown', true, true, window); element.dispatchEvent(event); }; showDropdown(arguments[0]);",select)
                time.sleep(0.1)
                select.find_element_by_xpath("option[text()='{}']".format(c_mode)).click()

                c_type = constraint[1]
                select = self.driver.find_element_by_id("constraint_type_{}".format(ind))
                self.driver.execute_script("showDropdown = function (element) {var event; event = document.createEvent('MouseEvents'); event.initMouseEvent('mousedown', true, true, window); element.dispatchEvent(event); }; showDropdown(arguments[0]);",select)
                time.sleep(0.1)
                select.find_element_by_xpath("option[text()='{}']".format(c_type)).click()

                atoms = constraint[2]
                self.driver.find_element_by_id("calc_constraint_{}_1".format(ind)).send_keys(str(atoms[0]))
                self.driver.find_element_by_id("calc_constraint_{}_2".format(ind)).send_keys(str(atoms[1]))
                if c_type == 'Angle':
                    self.driver.find_element_by_id("calc_constraint_{}_3".format(ind)).send_keys(str(atoms[2]))
                elif c_type == 'Dihedral':
                    self.driver.find_element_by_id("calc_constraint_{}_3".format(ind)).send_keys(str(atoms[2]))
                    self.driver.find_element_by_id("calc_constraint_{}_4".format(ind)).send_keys(str(atoms[3]))
                if c_mode == "Scan":
                    scan = constraint[3]
                    if not 'software' in params.keys() or params['software'] != "Gaussian":
                        self.driver.find_element_by_id("calc_scan_{}_1".format(ind)).send_keys(str(scan[0]))
                    self.driver.find_element_by_id("calc_scan_{}_2".format(ind)).send_keys(str(scan[1]))
                    self.driver.find_element_by_id("calc_scan_{}_3".format(ind)).send_keys(str(scan[2]))


            constr = params['constraints']
            handle_constraint(constr[0], 1)
            if len(constr) > 1:
                ind = 2
                for c in params['constraints'][1:]:
                    self.driver.find_element_by_id("add_constraint_btn").click()
                    time.sleep(0.1)
                    handle_constraint(c, ind)
                    time.sleep(0.1)
                    ind += 1


        if 'theory' in params.keys():
            select = self.driver.find_element_by_id("calc_theory_level")
            self.driver.execute_script("showDropdown = function (element) {var event; event = document.createEvent('MouseEvents'); event.initMouseEvent('mousedown', true, true, window); element.dispatchEvent(event); }; showDropdown(arguments[0]);",select)
            time.sleep(0.1)
            self.driver.find_element_by_xpath("//*[@id='calc_theory_level']/option[text()='{}']".format(params['theory'])).click()

        if 'method' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_method']/option[text()='{}']".format(params['method'])).click()

        if 'functional' in params.keys():
            element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "calc_functional"))
            )
            func = self.driver.find_element_by_id("calc_functional")
            func.clear()
            func.send_keys(params['functional'])

        if 'basis_set' in params.keys():
            bs = self.driver.find_element_by_id("calc_basis_set")
            bs.clear()
            bs.send_keys(params['basis_set'])

        if 'specifications' in params.keys():
            self.driver.find_element_by_css_selector("summary").click()
            specs = self.driver.find_element_by_id("calc_specifications")
            specs.clear()
            specs.send_keys(params['specifications'])
            #self.driver.find_element_by_css_selector("summary").click()

        if 'filter' in params.keys():
            assert 'filter_value' in params.keys()

            filter_select = self.driver.find_element_by_id("calc_filter")
            filter_select.find_element_by_xpath("option[text()='{}']".format(params['filter'])).click()

            filter_value = self.driver.find_element_by_id("filter_value_input")
            filter_value.send_keys(params['filter_value'])

        if 'resource' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_resource']/option[text()='{}']".format(params['resource'])).click()

    def calc_launch(self):
        submit = self.driver.find_element_by_id('submit_button')
        submit.click()

    def get_confirmed_specifications(self):
        assert self.is_on_page_ensemble()
        cell = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.ID, "param_specifications_cell"))
        )

        return cell.text

    def get_number_calc_orders(self):
        return len(self.get_calc_orders())

    def get_status_calc_orders(self):
        orders = self.get_calc_orders()
        statuses = []
        for o in orders:
            head = o.find_element_by_css_selector("article > div")
            color = head.get_attribute("class")
            if color.find("has-background-warning") != -1:
                statuses.append(1)
            elif color.find("has-background-success") != -1:
                statuses.append(2)
            elif color.find("has-background-danger") != -1:
                statuses.append(3)
            else:
                statuses.append(0)
        return statuses

    def get_number_unseen_calcs(self):
        try:
            badge = self.driver.find_element_by_id("unseen_calculations_badge")
        except selenium.common.exceptions.NoSuchElementException:
            return 0
        if badge is None or badge.text.strip() == '':
            return 0
        return int(badge.text)

    def get_number_unseen_calcs_manually(self):
        assert self.is_on_page_calculations()

        orders = self.get_calc_orders()
        num = 0
        for o in orders:
            if o.get_attribute("class").find("new") != -1:
                num += 1
        return num

    def get_number_calc_methods(self):
        assert self.is_on_page_ensemble()

        tabs_list = self.driver.find_element_by_css_selector("#tabs")
        tabs = tabs_list.find_elements_by_css_selector("li")
        return len(tabs)

    def wait_for_ajax(self):
        wait = WebDriverWait(self.driver, 5)

        wait.until(lambda driver: driver.execute_script('return jQuery.active') == 0)
        wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')

    def get_nmr_shifts(self):
        assert self.is_on_page_nmr_analysis()
        self.wait_for_ajax()

        tbody = self.driver.find_element_by_id("shifts_body")
        lines = tbody.find_elements_by_css_selector("tr")
        shifts = [line.find_element_by_css_selector("td:nth-child(3)").text for line in lines]
        return shifts

    def click_calc_method(self, num):
        assert self.is_on_page_ensemble()

        self.wait_for_ajax()
        tabs_list = self.driver.find_element_by_css_selector("#tabs")
        tabs = tabs_list.find_elements_by_css_selector("li")
        tabs[num-1].click()
        self.wait_for_ajax()

    def click_calc_method_not_geom(self):
        assert self.is_on_page_ensemble()

        self.wait_for_ajax()
        tabs_list = self.driver.find_element_by_css_selector("#tabs")
        tabs = tabs_list.find_elements_by_css_selector("li")

        not_geom = None
        for t in tabs:
            if '(GEOMETRY)' not in t.text:
                if not_geom is None:
                    not_geom = t
                else:
                    raise Exception("More than one tab of properties")

        not_geom.click()
        self.wait_for_ajax()

    def click_calc_method_geom(self):
        assert self.is_on_page_ensemble()

        self.wait_for_ajax()
        tabs_list = self.driver.find_element_by_css_selector("#tabs")
        tabs = tabs_list.find_elements_by_css_selector("li")

        not_geom = None
        for t in tabs:
            if '(GEOMETRY)' in t.text:
                t.click()
                break
        else:
            raise Exception("No tab for the geometry")

        self.wait_for_ajax()

    def click_advanced_nmr_analysis(self):
        assert self.is_on_page_ensemble()

        button = self.driver.find_element_by_id("advanced_nmr_analysis_button")
        button.click()

    def click_get_shifts(self):
        assert self.is_on_page_nmr_analysis()

        button = self.driver.find_element_by_id("get_shifts_button")
        button.click()

    def get_conformers(self):
        assert self.is_on_page_ensemble()
        self.wait_for_ajax()

        conf_table = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.ID, "conf_table"))
        )
        conformers = conf_table.find_elements_by_css_selector("tr")
        return conformers

    def get_number_conformers(self):
        conformers = self.get_conformers()
        return len(conformers)

    def get_conformer_data(self):
        conformers = self.get_conformers()
        conf_data = []

        for line in conformers:
            data = line.find_elements_by_css_selector("th")
            conf_data.append([i.text for i in data])

        return conf_data

    def select_conformer(self, num):
        conformers = self.get_conformers()
        conformers[num-1].click()

    def select_conformers(self, nums):
        conformers = self.get_conformers()
        first_conf = nums.pop(0)-1

        conformers[first_conf].click()

        for n in nums:
            ActionChains(self.driver).key_down(Keys.CONTROL).click(conformers[n-1]).key_up(Keys.CONTROL).perform()


    def get_split_url(self):
        return self.driver.current_url.split('/')[3:]

    def get_group_panel(self):
        return self.driver.find_element_by_css_selector(".navbar-start > div")

    def group_panel_present(self):
        try:
            a = self.get_group_panel()
        except selenium.common.exceptions.NoSuchElementException:
            return False
        else:
            return True

    def group_num_members(self):
        assert self.group_panel_present()

        panel = self.get_group_panel()
        users = panel.find_elements_by_css_selector(".navbar-dropdown > .navbar-item")

        assert len(users) > 0

        return len(users)

    def group_click_member(self, name):
        assert self.group_panel_present()

        panel = self.get_group_panel()
        panel.click()
        users = panel.find_elements_by_css_selector(".navbar-dropdown > .navbar-item")
        for u in users:
            username = u.text
            if username == name:
                u.click()
                return
        raise Exception("No such user")

    def add_cluster(self):
        assert self.is_on_page_profile()

        address = self.driver.find_element_by_name("cluster_address")
        username = self.driver.find_element_by_name("cluster_username")
        if docker:
            address.send_keys("slurm")
            username.send_keys("slurm")
        else:
            address.send_keys("localhost")
            username.send_keys("calcus")


        pal = self.driver.find_element_by_name("cluster_cores")
        pal.clear()
        pal.send_keys("8")

        memory = self.driver.find_element_by_name("cluster_memory")
        memory.clear()
        memory.send_keys("6000")

        password = self.driver.find_element_by_name("cluster_password")
        password.clear()
        password.send_keys("Selenium")

        self.driver.find_element_by_id("add_access_button").click()

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "public_key_area"))
        )

        for i in range(5):
            public_key = self.driver.find_element_by_id("public_key_area").text
            if public_key.strip() != "":
                break
            time.sleep(1)

        if docker:
            child = pexpect.spawn('ssh slurm@slurm')
            #child.logfile = open("/calcus/pexpect.log", 'wb')
            choice = child.expect(["(yes/no)", "password"])
            if choice == 0:
                child.sendline('yes')
                child.expect("password")
                child.sendline('clustertest')
            elif choice == 1:
                child.sendline('clustertest')

            child.expect("\$")
            child.sendline("mkdir -p .ssh/".format(public_key))
            child.expect("\$")
            child.sendline("echo '{}' > .ssh/authorized_keys".format(public_key))
            child.expect("\$")
            child.sendline("chmod 700 .ssh/authorized_keys")
            child.expect("\$")
            child.sendline("chown slurm:slurm .ssh/authorized_keys")
            child.expect("\$")
            child.sendline("exit")
        else:
            child = pexpect.spawn('su - calcus')
            child.expect ('Password:')
            child.sendline('clustertest')
            child.expect('\$')
            child.sendline("echo '{}' > /home/calcus/.ssh/authorized_keys".format(public_key))
            time.sleep(0.1)

    def connect_cluster(self):
        assert self.is_on_page_access()

        status = self.driver.find_element_by_id("status_box")

        if 'has-background-success' in status.get_attribute("class"):#Already connected
            return

        password = self.driver.find_element_by_id("ssh_password")
        password.clear()
        password.send_keys("Selenium")

        test_access = self.driver.find_element_by_id("connect_button")
        test_access.click()

        for i in range(10):
            time.sleep(1)
            try:
                msg = self.driver.find_element_by_id("test_msg").text
                if msg == "Connected" or msg == "Already connected":
                    return
            except:
                pass

        raise Exception("Could not connect to the cluster")

    def disconnect_cluster(self):
        assert self.is_on_page_access()

        disconnect = self.driver.find_element_by_id("disconnect_button")
        disconnect.click()

    def select_cluster(self, num):
        assert self.is_on_page_profile()

        clusters = self.driver.find_elements_by_css_selector("#owned_accesses > center > table > tbody > tr")
        cluster = clusters[num-1]
        cluster.find_element_by_css_selector("th > a.button").click()

    def is_user(self, username):
        try:
            u = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            return False
        else:
            return True

    def is_user_project(self, username, project_name):
        try:
            u = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            return False
        else:
            try:
                p = Project.objects.get(name=project_name.replace('%20', ' '), author=u)
            except Project.DoesNotExist:
                return False
            else:
                return True

    def is_molecule_id(self, mol_id):
        try:
            mol = Molecule.objects.get(pk=mol_id)
        except Molecule.DoesNotExist:
            return False
        else:
            return True

    def is_ensemble_id(self, e_id):
        try:
            e = Ensemble.objects.get(pk=e_id)
        except Ensemble.DoesNotExist:
            return False
        else:
            return True

    def is_on_page_folders(self):
        for i in range(3):
            url = self.get_split_url()
            if url[0] == 'projects' and self.is_user(url[1]) and self.is_user_project(url[1], url[2]) and url[3] == "folders":
                return True
            time.sleep(1)

        return False

    def is_on_page_order_details(self):
        for i in range(3):
            url = self.get_split_url()
            if url[0] == 'calculationorder' and url[1] != '':
                return True
            time.sleep(1)

        return False

    def is_on_page_projects(self):
        for i in range(3):
            url = self.get_split_url()
            if (url[0] == 'projects' or url[0] == 'home') and (url[1] == '' or self.is_user(url[1])):
                return True
            time.sleep(1)

        return False

    def is_on_page_user_project(self):
        for i in range(3):
            url = self.get_split_url()
            if url[0] == 'projects' and self.is_user(url[1]) and self.is_user_project(url[1], url[2]):
                return True
            time.sleep(1)

        return False

    def is_on_page_calculations(self):
        for i in range(3):
            url = self.get_split_url()
            if url[0] == 'calculations' and url[1] == '':
                return True
            time.sleep(1)

        return False

    def is_on_page_calculation(self):
        for i in range(3):
            url = self.get_split_url()
            if url[0] == 'calculation' and url[1] != '':
                return True
            time.sleep(1)

        return False

    def is_on_page_profile(self):
        for i in range(3):
            url = self.get_split_url()
            if url[0] == 'profile' and url[1] == '':
                return True
            time.sleep(1)

        return False

    def is_on_page_access(self):
        for i in range(3):
            url = self.get_split_url()
            if url[0] == 'manage_access' and url[1] != '':
                return True
            time.sleep(1)

        return False


    def is_on_page_managePI(self):
        for i in range(3):
            url = self.get_split_url()
            if url[0] == 'manage_pi_requests' and url[1] == '':
                return True
            time.sleep(1)

        return False

    def is_on_page_molecule(self):
        for i in range(3):
            url = self.get_split_url()
            try:
                mol_id = int(url[1])
            except ValueError:
                pass
            else:
                if url[0] == 'molecule' and self.is_molecule_id(mol_id):
                    return True
            time.sleep(1)

        return False

    def is_on_page_ensemble(self):
        for i in range(3):
            url = self.driver.current_url.split('/')[3:]
            try:
                e_id = int(url[1])
            except ValueError:
                pass
            else:
                if url[0] == 'ensemble' and self.is_ensemble_id(e_id):
                    return True
            time.sleep(1)

        return False

    def is_on_page_nmr_analysis(self):
        for i in range(3):
            url = self.get_split_url()
            if url[0] == 'nmr_analysis' and url[1] != '':
                return True
            time.sleep(1)

        return False

    def get_projects(self):
        assert self.is_on_page_projects()

        project_div = self.driver.find_element_by_id("projects_list")
        projects = project_div.find_elements_by_css_selector(".box")
        return projects

    def get_number_projects(self):
        projects = self.get_projects()

        num = len(projects)
        return num

    def get_number_calcs_in_project(self, name):
        projects = self.get_projects()
        proj = None
        for _proj in projects:
            proj_name = _proj.find_element_by_css_selector("a > strong > p").text
            if proj_name == name:
                proj = _proj
                break
        else:
            raise Exception("Project not found")

        sline = proj.find_element_by_css_selector("a > p").text.split()
        return int(sline[0])

    def get_number_calcs_in_molecule(self, name):
        molecules = self.get_molecules()
        mol = None
        for _mol in molecules:
            mol_name = _mol.find_element_by_css_selector("a > strong > p").text
            if mol_name == name:
                mol = _mol
                break
        else:
            raise Exception("Molecule not found")

        sline = mol.find_element_by_css_selector("a > p").text.split()
        return int(sline[0])

    def rename_project(self, proj, name):
        rename_icon = proj.find_element_by_class_name("fa-edit")
        rename_icon.click()
        text_box = proj.find_element_by_css_selector("a > strong > p")
        text_box.clear()
        text_box.send_keys(name)
        text_box.send_keys(Keys.RETURN)
        self.wait_for_ajax()

    def rename_project2(self, proj, name):
        rename_icon = proj.find_element_by_class_name("fa-edit")
        rename_icon.click()

        text_box = proj.find_element_by_css_selector("a > strong > p")
        text_box.clear()
        text_box.send_keys(name)

        done_icon = proj.find_element_by_class_name("fa-check")
        done_icon.click()
        self.wait_for_ajax()

    def get_name_projects(self):
        projects = self.get_projects()
        names = [proj.find_element_by_css_selector("strong > p").text for proj in projects]
        return names

    def create_empty_project(self):
        assert self.is_on_page_projects()
        num_before = self.get_number_projects()

        create_proj_box = self.driver.find_element_by_css_selector("#content_container > div > center > a")
        create_proj_box.click()
        for i in range(5):
            num_projects = self.get_number_projects()
            if num_projects == num_before + 1:
                return
            time.sleep(1)
        raise Exception("Could not create empty project")

    def create_molecule_in_project(self):
        assert self.is_on_page_user_project()
        link = self.driver.find_element_by_css_selector("#molecule_in_project")
        link.click()

    def click_project(self, name):
        projects = self.get_projects()

        for proj in projects:
            p_name = proj.find_element_by_css_selector("strong > p").text
            if p_name == name:
                link = proj.find_element_by_css_selector("div > a")
                link.click()
                return
        else:
            raise Exception("Project not found")

    def get_number_molecules(self):
        assert self.is_on_page_user_project()

        molecules = self.get_molecules()
        num = len(molecules)

        return num

    def click_molecule(self, name):
        assert self.is_on_page_user_project()

        molecules = self.get_molecules()
        for mol in molecules:
            mol_name = mol.find_element_by_css_selector("a > strong > p").text
            if mol_name == name:
                #link = mol.find_element_by_css_selector("a")
                #link.click()
                mol.click()
                return
        else:
            raise Exception("Could not click on molecule")

    def get_number_ensembles(self):
        assert self.is_on_page_molecule()

        ensembles = self.get_ensemble_rows()
        num = len(ensembles)
        return num

    def click_ensemble(self, name):
        assert self.is_on_page_molecule()

        table_body = self.driver.find_element_by_css_selector(".table > tbody")
        ensembles = table_body.find_elements_by_css_selector("tr")

        for e in ensembles:
            e_link = e.find_element_by_css_selector("td:nth-child(2) > a")
            e_name = e_link.text
            if e_name == name:
                e_link.click()
                return
        else:
            raise Exception("Ensemble not found")

    def get_calc_orders(self):
        assert self.is_on_page_calculations()
        self.wait_for_ajax()

        try:
            calculations_div = WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#calculations_list"))
            )
        except selenium.common.exceptions.TimeoutException:
            return []

        calculations = calculations_div.find_elements_by_css_selector("article")
        return calculations

    def click_latest_calc(self):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0

        calculations = self.get_calc_orders()
        calculations[0].click()
        self.wait_for_ajax()

    def see_latest_calc(self):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0

        calculations = self.get_calc_orders()
        calc = calculations[0]
        eye = calc.find_element_by_class_name("fa-eye")
        eye.click()
        self.wait_for_ajax()

    def details_latest_order(self):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0

        calculations = self.get_calc_orders()

        link = calculations[0].find_element_by_class_name("fa-list")
        link.click()

    def get_error_messages(self):
        assert self.is_on_page_order_details()
        assert self.get_number_calc_in_order() > 0

        calcs = self.get_calcs_in_order()

        error_messages = [i.find_element_by_css_selector("th:nth-child(2)").text for i in calcs]
        return error_messages

    def details_first_calc(self):
        assert self.is_on_page_order_details()

        calcs = self.driver.find_elements_by_css_selector("tbody > tr")
        first_calc = calcs[0]
        buttons = first_calc.find_elements_by_css_selector(".button")
        details = buttons[0]
        assert details.text != "Kill"
        details.click()

    def get_calcs_in_order(self):
        assert self.is_on_page_order_details()
        calcs = self.driver.find_elements_by_css_selector("tbody > tr")
        return calcs

    def get_number_calc_in_order(self):
        calcs = self.get_calcs_in_order()
        return len(calcs)

    def cancel_all_calc(self):
        calcs = self.get_calcs_in_order()
        for c in calcs:
            buttons = c.find_elements_by_css_selector(".button")
            for b in buttons:
                if b.text == "Kill":
                    b.click()

                    for i in range(3):
                        c = b.get_attribute("class")
                        if c.find("has-background-success") != -1:
                            break
                        time.sleep(1)

                    assert b.get_attribute("class").find("has-background-success") != -1

    def refetch_all_calc(self):
        assert self.is_on_page_order_details()

        calcs = self.driver.find_elements_by_css_selector("tbody > tr")
        for c in calcs:
            buttons = c.find_elements_by_css_selector(".button")
            for b in buttons:
                if b.text == "Refetch":
                    b.click()

                    for i in range(3):
                        c = b.get_attribute("class")
                        if c.find("has-background-success") != -1:
                            break
                        time.sleep(1)

                    assert b.get_attribute("class").find("has-background-success") != -1

    def relaunch_all_calc(self):
        assert self.is_on_page_order_details()

        calcs = self.driver.find_elements_by_css_selector("tbody > tr")
        for c in calcs:
            buttons = c.find_elements_by_css_selector(".button")
            for b in buttons:
                if b.text == "Relaunch":
                    b.click()

                    for i in range(3):
                        c = b.get_attribute("class")
                        if c.find("has-background-success") != -1:
                            break
                        time.sleep(1)

                    assert b.get_attribute("class").find("has-background-success") != -1

        self.wait_for_ajax()

    def get_calculation_statuses(self):
        assert self.is_on_page_order_details()
        calcs = self.driver.find_elements_by_css_selector("tbody > tr")

        statuses = []
        for c in calcs:
            status = c.find_element_by_css_selector("th:nth-child(2)").text
            statuses.append(status)

        return statuses

    def apply_PI(self, group_name):
        assert self.is_on_page_profile()
        self.wait_for_ajax()
        group_name = self.driver.find_element_by_name('group_name')
        submit = self.driver.find_element_by_css_selector("button.button:nth-child(3)")
        group_name.send_keys("Test group")
        submit.send_keys(Keys.RETURN)

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "PI_application_message"))
        )


    def accept_PI_request(self):
        assert self.is_on_page_managePI()
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "table"))
        )

        table = self.driver.find_element_by_class_name('table')

        self.assertTrue(table.text.find("Accept") != -1)
        self.assertTrue(table.text.find("Deny") != -1)

        accept_button = self.driver.find_element_by_css_selector('#requests_table > table > tbody > tr > td:nth-child(1) > button')
        accept_button.send_keys(Keys.RETURN)

    def wait_latest_calc_done(self, timeout):
        assert self.is_on_page_calculations()
        self.wait_for_ajax()
        assert self.get_number_calc_orders() > 0

        for i in range(0, timeout, 2):
            calculations = self.get_calc_orders()

            header = calculations[0].find_element_by_class_name("message-header")
            if "has-background-success" in header.get_attribute("class") or "has-background-danger" in header.get_attribute("class"):
                return
            time.sleep(2)
            self.driver.refresh()
        raise Exception("Calculation did not finish")

    def wait_all_calc_done(self, timeout):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0

        for i in range(0, timeout, 2):
            calculations = self.get_calc_orders()

            for calc in calculations:
                header = calculations[0].find_element_by_class_name("message-header")
                if not "has-background-success" in header.get_attribute("class") and not "has-background-danger" in header.get_attribute("class"):
                    break
            else:
                return
            time.sleep(2)
            self.driver.refresh()
        raise Exception("Calculation did not finish")

    def wait_all_calc_done(self, timeout):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0


        def calc_done():
            for c in calculations:
                header = c.find_element_by_class_name("message-header")
                if not "has-background-success" in header.get_attribute("class") and not "has-background-danger" in header.get_attribute("class"):
                    return False
            else:
                return True

        for i in range(0, timeout, 2):
            calculations = self.get_calc_orders()
            if calc_done():
                return
            time.sleep(2)
            self.driver.refresh()
        raise Exception("Calculation did not finish")


    def wait_latest_calc_running(self, timeout):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0

        for i in range(timeout):
            calculations = self.get_calc_orders()

            header = calculations[0].find_element_by_class_name("message-header")
            if "has-background-warning" in header.get_attribute("class"):
                    return
            time.sleep(1)
            self.driver.refresh()
        raise Exception("Calculation did not run")

    def wait_latest_calc_error(self, timeout):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0

        for i in range(timeout):
            calculations = self.get_calc_orders()

            header = calculations[0].find_element_by_class_name("message-header")
            if "has-background-danger" in header.get_attribute("class"):
                    return
            time.sleep(1)
            self.driver.refresh()
        raise Exception("Calculation did not produce an error")

    def latest_calc_successful(self):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0


        calculations_container = self.driver.find_element_by_id("calculations_list")
        calculations = calculations_container.find_elements_by_css_selector("article")
        header = calculations[0].find_element_by_class_name("message-header")
        successful = "has-background-success" in header.get_attribute("class")

        if not successful:
            latest_order = CalculationOrder.objects.latest('id')
            print("Error messages of calculations in order {}".format(latest_order.id))
            for c in latest_order.calculation_set.all():
                print(c.error_message)
        return successful

    def all_calc_successful(self):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0

        calculations_container = self.driver.find_element_by_id("calculations_list")
        calculations = calculations_container.find_elements_by_css_selector("article")
        for c in calculations:
            header = c.find_element_by_class_name("message-header")
            successful = "has-background-success" in header.get_attribute("class")

            if not successful:
                latest_order = CalculationOrder.objects.latest('id')
                print("Error messages of calculations in order {}".format(latest_order.id))
                for c in latest_order.calculation_set.all():
                    print(c.error_message)
                return False
        return True

    def add_user_to_group(self, username):
        assert self.is_on_page_profile()

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "code"))
        )
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "user_to_add"))
        )


        p = Profile.objects.get(user__username=username)
        code = p.code
        field_username = self.driver.find_element_by_id("user_to_add")
        field_code = self.driver.find_element_by_id("code")
        button_submit = self.driver.find_element_by_css_selector("button.button:nth-child(4)")
        field_username.send_keys(username)
        field_code.send_keys(code)
        button_submit.send_keys(Keys.RETURN)

    def launch_ensemble_next_step(self):
        assert self.is_on_page_ensemble()
        button = WebDriverWait(self.driver, 1).until(
            EC.presence_of_element_located((By.ID, "next_step_ensemble"))
        )
        button.send_keys(Keys.RETURN)

    def launch_structure_next_step(self):
        assert self.is_on_page_ensemble()

        button = WebDriverWait(self.driver, 1).until(
            EC.presence_of_element_located((By.ID, "next_step_structure"))
        )
        table = WebDriverWait(self.driver, 1).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#conf_table > tr"))
        )

        button.send_keys(Keys.RETURN)

    def launch_frame_next_step(self):
        assert self.is_on_page_calculation()

        for i in range(3):
            try:
                button = self.driver.find_element_by_id("launch_from_frame")
            except selenium.common.exceptions.NoSuchElementException:
                pass
            else:
                break
            time.sleep(0.1)

            self.driver.get(self.driver.current_url)
            self.wait_for_ajax()
        else:
            raise Exception("Could not get the button to launch calculation from frame")

        button.send_keys(Keys.RETURN)

    def delete_project(self, name):
        assert self.is_on_page_projects()
        main_window_handle = None
        while not main_window_handle:
            main_window_handle = self.driver.current_window_handle

        project_div = self.driver.find_element_by_id("projects_list")
        projects = project_div.find_elements_by_css_selector(".box")

        for proj in projects:
            p_name = proj.find_element_by_css_selector("strong > p").text

            if p_name == name:
                trash = proj.find_element_by_css_selector("a > i.fa-trash-alt")
                trash.click()

                alert = Alert(self.driver)
                alert.accept()
                return

    def get_molecules(self):
        assert self.is_on_page_user_project()
        molecules = self.driver.find_elements_by_css_selector(".grid > .box")
        return molecules

    def get_name_molecules(self):
        molecules = self.get_molecules()
        names = []
        for mol in molecules:
            try:
                names.append(mol.find_element_by_css_selector("strong > p").text)
            except selenium.common.exceptions.NoSuchElementException:
                pass

        return names

    def rename_molecule(self, mol, name):
        rename_icon = mol.find_element_by_class_name("fa-edit")
        rename_icon.click()
        text_box = mol.find_element_by_css_selector("a > strong > p")
        text_box.clear()
        text_box.send_keys(name)
        text_box.send_keys(Keys.RETURN)
        self.wait_for_ajax()

    def rename_molecule2(self, mol, name):
        rename_icon = mol.find_element_by_class_name("fa-edit")
        rename_icon.click()

        text_box = mol.find_element_by_css_selector("a > strong > p")
        text_box.clear()
        text_box.send_keys(name)

        done_icon = mol.find_element_by_class_name("fa-check")
        done_icon.click()
        self.wait_for_ajax()

    def delete_molecule(self, name):
        assert self.is_on_page_user_project()
        main_window_handle = None
        while not main_window_handle:
            main_window_handle = self.driver.current_window_handle

        molecules = self.get_molecules()

        for mol in molecules:
            mol_name = mol.find_element_by_css_selector("strong > p").text
            if mol_name == name:
                trash = mol.find_element_by_css_selector("i.fa-trash-alt")
                trash.click()

                alert = Alert(self.driver)
                alert.accept()
                return
        else:
            raise Exception("Could not delete molecule")

    def get_ensemble_rows(self):
        assert self.is_on_page_molecule()
        table_body = self.driver.find_element_by_css_selector("#ensemble_table_body")
        ensemble_rows = table_body.find_elements_by_css_selector("tr")
        return ensemble_rows

    def get_name_ensembles(self):
        ensemble_rows = self.get_ensemble_rows()
        names = [e.find_element_by_css_selector("td:nth-child(2) > a").text for e in ensemble_rows]

        return names

    def rename_ensemble(self, e, name):
        rename_icon = e.find_element_by_class_name("fa-edit")
        rename_icon.click()

        text_box = e.find_element_by_css_selector("tr > td > a")
        text_box.clear()
        text_box.send_keys(name)

        text_box.send_keys(Keys.RETURN)
        self.wait_for_ajax()

    def rename_ensemble2(self, e, name):
        rename_icon = e.find_element_by_class_name("fa-edit")
        rename_icon.click()

        text_box = e.find_element_by_css_selector("tr > td > a")
        text_box.clear()
        text_box.send_keys(name)

        done_icon = e.find_element_by_class_name("fa-check")
        done_icon.click()
        self.wait_for_ajax()

    def delete_ensemble(self, name):
        assert self.is_on_page_molecule()
        main_window_handle = None
        while not main_window_handle:
            main_window_handle = self.driver.current_window_handle

        ensembles_rows = self.get_ensemble_rows()

        for e in ensembles_rows:
            e_name = e.find_element_by_css_selector("td:nth-child(2) > a").text
            if e_name == name:
                trash = e.find_element_by_css_selector("i.fa-trash-alt")
                trash.click()

                alert = Alert(self.driver)
                alert.accept()
                self.wait_for_ajax()
                return
        else:
            raise Exception("Could not delete ensemble")

    def flag_ensemble(self):
        assert self.is_on_page_ensemble()

        button = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.ID, "icon_flag"))
        )
        button.click()
        self.wait_for_ajax()

    def is_ensemble_flagged(self):
        assert self.is_on_page_ensemble()
        icon = self.driver.find_element_by_id("icon_flag")
        if icon.value_of_css_property("color") == "rgba(192, 192, 192, 1)":
            return True
        else:
            return False

    def setup_test_group(self):
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

    def is_loaded_frequencies(self):
        assert self.is_on_page_ensemble()

        self.wait_for_ajax()

        try:
            table = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "vib_table"))
            )
        except selenium.common.exceptions.TimeoutException:
            return False

        freqs = table.find_elements_by_css_selector("div.column")

        if len(freqs) > 0:
            return True
        return False

    def is_loaded_mo(self):
        assert self.is_on_page_ensemble()

        self.wait_for_ajax()

        try:
            mo_div = self.driver.find_element_by_id("mo_structure_details")
        except selenium.common.exceptions.NoSuchElementException:
            return False

        try:
            mo_viewer = mo_div.find_element_by_id("mo_viewer_div")
            mo_container = mo_div.find_element_by_id("mo_container")
        except selenium.common.exceptions.NoSuchElementException:
            return False

        return True

    def save_preset(self, name):
        main_window_handle = None
        while not main_window_handle:
            main_window_handle = self.driver.current_window_handle

        button = self.driver.find_element_by_css_selector("a.button:nth-child(4)")
        button.click()

        alert = Alert(self.driver)
        alert.send_keys(name)
        alert.accept()
        self.wait_for_ajax()

    def load_preset(self, name):
        self.select_preset(name)
        button = self.driver.find_element_by_css_selector("a.button:nth-child(3)")
        button.click()
        self.wait_for_ajax()

    def delete_preset(self, name):
        self.select_preset(name)
        button = self.driver.find_element_by_css_selector("a.button:nth-child(5)")
        button.click()
        self.wait_for_ajax()

    def set_project_preset(self):
        button = self.driver.find_element_by_css_selector("a.button:nth-child(7)")
        button.click()
        self.wait_for_ajax()

    def get_name_presets(self):
        select = self.driver.find_element_by_css_selector("#presets")
        presets = select.find_elements_by_css_selector("option")
        names = [p.text for p in presets]
        return names

    def select_preset(self, name):
        self.wait_for_ajax()
        element = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='presets']/option[text()='{}']".format(name)))
        )

        self.driver.find_element_by_xpath("//*[@id='presets']/option[text()='{}']".format(name)).click()

    def try_assert_number_unseen_calcs(self, num, timeout):
        for i in range(timeout):
            if self.get_number_unseen_calcs() == num:
                return True
            self.driver.refresh()
            time.sleep(1)
        return False

    def get_related_calculations_div(self):
        assert self.is_on_page_ensemble()
        fold_details = self.driver.find_element_by_css_selector("details")

        if fold_details.get_attribute("open") is None:
            fold = self.driver.find_element_by_css_selector("summary")
            fold.click()
            self.wait_for_ajax()

        return self.driver.find_element_by_id("related_calculations_div")

    def get_related_orders(self):
        related_calculations_div = self.get_related_calculations_div()

        orders_links = related_calculations_div.find_elements_by_css_selector("ul.tree > li > a")
        orders = [i.text for i in orders_links]
        return orders

    def get_related_calculations(self, order_id):
        related_calculations_div = self.get_related_calculations_div()

        trees = related_calculations_div.find_elements_by_css_selector("ul.tree > li")
        for t in trees:
            link = t.find_element_by_css_selector("li > a")
            t_id = int(link.text.split()[1])
            if t_id == order_id:
                tree = t
                break
        else:
            raise Exception("Order {} is not related to this ensemble!".format(order_id))

        calc_tree = tree.find_elements_by_css_selector("ul > li")

        calcs = [i.find_element_by_css_selector("a").text for i in calc_tree]
        return calcs

    def click_icon(self, proj_name, icon):
        projects = self.get_projects()
        for proj in projects:
            name = proj.find_element_by_css_selector("a > strong > p").text
            if name == proj_name:
                icon = proj.find_element_by_css_selector(".fa-{}".format(icon))
                icon.click()
                return
        else:
            raise Exception("No such project found")

    def click_icon_folder(self, proj_name):
        self.click_icon(proj_name, "folder")

    def click_icon_shield(self, proj_name):
        self.click_icon(proj_name, "user-shield")

    def create_empty_folder(self):
        assert self.is_on_page_folders()

        create_box = self.driver.find_element_by_id("create_folder_link")
        create_box.click()
        self.wait_for_ajax()

    def get_folders(self):
        assert self.is_on_page_folders()

        folder_list = self.driver.find_element_by_id("folder_list")
        return folder_list.find_elements_by_css_selector(".box")

    def get_folder_ensembles(self):
        assert self.is_on_page_folders()

        return self.driver.find_elements_by_css_selector(".grid > .box")

    def get_number_folders(self):
        folders = self.get_folders()
        return len(folders)

    def get_number_folder_ensembles(self):
        ensembles = self.get_folder_ensembles()
        return len(ensembles)

    def get_name_folders(self):
        folders = self.get_folders()
        names = [i.find_element_by_css_selector("a > strong > p").text for i in folders]
        return names

    def get_name_folder_ensembles(self):
        ensembles = self.get_folder_ensembles()
        names = []

        for e in ensembles:
            pars = e.find_elements_by_css_selector("a > strong > p")
            names.append(''.join([i.text for i in pars]))

        return names

    def get_folder(self, folder_name):
        folders = self.get_folders()
        for f in folders:
            name = f.find_element_by_css_selector("a > strong > p").text
            if name == folder_name:
                return f
        else:
            raise Exception("No such folder found")

    def get_folder_ensemble(self, ensemble_name):
        ensembles = self.get_folder_ensembles()
        for e in ensembles:
            pars = e.find_elements_by_css_selector("a > strong > p")
            name = ''.join([i.text for i in pars])
            if name == ensemble_name:
                return e
        else:
            raise Exception("No such ensemble found")

    def drag_folder_to_folder(self, folder_name1, folder_name2):
        folder1 = self.get_folder(folder_name1)
        folder2 = self.get_folder(folder_name2)

        ActionChains(self.driver).drag_and_drop(folder1, folder2).perform()

    def drag_ensemble_to_folder(self, ensemble_name, folder_name):
        folder = self.get_folder(folder_name)
        ensemble = self.get_folder_ensemble(ensemble_name)

        ActionChains(self.driver).drag_and_drop(ensemble, folder).perform()

    def click_folder(self, folder_name):
        folder = self.get_folder(folder_name)
        folder.click()

    def send_slurm_command(self, cmd):
        if docker:
            child = pexpect.spawn('ssh slurm@slurm')
            choice = child.expect(["(yes/no)", "password"])
            if choice == 0:
                child.sendline('yes')
                child.expect("password")
                child.sendline('clustertest')
            elif choice == 1:
                child.sendline('clustertest')

            child.expect("\$")
            child.sendline(cmd)
        else:
            child = pexpect.spawn('su - calcus')
            child.expect ('Password:')
            child.sendline('clustertest')
            child.expect('\$')
            child.sendline(cmd)

    def see_all(self):
        btn = self.driver.find_element_by_id("see_all_btn")
        btn.click()

    def clean_all_successful(self):
        btn = self.driver.find_element_by_id("clean_all_successful_btn")
        btn.click()

    def clean_all_completed(self):
        btn = self.driver.find_element_by_id("clean_all_completed_btn")
        btn.click()
