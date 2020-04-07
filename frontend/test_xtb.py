import glob
import os
import time
import unittest

from django.http import HttpResponse, HttpResponseRedirect
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import *
from django.contrib.auth.models import User
from shutil import copyfile, rmtree
from .tasks import run_procedure
from django.core.management import call_command

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(tests_dir, "scr")
RESULTS_DIR = os.path.join(tests_dir, "results")
SOLVENTS = [
    'Acetone',
    'Acetonitrile',
    'Benzene',
    'Dichloromethane',
    'Chloroform',
    'Carbon disulfide',
    'Dimethylformamide',
    'Dimethylsulfoxide',
    'Diethyl ether',
    'Water',
    'Methanol',
    'n-Hexane',
    'Tetrahydrofuran',
    'Toluene',
        ]

def create_user(username):
    p, u = User.objects.get_or_create(username=username, password="test1234")
    return p

counter = 1
def create_calculation(in_file, proc, solvent, user, project):
    global counter
    name = "Test"
    fname = in_file.split('/')[-1]
    ext = fname.split('.')[-1]

    charge = 0
    if fname.find("anion") != -1:
        charge = -1
    elif fname.find("dianion") != -1:
        charge = -2
    elif fname.find("cation") != -1:
        charge = 1
    elif fname.find("dication") != -1:
        charge = 2

    with open(in_file) as f:
        lines = f.readlines()

    struct = ''.join(lines)
    if ext == 'xyz':
        s = Structure.objects.create(xyz_structure=struct)
    elif ext == 'mol':
        s = Structure.objects.create(mol_structure=struct)
    elif ext == 'sdf':
        s = Structure.objects.create(sdf_structure=struct)
    else:
        print("unknown ext: {}".format(ext))

    e = Ensemble.objects.create()
    s.parent_ensemble = e
    s.save()
    e.save()

    params = Parameters.objects.create(solvent=solvent, charge=charge, multiplicity=1)
    c = Calculation.objects.create(id=counter, name=name, date=timezone.now(), global_parameters=params, ensemble=e)
    counter += 1

    user.profile.calculation_set.add(c)
    project.calculation_set.add(c)

    c.save()
    project.save()
    user.profile.save()

    id = str(c.id)
    scr = os.path.join(SCR_DIR, id)

    os.mkdir(scr)

    #copyfile(in_file, os.path.join(scr, "initial.{}".format(ext)))

    return c

def create_project(user, name):
    p, created = Project.objects.get_or_create(name=name, author=user.profile)
    p.save()
    return p

class JobTestCase(TestCase):

    def run_calc(self, drawing, calc, type):

        calc.status = 1
        calc.save()

        proc = Procedure.objects.get(name=type)
        calc.procedure = proc
        calc.save()
        proc.save()
        os.chdir(os.path.join(SCR_DIR, str(calc.id)))

        ti = time.time()

        retval = run_procedure(drawing, calc.id)

        calc = Calculation.objects.get(pk=calc.id)

        for f in glob.glob(os.path.join(SCR_DIR, str(calc.id)) + '/*/'):
            for ff in glob.glob("{}*.out".format(f)):
                fname = ff.split('/')[-1]
                copyfile(ff, os.path.join(RESULTS_DIR, str(calc.id)) + '/' + fname)

        tf = time.time()
        execution_time = tf - ti

        job_id = str(calc.id)

        if retval == 0:
            calc.status = 2
        else:
            calc.status = 3
            calc.error_message = "Unknown error"

        calc.save()

        self.status = calc.status
        self.id = str(calc.id)
        return calc

    def tearDown(self):
        try:
            a = self.status
            if a == 2:
                if os.path.isdir(os.path.join(SCR_DIR, self.id)):
                    rmtree(os.path.join(SCR_DIR, self.id))
        except:
            pass

    def setUp(self):
        call_command('init_static_obj')
        pass

    @classmethod
    def setUpClass(self):
        self.user = create_user("test")

        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)
        if not os.path.isdir(RESULTS_DIR):
            os.mkdir(RESULTS_DIR)

        self.project = create_project(self.user, "TestProject")

    @classmethod
    def tearDownClass(self):
        pass
        return
        if os.path.isdir(SCR_DIR):
            rmtree(SCR_DIR)
        if os.path.isdir(RESULTS_DIR):
            rmtree(RESULTS_DIR)

