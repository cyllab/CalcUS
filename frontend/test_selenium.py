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

class AccountTestCase(LiveServerTestCase):
    def setUp(self):
        self.driver = webdriver.Firefox()
        self.user = "Steve"
        self.password = "betatest"
        self.login()

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

        url = self.driver.current_url.split('/')
        self.assertTrue(url[-2] == "home")

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

    def test_basic_launch(self):
        self.driver.get('http://127.0.0.1:8000/launch/')

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "editor"))
        )

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

        url = self.driver.current_url.split('/')
        self.assertTrue(url[-2] == "details")

        status_bar = self.driver.find_element_by_id('calc_title')

        element = WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element((By.ID, "calc_title"), 'Done')
        )

