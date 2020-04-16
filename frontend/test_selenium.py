import os
import time
import sys
import glob
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import LiveServerTestCase
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

from labsandbox.celery import app

from .models import *
from django.core.management import call_command

dir_path = os.path.dirname(os.path.realpath(__file__))

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(tests_dir, "scr")
RESULTS_DIR = os.path.join(tests_dir, "results")

for s in glob.glob("{}/selenium_screenshots/*.png".format(dir_path)):
    os.remove(s)

class CalcusLiveServer(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = webdriver.Chrome()
        cls.driver.set_window_size(1424, 768)

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
        call_command('init_static_obj')
        self.username = "Selenium"
        self.password = "test1234"

        u = User.objects.create_superuser(username=self.username, password=self.password)#Weird things happen if the user is not superuser...
        u.save()
        self.login(self.username, self.password)
        self.profile = Profile.objects.get(user__username=self.username)

    def tearDown(self):
        for method, error in self._outcome.errors:
            if error:
                test_method_name = self._testMethodName
                self.driver.get_screenshot_as_file("{}/selenium_screenshots/{}.png".format(dir_path, test_method_name))

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
            EC.presence_of_element_located((By.ID, "projects_list"))
        )

    def logout(self):
        self.driver.get('{}/accounts/logout/?next=/'.format(self.live_server_url))

    def lget(self, url):
        self.driver.get('{}{}'.format(self.live_server_url, url))

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

    def calc_input_params(self, params):
        self.driver.implicitly_wait(10)
        if 'calc_name' in params.keys():
            element = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.NAME, "calc_name"))
            )
            name_input = self.driver.find_element_by_name('calc_name')

        element = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.NAME, "calc_solvent"))
        )

        element = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.NAME, "calc_project"))
        )

        solvent_input = self.driver.find_element_by_name('calc_solvent')
        charge_input = self.driver.find_element_by_name('calc_charge')
        project_input = self.driver.find_element_by_id('calc_project')
        new_project_input = self.driver.find_element_by_name('new_project_name')
        calc_type_input = self.driver.find_element_by_id('calc_type')
        ressource_input = self.driver.find_element_by_name('calc_ressource')
        try:
            upload_input = self.driver.find_element_by_name('file_structure')
        except selenium.common.exceptions.NoSuchElementException:
            pass

        if 'calc_name' in params.keys():
            name_input.send_keys(params['calc_name'])

        if 'solvent' in params.keys():
            self.driver.find_element_by_xpath("/html/body/div[1]/div/div[2]/form/div[2]/div[2]/div/div/div/select/option[text()='{}']".format(params['solvent'])).click()

        if 'charge' in params.keys():
            self.driver.find_element_by_xpath("/html/body/div[1]/div/div[2]/form/div[2]/div[3]/div/div/div/select/option[text()='{}']".format(params['charge'])).click()

        if 'type' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_type']/option[text()='{}']".format(params['type'])).click()

        if 'project' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_project']/option[text()='{}']".format(params['project'])).click()

        if 'new_project_name' in params.keys():
            new_project_input.send_keys(params['new_project_name'])

        if 'in_file' in params.keys():
            upload_input.send_keys("{}/tests/{}".format(dir_path, params['in_file']))

    def calc_launch(self):
        submit = self.driver.find_element_by_id('submit_button')
        submit.click()

    def get_number_calc_orders(self):
        assert self.is_on_page_calculations()
        calculations_container = self.driver.find_element_by_id("calculations_list")
        try:
            calculations_div = calculations_container.find_element_by_css_selector(".grid")
        except selenium.common.exceptions.NoSuchElementException:
            assert calculations_container.text.find('No calculation') != -1
            return 0

        calculations = calculations_div.find_elements_by_css_selector("article")
        num = len(calculations)
        return num

    def get_number_calc_methods(self):
        assert self.is_on_page_ensemble()

        tabs_list = self.driver.find_element_by_css_selector("#tabs")
        tabs = tabs_list.find_elements_by_css_selector("li")
        return len(tabs)

    def get_split_url(self):
        return self.driver.current_url.split('/')[3:]

    def get_group_panel(self):
        return self.driver.find_element_by_xpath("/html/body/article")

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
        users = panel.find_elements_by_css_selector(".panel-block")

        assert len(users) > 0

        return len(users)

    def group_click_member(self, name):
        assert self.group_panel_present()

        panel = self.get_group_panel()
        users = panel.find_elements_by_css_selector(".panel-block")

        for u in users:
            username = u.text
            if username == name:
                button = u.find_element_by_css_selector("a.button")
                button.click()
                return
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

    def is_on_page_projects(self):
        url = self.get_split_url()
        if (url[0] == 'projects' or url[0] == 'home') and (url[1] == '' or self.is_user(url[1])):
            return True
        else:
            return False

    def is_on_page_user_project(self):
        url = self.get_split_url()
        if url[0] == 'projects' and self.is_user(url[1]) and self.is_user_project(url[1], url[2]):
            return True
        else:
            return False

    def is_on_page_calculations(self):
        url = self.get_split_url()
        if url[0] == 'calculations' and url[1] == '':
            return True
        else:
            return False

    def is_on_page_profile(self):
        url = self.get_split_url()
        if url[0] == 'profile' and url[1] == '':
            return True
        else:
            return False

    def is_on_page_managePI(self):
        url = self.get_split_url()
        if url[0] == 'manage_pi_requests' and url[1] == '':
            return True
        else:
            return False

    def is_on_page_molecule(self):
        url = self.get_split_url()

        try:
            mol_id = int(url[1])
        except:
            return False

        if url[0] == 'molecule' and self.is_molecule_id(mol_id):
            return True
        else:
            return False

    def is_on_page_ensemble(self):
        url = self.driver.current_url.split('/')[3:]

        try:
            e_id = int(url[1])
        except:
            return False

        if url[0] == 'ensemble' and self.is_ensemble_id(e_id):
            return True
        else:
            return False

    def get_number_projects(self):
        assert self.is_on_page_projects()

        project_div = self.driver.find_element_by_css_selector(".grid")
        projects = project_div.find_elements_by_css_selector("article")
        num = len(projects)
        if num == 0:
            assert project_div.text.find('No project') != -1
        return num

    def click_project(self, name):
        assert self.is_on_page_projects()

        project_div = self.driver.find_element_by_css_selector(".grid")
        projects = project_div.find_elements_by_css_selector("article")

        for proj in projects:
            p_name = proj.find_element_by_css_selector("div > p").text
            if p_name == name:
                proj.click()
                return

    def get_number_molecules(self):
        assert self.is_on_page_user_project()

        molecules_div = self.driver.find_element_by_css_selector(".grid")
        molecules = molecules_div.find_elements_by_css_selector("article")
        num = len(molecules)
        if num == 0:
            assert molecules_div.text.find('No molecule') != -1
        return num

    def click_molecule(self, name):
        assert self.is_on_page_user_project()

        molecules_div = self.driver.find_element_by_css_selector(".grid")
        molecules = molecules_div.find_elements_by_css_selector("article")

        for mol in molecules:
            mol_name = mol.find_element_by_css_selector("div > p").text
            if mol_name == name:
                mol.click()
                return

    def get_number_ensembles(self):
        assert self.is_on_page_molecule()

        ensembles_div = self.driver.find_element_by_css_selector(".grid")
        ensembles = ensembles_div.find_elements_by_css_selector("article")
        num = len(ensembles)
        if num == 0:
            assert ensembles_div.text.find('No ensemble') != -1
        return num

    def click_ensemble(self, name):
        assert self.is_on_page_molecule()

        ensembles_div = self.driver.find_element_by_css_selector(".grid")
        ensembles = ensembles_div.find_elements_by_css_selector("article")

        for e in ensembles:
            e_name = e.find_element_by_css_selector("div > p").text
            if e_name == name:
                e.click()
                return

    def click_latest_calc(self):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0

        calculations_container = self.driver.find_element_by_id("calculations_list")
        calculations_div = calculations_container.find_element_by_css_selector(".grid")
        calculations = calculations_div.find_elements_by_css_selector("article")
        calculations[0].click()

    def apply_PI(self, group_name):
        assert self.is_on_page_profile()
        group_name = self.driver.find_element_by_name('group_name')
        submit = self.driver.find_element_by_xpath('/html/body/div/div[2]/div/div[1]/form/button')
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

        accept_button = self.driver.find_element_by_xpath('/html/body/div/div/table/tbody/tr[1]/td[1]/button')
        accept_button.send_keys(Keys.RETURN)

    def wait_latest_calc_done(self, timeout):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0


        ind = 0
        while ind < timeout:
            calculations_container = self.driver.find_element_by_id("calculations_list")
            calculations_div = calculations_container.find_element_by_css_selector(".grid")
            calculations = calculations_div.find_elements_by_css_selector("article")
            header = calculations[0].find_element_by_class_name("message-header")
            if "has-background-success" in header.get_attribute("class") or "has-background-danger" in header.get_attribute("class"):
                    return
            time.sleep(1)
            ind += 1
            self.driver.refresh()

    def latest_calc_successful(self):
        assert self.is_on_page_calculations()
        assert self.get_number_calc_orders() > 0


        calculations_container = self.driver.find_element_by_id("calculations_list")
        calculations_div = calculations_container.find_element_by_css_selector(".grid")
        calculations = calculations_div.find_elements_by_css_selector("article")
        header = calculations[0].find_element_by_class_name("message-header")
        return "has-background-success" in header.get_attribute("class")

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
        button_submit = self.driver.find_element_by_xpath("/html/body/div/div[3]/div/div/div[1]/div/button")
        field_username.send_keys(username)
        field_code.send_keys(code)
        button_submit.send_keys(Keys.RETURN)

    def launch_ensemble_next_step(self):
        assert self.is_on_page_ensemble()
        button = self.driver.find_element_by_xpath("/html/body/div[1]/div/div[2]/div[1]/a")
        button.click()

    def launch_structure_next_step(self):
        assert self.is_on_page_ensemble()
        button = self.driver.find_element_by_xpath("/html/body/div[1]/div/div[2]/div[1]/button[5]")
        button.click()

    def delete_project(self, name):
        assert self.is_on_page_projects()
        main_window_handle = None
        while not main_window_handle:
            main_window_handle = self.driver.current_window_handle

        project_div = self.driver.find_element_by_css_selector(".grid")
        projects = project_div.find_elements_by_css_selector("article")

        for proj in projects:
            p_name = proj.find_element_by_css_selector("div > p").text
            if p_name == name:
                trash = proj.find_element_by_css_selector(".message-header > div > a > i.fa-trash-alt")
                trash.click()

                alert = self.driver.switch_to_alert()
                alert.accept()
                self.driver.switch_to_default_content()
                return

    def delete_molecule(self, name):
        assert self.is_on_page_user_project()
        main_window_handle = None
        while not main_window_handle:
            main_window_handle = self.driver.current_window_handle

        molecule_div = self.driver.find_element_by_css_selector(".grid")
        molecules = molecule_div.find_elements_by_css_selector("article")

        for mol in molecules:
            mol_name = mol.find_element_by_css_selector("div > p").text
            if mol_name == name:
                trash = mol.find_element_by_css_selector(".message-header > div > a > i.fa-trash-alt")
                trash.click()

                alert = self.driver.switch_to_alert()
                alert.accept()
                self.driver.switch_to_default_content()
                return

    def delete_ensemble(self, name):
        assert self.is_on_page_molecule()
        main_window_handle = None
        while not main_window_handle:
            main_window_handle = self.driver.current_window_handle

        ensemble_div = self.driver.find_element_by_css_selector(".grid")
        ensembles = ensemble_div.find_elements_by_css_selector("article")

        for e in ensembles:
            e_name = e.find_element_by_css_selector("div > p").text
            if e_name == name:
                trash = e.find_element_by_css_selector(".message-header > div > a > i.fa-trash-alt")
                trash.click()

                alert = self.driver.switch_to_alert()
                alert.accept()
                self.driver.switch_to_default_content()
                return


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

    #Test delete other user's stuff