def gen_test(in_file, type, solvent):
    def test(self):
        c = create_calculation(in_file, type, solvent, self.user, self.project)

        c = self.run_calc(False, c, type)

        id = str(c.id)

        self.assertEqual(c.status, 2)
        self.assertTrue(c.result_ensemble != None)

        calc_path = os.path.join(RESULTS_DIR, id)

        if type == "Simple Optimisation":
            self.assertTrue(c.result_ensemble.structure_set.count() == 1)
            with open(os.path.join(calc_path, "xtb_opt.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("normal termination of xtb") != -1)

        elif type == "Conformational Search":
            with open(os.path.join(calc_path, "crest.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("CREST terminated normally.") != -1)
        elif type == "Constrained Optimisation":
            pass
        elif type == "Simple UV-Vis":
            with open(os.path.join(calc_path, "xtb_opt.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("normal termination of xtb") != -1)

            with open(os.path.join(calc_path, "xtb4stda.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("wall time for all") != -1)

            with open(os.path.join(calc_path, "stda.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-2].find("sTDA done.") != -1)
        elif type == "MO Generation":
            with open(os.path.join(calc_path, "xtb_opt.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("normal termination of xtb") != -1)
            with open(os.path.join(calc_path, "orca_mo.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-2].find("ORCA TERMINATED NORMALLY") != -1)
        elif type == "Opt+Freq":
            with open(os.path.join(calc_path, "xtb_opt.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("normal termination of xtb") != -1)

            with open(os.path.join(calc_path, "xtb_freq.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("normal termination of xtb") != -1)
        elif type == "TS+Freq":
            with open(os.path.join(calc_path, "xtb_ts.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-2].find("ORCA TERMINATED NORMALLY") != -1)

            with open(os.path.join(calc_path, "xtb_freq.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("normal termination of xtb") != -1)
        elif type == "NMR Prediction":
            pass
    return test


input_files = glob.glob(tests_dir + '*.*')
input_files = [
                'benzene.mol',
                'carbo_cation.mol',
                #'Cl-iodane_2D.mol',
                'enolate_anion.mol',
                'ethanol.sdf',
                'EtMgBr.mol',
                'FeCl2.mol',
                'NH3.mol',
                'propane.mol'
                ]
#TYPES = [0, 1, 2, 3]
TYPES = [
            "Simple Optimisation",
            #"Constrained Optimisation",
            "Conformational Search",
            "Opt+Freq",
            "TS+Freq",
            "Simple UV-Vis",
            #"NMR Prediction",
            "MO Generation",
        ]

for type in TYPES:
    solvent = "Vacuum"
    for f in input_files:
        in_name = f.split('.')[0]
        test_name = "test_{}_{}_{}".format(in_name, type.replace(' ', '_'), solvent)
        test = gen_test(os.path.join(tests_dir, f), type, solvent)
        setattr(JobTestCase, test_name, test)

'''
for solv in SOLVENTS:
    for f in [input_files[i] for i in [0, 4, 6]]:
        for type in TYPES:
            in_name = f.split('.')[0]
            test_name = "test_{}_{}_{}".format(in_name, type, solv)
            test = gen_test(os.path.join(tests_dir, f), type, solv)
            setattr(JobTestCase, test_name, test)
'''
class ModelTestCase(TestCase):
    def setUp(self):
        self.bs1 = BasicStep.objects.create(name="step1")
        self.bs2 = BasicStep.objects.create(name="step2")
        self.bs3 = BasicStep.objects.create(name="step3")
        self.bs4 = BasicStep.objects.create(name="step4")
        self.bs1.save()
        self.bs2.save()
        self.bs3.save()
        self.bs4.save()

    def test_procedure_singlestep(self):
        params = Parameters.objects.create(name="TestParams", charge=1, multiplicity=1)
        params.save()

        p = Procedure.objects.create(name="TestProcedure")
        p.save()

        s1 = Step.objects.create(step_model=self.bs1, parent_procedure=p, parameters=params, from_procedure=p)
        s1.save()

        self.assertEqual(s1.parent_procedure.name, "TestProcedure")
        self.assertEqual(len(p.step_set.all()), 1)
        self.assertEqual(len(p.initial_steps.all()), 1)

    def test_procedure_multistep(self):
        params = Parameters.objects.create(name="TestParams", charge=1, multiplicity=1)
        params.save()

        p = Procedure.objects.create(name="TestProcedure")
        p.save()

        s1 = Step.objects.create(step_model=self.bs1, parent_procedure=p, parameters=params, from_procedure=p)
        s1.save()
        s2 = Step.objects.create(step_model=self.bs2, parent_step=s1, parameters=params, from_procedure=p)
        s2.save()

        self.assertEqual(len(p.step_set.all()), 2)
        self.assertEqual(len(p.initial_steps.all()), 1)
        self.assertEqual(len(s1.step_set.all()), 1)
class ViewTestCase(TestCase):
    @classmethod
    def setUpClass(self):
        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)
        if not os.path.isdir(RESULTS_DIR):
            os.mkdir(RESULTS_DIR)

    @classmethod
    def tearDownClass(self):
        if os.path.isdir(SCR_DIR):
            rmtree(SCR_DIR)
        if os.path.isdir(RESULTS_DIR):
            rmtree(RESULTS_DIR)

    def setUp(self):
        self.bs1 = BasicStep.objects.create(name="step1")
        self.bs2 = BasicStep.objects.create(name="step2")
        self.bs3 = BasicStep.objects.create(name="step3")
        self.bs4 = BasicStep.objects.create(name="step4")
        self.bs1.save()
        self.bs2.save()
        self.bs3.save()
        self.bs4.save()
        self.client = Client()
        self.submit_url = reverse('submit_calculation', 'frontend.urls')
        u = User.objects.create(username="Tester")
        u.set_password('xxPassWordxx')
        u.save()
        self.profile = Profile.objects.get(user__username="Tester")
        self.profile.is_PI = True
        self.profile.save()
        self.client.login(username="Tester", password="xxPassWordxx")

    def test_basic_calc_fail(self):
        with open(os.path.join(tests_dir, 'benzene.mol')) as f:
            response = self.client.post(self.submit_url, {
                'file_structure': f,
                'calc_name': 'TestCalc',
                'calc_type': 'Opt+Freq',
                'calc_project': 'New Project',
                'new_project_name': 'TestProject',
                'calc_charge': '0',
                'calc_solvent': 'Vacuum',
                'calc_ressource': 'Local',
            })

        self.assertTemplateUsed('frontend/error.html')


    def test_basic_calc(self):
        proc = Procedure.objects.create(name="Opt+Freq")

        with open(os.path.join(tests_dir, 'benzene.mol')) as f:
            response = self.client.post(self.submit_url, {
                'file_structure': f,
                'calc_name': 'TestCalc',
                'calc_type': 'Opt+Freq',
                'calc_project': 'New Project',
                'new_project_name': 'TestProject',
                'calc_charge': '0',
                'calc_solvent': 'Vacuum',
                'calc_ressource': 'Local',
            })

        self.assertTrue(isinstance(response, HttpResponseRedirect))

        c = Calculation.objects.get(name='TestCalc')
        self.assertEqual(c.project.name, 'TestProject')
        self.assertEqual(c.global_parameters.charge, 0)

        self.assertTrue(os.path.isdir(os.path.join(SCR_DIR, str(c.id))))
