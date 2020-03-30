import os

from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from django.contrib.auth.models import User, Group

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

dir_path = os.path.dirname(os.path.realpath(__file__))

class LaunchTestCase(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Firefox()
        cls.user = "Steve"
        cls.password = "betatest"
        cls.login(cls)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def login(self):
        self.driver.get('http://127.0.0.1:8000/accounts/login/')
        username = self.driver.find_element_by_id('id_username')
        password = self.driver.find_element_by_id('id_password')
        submit = self.driver.find_element_by_xpath('/html/body/div/div[2]/div/section/div[1]/div/form/div[2]/input[1]')
        username.send_keys(self.user)
        password.send_keys(self.password)
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
        self.driver.get('http://127.0.0.1:8000/launch/')

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
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }

        self.basic_launch(params, 10)

    def test_opt_freq(self):
        params = {
                'calc_name': 'test',
                'type': 'Opt+Freq',
                'project': 'SeleniumProject',
                'in_file': 'carbo_cation.mol',
                'charge': '+1',
                }

        self.basic_launch(params, 10)

    def test_conf_search(self):
        params = {
                'calc_name': 'test',
                'type': 'Conformer Search',
                'project': 'SeleniumProject',
                'in_file': 'ethanol.sdf',
                }

        self.basic_launch(params, 120)
