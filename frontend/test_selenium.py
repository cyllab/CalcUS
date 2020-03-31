import os
import time
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import LiveServerTestCase
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

from labsandbox.celery import app

from .models import *

dir_path = os.path.dirname(os.path.realpath(__file__))

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(tests_dir, "scr")
RESULTS_DIR = os.path.join(tests_dir, "results")

class UserPermissionsTests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = webdriver.Chrome()

        app.loader.import_module('celery.contrib.testing.tasks')
        cls.celery_worker = start_worker(app, perform_ping_check=False)
        cls.celery_worker.__enter__()

        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)
        if not os.path.isdir(RESULTS_DIR):
            os.mkdir(RESULTS_DIR)


    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
        cls.celery_worker.__exit__(None, None, None)

        if os.path.isdir(SCR_DIR):
            rmtree(SCR_DIR)
        if os.path.isdir(RESULTS_DIR):
            rmtree(RESULTS_DIR)


    def setUp(self):
        self.username = "Selenium"
        self.password = "test1234"

        u = User.objects.create_superuser(username=self.username, password=self.password)#Weird things happen if the user is not superuser...
        u.save()
        self.login(self.username, self.password)

    def tearDown(self):
        pass

    def login(self, username, password):
        self.driver.get('{}/accounts/login/'.format(self.live_server_url))

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "id_username"))
        )
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "id_password"))
        )

        username_f = self.driver.find_element_by_id('id_username')
        password_f = self.driver.find_element_by_id('id_password')
        submit = self.driver.find_element_by_xpath('/html/body/div/div[2]/div/section/div[1]/div/form/div[2]/input[1]')
        username_f.send_keys(username)
        password_f.send_keys(password)
        submit.send_keys(Keys.RETURN)

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "calculations_list"))
        )

    def logout(self):
        self.driver.get('{}/accounts/logout/?next=/'.format(self.live_server_url))

    def test_access_calc_without_permission(self):
        u = User.objects.create_superuser(username="OtherPI", password="irrelevant")
        p = Profile.objects.get(user__username="OtherPI")
        proj = Project.objects.create(author=p, name="SecretProj")
        c = Calculation.objects.create(name="test", date=datetime.datetime.now(), charge=0, type=0, status=2, author=p, project=proj)
        proj.save()
        c.save()
        p.save()

        self.lget('/details/1')
        self.driver.implicitly_wait(5)
        self.assertEqual(self.driver.current_url.split('/')[-2], 'home')

    def test_launch_without_group(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }

        self.basic_launch(params, 10)

    def test_request_PI(self):
        self.driver.get('{}/profile/'.format(self.live_server_url))
        group_name = self.driver.find_element_by_name('group_name')
        submit = self.driver.find_element_by_xpath('/html/body/div/div[2]/div/div[1]/form/button')
        group_name.send_keys("Test group")
        submit.send_keys(Keys.RETURN)

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "PI_application_message"))
        )

        self.assertTrue(self.driver.find_element_by_id("PI_application_message").text.find("Your request has been received") != -1)

    def lget(self, url):
        self.driver.get('{}{}'.format(self.live_server_url, url))

    def test_manage_PI_request(self):
        self.lget('/profile/')
        group_name = self.driver.find_element_by_name('group_name')
        submit = self.driver.find_element_by_xpath('/html/body/div/div[2]/div/div[1]/form/button')
        group_name.send_keys("Test group")
        submit.send_keys(Keys.RETURN)

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "PI_application_message"))
        )
        self.logout()

        u = User.objects.create_superuser(username="SU", password=self.password)
        u.save()
        p = Profile.objects.get(user__username="SU")
        p.is_SU = True
        p.save()

        self.login("SU", self.password)
        self.lget('/manage_pi_requests/')
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "table"))
        )

        table = self.driver.find_element_by_class_name('table')

        self.assertTrue(table.text.find("Accept") != -1)
        self.assertTrue(table.text.find("Deny") != -1)

        accept_button = self.driver.find_element_by_xpath('/html/body/div/div/table/tbody/tr[1]/td[1]/button')
        accept_button.send_keys(Keys.RETURN)
        self.logout()

        self.login(self.username, self.password)

        self.driver.get('{}/launch/'.format(self.live_server_url))

        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }
        self.launch_calc(params)
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "calc_title"))
        )

        element = WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element((By.ID, "calc_title"), "Done")
        )


    def launch_calc(self, params):
        name_input = self.driver.find_element_by_name('calc_name')
        solvent_input = self.driver.find_element_by_name('calc_solvent')
        charge_input = self.driver.find_element_by_name('calc_charge')
        project_input = self.driver.find_element_by_id('calc_project')
        new_project_input = self.driver.find_element_by_name('new_project_name')
        calc_type_input = self.driver.find_element_by_id('calc_type')
        ressource_input = self.driver.find_element_by_name('calc_ressource')
        upload_input = self.driver.find_element_by_name('file_structure')
        submit = self.driver.find_element_by_xpath('/html/body/div[1]/div/div[2]/form/div[7]/div/button')

        name_input.send_keys(params['calc_name'])

        if 'solvent' in params.keys():
            self.driver.find_element_by_xpath("/html/body/div[1]/div/div[2]/form/div[2]/div[2]/div/div/div/select/option[text()='{}']".format(params['solvent'])).click()

        if 'charge' in params.keys():
            self.driver.find_element_by_xpath("/html/body/div[1]/div/div[2]/form/div[2]/div[3]/div/div/div/select/option[text()='{}']".format(params['charge'])).click()

        if 'type' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_type']/option[text()='{}']".format(params['type'])).click()

        self.driver.find_element_by_xpath("//*[@id='calc_project']/option[text()='{}']".format(params['project'])).click()

        if 'new_project_name' in params.keys():
            new_project_input.send_keys(params['new_project_name'])

        if 'in_file' in params.keys():
            upload_input.send_keys("{}/tests/{}".format(dir_path, params['in_file']))

        submit.send_keys(Keys.RETURN)

    def basic_launch(self, params, delay):
        self.driver.get('{}/launch/'.format(self.live_server_url))

        self.driver.implicitly_wait(10)
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "editor"))
        )
        element = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.NAME, "calc_name"))
        )

        element = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.NAME, "calc_solvent"))
        )

        element = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.NAME, "calc_project"))
        )

        self.launch_calc(params)

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "box"))
        )
        self.assertTrue(self.driver.find_element_by_class_name('box').text.find("You have no computing ressource") != -1)


class CalculationTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = webdriver.Chrome()
        cls.username = "Selenium"
        cls.password = "test1234"

        app.loader.import_module('celery.contrib.testing.tasks')
        cls.celery_worker = start_worker(app, perform_ping_check=False)
        cls.celery_worker.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
        cls.celery_worker.__exit__(None, None, None)

    def setUp(self):
        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)
        if not os.path.isdir(RESULTS_DIR):
            os.mkdir(RESULTS_DIR)

        u = User.objects.create_superuser(username=self.username, password=self.password)#Weird things happen if the user is not superuser...
        u.save()
        p = Profile.objects.get(user__username=self.username)
        self.login()
        a = ResearchGroup(PI=p)
        p.is_PI = True
        a.save()
        p.save()

    def tearDown(self):
        if os.path.isdir(SCR_DIR):
            rmtree(SCR_DIR)
        if os.path.isdir(RESULTS_DIR):
            rmtree(RESULTS_DIR)

    def lget(self, url):
        self.driver.get('{}{}'.format(self.live_server_url, url))

    def login(self):
        self.driver.get('{}/accounts/login/'.format(self.live_server_url))
        username_f = self.driver.find_element_by_id('id_username')
        password_f = self.driver.find_element_by_id('id_password')
        submit = self.driver.find_element_by_xpath('/html/body/div/div[2]/div/section/div[1]/div/form/div[2]/input[1]')
        username_f.send_keys(self.username)
        password_f.send_keys(self.password)
        submit.send_keys(Keys.RETURN)

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "calculations_list"))
        )

    def get_charge(self, fname):

        charge = 0
        if fname.find("anion"):
            charge = -1
        elif fname.find("dianion"):
            charge = -2
        elif fname.find("cation"):
            charge = 1
        elif fname.find("dication"):
            charge = 2

        return charge, fname.replace('dianion', '').replace('dication', '').replace('anion', '').replace('cation', '')

    def launch_calc(self, params):
        name_input = self.driver.find_element_by_name('calc_name')
        solvent_input = self.driver.find_element_by_name('calc_solvent')
        charge_input = self.driver.find_element_by_name('calc_charge')
        project_input = self.driver.find_element_by_id('calc_project')
        new_project_input = self.driver.find_element_by_name('new_project_name')
        calc_type_input = self.driver.find_element_by_id('calc_type')
        ressource_input = self.driver.find_element_by_name('calc_ressource')
        upload_input = self.driver.find_element_by_name('file_structure')
        submit = self.driver.find_element_by_xpath('/html/body/div[1]/div/div[2]/form/div[7]/div/button')

        name_input.click()
        name_input.send_keys(params['calc_name'])

        if 'solvent' in params.keys():
            self.driver.find_element_by_xpath("/html/body/div[1]/div/div[2]/form/div[2]/div[2]/div/div/div/select/option[text()='{}']".format(params['solvent'])).click()

        if 'charge' in params.keys():
            self.driver.find_element_by_xpath("/html/body/div[1]/div/div[2]/form/div[2]/div[3]/div/div/div/select/option[text()='{}']".format(params['charge'])).click()

        if 'type' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_type']/option[text()='{}']".format(params['type'])).click()

        self.driver.find_element_by_xpath("//*[@id='calc_project']/option[text()='{}']".format(params['project'])).click()

        if 'new_project_name' in params.keys():
            new_project_input.click()
            new_project_input.send_keys(params['new_project_name'])

        if 'in_file' in params.keys():
            upload_input.send_keys("{}/tests/{}".format(dir_path, params['in_file']))

        submit.send_keys(Keys.RETURN)

    def basic_launch(self, params, delay):
        self.driver.get('{}/launch/'.format(self.live_server_url))

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "editor"))
        )
        element = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.NAME, "calc_name"))
        )


        self.launch_calc(params)

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "calc_title"))
        )

        url = self.driver.current_url.split('/')
        self.assertTrue(url[-2] == "details")

        status_bar = self.driver.find_element_by_id('calc_title')

        element = WebDriverWait(self.driver, delay).until(
            EC.text_to_be_present_in_element((By.ID, "calc_title"), 'Done')
        )

    def test_opt(self):
        self.client.login(username=self.username, password=self.password)
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }

        self.basic_launch(params, 10)

    def test_proj(self):
        self.client.login(username=self.username, password=self.password)
        p = Profile.objects.get(user__username=self.username)
        proj = Project.objects.create(author=p, name="TestProj")
        proj.save()
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'TestProj',
                'in_file': 'benzene.mol',
                }

        self.basic_launch(params, 20)

    def test_opt_freq(self):
        self.client.login(username=self.username, password=self.password)
        params = {
                'calc_name': 'test',
                'type': 'Opt+Freq',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                }

        self.basic_launch(params, 20)

    def test_conf_search(self):
        self.client.login(username=self.username, password=self.password)
        params = {
                'calc_name': 'test',
                'type': 'Conformer Search',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ethanol.sdf',
                }

        self.basic_launch(params, 120)

    '''
    def test_ts(self):
        self.client.login(username=self.username, password=self.password)
        params = {
                'calc_name': 'test',
                'type': 'TS+Freq',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'ts.xyz',
                }

        self.basic_launch(params, 20)
    '''
    def test_second_step(self):
        self.client.login(username=self.username, password=self.password)
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }

        self.basic_launch(params, 20)

        calc_id = self.driver.current_url.split('/')[-1]
        next_button = self.lget('/launch/{}'.format(calc_id))

        params2 = {
                'calc_name': 'test2',
                'type': 'Opt+Freq',
                'project': 'SeleniumProject',
                }

        self.launch_calc(params)

        element = WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element((By.ID, "calc_title"), 'Done')
        )