class UserPermissionsTests(CalcusLiveServer):
    def test_launch_without_group(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
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
                'in_file': 'benzene.mol',
                }
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations")
        self.assertEqual(self.get_number_calc_orders(), 1)


class CalculationTestsPI(CalcusLiveServer):

    '''
    def test_text_opt(self):
        #Will fail
        self.client.login(username=self.username, password=self.password)
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_text': 'Cl-iodane_2D.mol',
                }

        self.basic_launch(params, 10)
    '''

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
                'in_file': 'benzene.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertTrue(self.is_on_page_molecule())

    def test_proj(self):
        proj = Project.objects.create(author=self.profile, name="TestProj")
        proj.save()

        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'TestProj',
                'in_file': 'benzene.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertTrue(self.is_on_page_molecule())

    def test_opt_freq(self):
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
        self.assertTrue(self.is_on_page_molecule())

    def test_conf_search(self):
        params = {
                'calc_name': 'test',
                'type': 'Crest',
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
        self.assertTrue(self.is_on_page_molecule())

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
        self.click_latest_calc()
        self.assertTrue(self.is_on_page_molecule())

    def test_ensemble_second_step(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.click_ensemble("Geometrical Optimisation Result")
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
        self.assertTrue(self.is_on_page_molecule())

    def test_structure_second_step(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.click_ensemble("Geometrical Optimisation Result")
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
        self.assertTrue(self.is_on_page_molecule())

class CalculationTestsStudent(CalcusLiveServer):
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
                'in_file': 'benzene.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertTrue(self.is_on_page_molecule())

    def test_proj(self):
        student = Profile.objects.get(user__username="Student")
        proj = Project.objects.create(author=student, name="TestProj")
        proj.save()

        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'TestProj',
                'in_file': 'benzene.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertTrue(self.is_on_page_molecule())

    def test_opt_freq(self):
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
        self.assertTrue(self.is_on_page_molecule())

    def test_conf_search(self):
        params = {
                'calc_name': 'test',
                'type': 'Crest',
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
        self.assertTrue(self.is_on_page_molecule())

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
        self.click_latest_calc()
        self.assertTrue(self.is_on_page_molecule())

    def test_ensemble_second_step(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.click_ensemble("Geometrical Optimisation Result")
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
        self.assertTrue(self.is_on_page_molecule())

    def test_structure_second_step(self):
        params = {
                'calc_name': 'test',
                'type': 'Geometrical Optimisation',
                'project': 'New Project',
                'new_project_name': 'SeleniumProject',
                'in_file': 'benzene.mol',
                }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.click_ensemble("Geometrical Optimisation Result")
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
        self.assertTrue(self.is_on_page_molecule())

