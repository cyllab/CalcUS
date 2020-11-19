import os
import time
import sys
import glob
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import datetime
import pexpect

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from shutil import copyfile, rmtree

from celery.contrib.testing.worker import start_worker
from django.core.management import call_command
from django.contrib.auth.models import User, Group
from .models import *

dir_path = os.path.dirname(os.path.realpath(__file__))

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(tests_dir, "scr")
RESULTS_DIR = os.path.join(tests_dir, "results")
CLUSTER_DIR = os.path.join(tests_dir, "cluster")
KEYS_DIR = os.path.join(tests_dir, "keys")

HEADLESS = os.getenv("CALCUS_HEADLESS")


from calcus.celery import app
class CalcusLiveServer(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        chrome_options = Options()
        if HEADLESS is not None and HEADLESS.lower() == "true":
            from pyvirtualdisplay import Display

            display = Display(visible=0, size=(1920, 1080))
            display.start()

        cls.driver = webdriver.Chrome(chrome_options=chrome_options)
        cls.driver.set_window_size(1920, 1080)

        app.loader.import_module('celery.contrib.testing.tasks')

        cls.celery_worker = start_worker(app, perform_ping_check=False)
        cls.celery_worker.__enter__()

        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)
        if not os.path.isdir(RESULTS_DIR):
            os.mkdir(RESULTS_DIR)
        if not os.path.isdir(CLUSTER_DIR):
            os.mkdir(CLUSTER_DIR)
        if not os.path.isdir(os.path.join(CLUSTER_DIR, 'todo')):
            os.mkdir(os.path.join(CLUSTER_DIR, 'todo'))
        if not os.path.isdir(os.path.join(CLUSTER_DIR, 'done')):
            os.mkdir(os.path.join(CLUSTER_DIR, 'done'))
        if not os.path.isdir(os.path.join(CLUSTER_DIR, 'connections')):
            os.mkdir(os.path.join(CLUSTER_DIR, 'connections'))
        if not os.path.isdir(KEYS_DIR):
            os.mkdir(KEYS_DIR)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
        cls.celery_worker.__exit__(None, None, None)

        if os.path.isdir(SCR_DIR):
            rmtree(SCR_DIR)
        if os.path.isdir(RESULTS_DIR):
            rmtree(RESULTS_DIR)
        if os.path.isdir(CLUSTER_DIR):
            rmtree(CLUSTER_DIR)
        if os.path.isdir(KEYS_DIR):
            rmtree(KEYS_DIR)

    def setUp(self):
        call_command('init_static_obj')
        self.username = "Selenium"
        self.password = "test1234"

        u = User.objects.create_superuser(username=self.username, password=self.password)#Weird things happen if the user is not superuser...
        u.save()
        self.login(self.username, self.password)
        self.profile = Profile.objects.get(user__username=self.username)
        time.sleep(0.1)#Reduces glitches (I think?)

    def tearDown(self):
        pass

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
            name_input.clear()
            name_input.send_keys(params['calc_name'])

        if 'solvent' in params.keys():
            solvent_input.send_keys(params['solvent'])

        if 'charge' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_charge']/option[text()='{}']".format(params['charge'])).click()

        if 'software' in params.keys():
            select = self.driver.find_element_by_id("calc_software")
            self.driver.execute_script("showDropdown = function (element) {var event; event = document.createEvent('MouseEvents'); event.initMouseEvent('mousedown', true, true, window); element.dispatchEvent(event); }; showDropdown(arguments[0]);",select)
            time.sleep(0.1)
            select.find_element_by_xpath("option[text()='{}']".format(params['software'])).click()

            self.driver.implicitly_wait(5)

        if 'type' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_type']/option[text()='{}']".format(params['type'])).click()

        if 'project' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_project']/option[text()='{}']".format(params['project'])).click()

        if 'solvation_method' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_solvation_model']/option[text()='{}']".format(params['solvation_method'])).click()

        if 'solvation_radii' in params.keys():
            self.driver.find_element_by_xpath("//*[@id='calc_solvation_radii']/option[text()='{}']".format(params['solvation_radii'])).click()

        if 'new_project_name' in params.keys():
            new_project_input.send_keys(params['new_project_name'])

        if 'in_file' in params.keys():
            upload_input.send_keys("{}/tests/{}".format(dir_path, params['in_file']))

        if 'in_files' in params.keys():
            for f in params['in_files']:
                upload_input.send_keys("{}/tests/{}".format(dir_path, f))

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
                    handle_constraint(c, ind)
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
            self.driver.find_element_by_css_selector("summary").click()

    def calc_launch(self):
        submit = self.driver.find_element_by_id('submit_button')
        submit.click()

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
        if badge is None:
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
        address.send_keys("localhost")

        username = self.driver.find_element_by_name("cluster_username")
        username.send_keys("calcus")

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

        for i in range(5):
            public_key = self.driver.find_element_by_id("public_key_area").text
            if public_key.strip() != "":
                break
            time.sleep(1)

        child = pexpect.spawn('su - calcus')
        child.expect ('Password:')
        child.sendline('clustertest')
        child.expect('\$')
        child.sendline("echo '{}' > /home/calcus/.ssh/authorized_keys".format(public_key))
        time.sleep(0.1)

    def connect_cluster(self):
        assert self.is_on_page_access()

        password = self.driver.find_element_by_id("ssh_password")
        password.clear()
        password.send_keys("Selenium")

        test_access = self.driver.find_element_by_id("connect_button")
        test_access.click()

        for i in range(10):
            time.sleep(1)
            try:
                msg = self.driver.find_element_by_id("test_msg").text
                if msg == "Connected":
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
        return int(sline[0]), int(sline[2].replace('(', '')), int(sline[4]), int(sline[6]), int(sline[8])

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
        return int(sline[0]), int(sline[2].replace('(', '')), int(sline[4]), int(sline[6]), int(sline[8])

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

        create_proj_box = self.driver.find_element_by_css_selector(".container > div > center > a")
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

        try:
            calculations_div = WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#calculations_list > .grid"))
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

    def details_first_calc(self):
        assert self.is_on_page_order_details()

        calcs = self.driver.find_elements_by_css_selector("tbody > tr")
        first_calc = calcs[0]
        buttons = first_calc.find_elements_by_css_selector(".button")
        details = buttons[0]
        assert details.text != "Kill"
        details.click()


    def cancel_all_calc(self):
        assert self.is_on_page_order_details()

        calcs = self.driver.find_elements_by_css_selector("tbody > tr")
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
        assert self.get_number_calc_orders() > 0

        for i in range(0, timeout, 2):
            calculations = self.get_calc_orders()

            header = calculations[0].find_element_by_class_name("message-header")
            if "has-background-success" in header.get_attribute("class") or "has-background-danger" in header.get_attribute("class"):
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
        button_submit = self.driver.find_element_by_css_selector("button.button:nth-child(4)")
        field_username.send_keys(username)
        field_code.send_keys(code)
        button_submit.send_keys(Keys.RETURN)

    def launch_ensemble_next_step(self):
        assert self.is_on_page_ensemble()
        button = WebDriverWait(self.driver, 0.5).until(
            EC.presence_of_element_located((By.ID, "next_step_ensemble"))
        )
        button.send_keys(Keys.RETURN)

    def launch_structure_next_step(self):
        assert self.is_on_page_ensemble()

        button = WebDriverWait(self.driver, 0.5).until(
            EC.presence_of_element_located((By.ID, "next_step_structure"))
        )
        table = WebDriverWait(self.driver, 0.5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#conf_table > tr"))
        )

        button.send_keys(Keys.RETURN)

    def launch_frame_next_step(self):
        assert self.is_on_page_calculation()

        button = WebDriverWait(self.driver, 0.5).until(
            EC.presence_of_element_located((By.ID, "launch_from_frame"))
        )

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

                alert = self.driver.switch_to_alert()
                alert.accept()
                self.driver.switch_to_default_content()
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

                alert = self.driver.switch_to_alert()
                alert.accept()
                self.driver.switch_to_default_content()
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

                alert = self.driver.switch_to_alert()
                alert.accept()
                self.driver.switch_to_default_content()
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

        try:
            table = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "vib_table"))
            )
        except selenium.common.exceptions.TimeoutException:
            return False

        rows = table.find_elements_by_css_selector("tr")

        if len(rows) > 0:
            return True
        return False

    def is_loaded_mo(self):
        assert self.is_on_page_ensemble()

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

        alert = self.driver.switch_to_alert()
        alert.send_keys(name)
        alert.accept()
        self.driver.switch_to_default_content()

    def load_preset(self, name):
        self.select_preset(name)
        button = self.driver.find_element_by_css_selector("a.button:nth-child(3)")
        button.click()

    def delete_preset(self, name):
        self.select_preset(name)
        button = self.driver.find_element_by_css_selector("a.button:nth-child(5)")
        button.click()

    def set_project_preset(self):
        button = self.driver.find_element_by_css_selector("a.button:nth-child(7)")
        button.click()

    def get_names_presets(self):
        select = self.driver.find_element_by_css_selector("#presets")
        presets = select.find_elements_by_css_selector("option")
        names = [p.text for p in presets]
        return names

    def select_preset(self, name):
        element = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='presets']/option[text()='{}']".format(name)))
        )

        self.driver.find_element_by_xpath("//*[@id='presets']/option[text()='{}']".format(name)).click()

