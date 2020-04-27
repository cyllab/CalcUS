import glob
import os
import time
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from django.http import HttpResponse, HttpResponseRedirect
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import *
from django.contrib.auth.models import User
from shutil import copyfile, rmtree, move
from .tasks import dispatcher, run_calc
from django.core.management import call_command

from celery.contrib.testing.worker import start_worker
from calcus.celery import app

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")
SCR_DIR = os.path.join(tests_dir, "scr")
RESULTS_DIR = os.path.join(tests_dir, "results")
REPORTS_DIR = os.path.join(tests_dir, "reports")

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

counter = 1

def create_user(username):
    p, u = User.objects.get_or_create(username=username, password="test1234")
    return p

def create_calculation(in_file, step_name, solvent, user, project):
    global counter
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

    step = BasicStep.objects.get(name=step_name)
    params = Parameters.objects.create(solvent=solvent, charge=charge, multiplicity=1)
    c = CalculationOrder.objects.create(id=counter, name="TestOrder", date=timezone.now(), parameters=params, ensemble=e, step=step)

    #user.profile.calculationorder_set.add(c)
    #project.calculationorder_set.add(c)

    c.save()
    #project.save()
    #user.profile.save()

    #scr = os.path.join(SCR_DIR, id)

    #os.mkdir(scr)

    counter += 1
    #copyfile(in_file, os.path.join(scr, "initial.{}".format(ext)))

    return c.id

def create_project(user, name):
    p, created = Project.objects.get_or_create(name=name, author=user.profile)
    p.save()
    return p

class JobTestCase(StaticLiveServerTestCase):

    def run_calc(self, drawing, order_id):

        #os.chdir(os.path.join(SCR_DIR, str(calc.id)))

        ti = time.time()

        submit_val = dispatcher.delay(drawing, order_id)
        time.sleep(1)

        #calculations = CalculationOrder.objects.all()[0].calculation_set.all()

        #for c in calculations:
        #    run_calc(c.id)

        ind = 0
        done = False
        while ind < 120 and not done:
            time.sleep(1)
            calculations = CalculationOrder.objects.get(pk=int(order_id)).calculation_set.all()
            done = True
            for c in calculations:
                if c.status != 2 and c.status != 3:
                    done = False
                    break
            ind += 1

        calculations = CalculationOrder.objects.get(pk=int(order_id)).calculation_set.all()
        for c in calculations:
            self.assertEqual(c.status, 2)

        return 0
        #calc = CalculationOrder.objects.get(pk=calc.id)

        tf = time.time()
        execution_time = tf - ti

        #job_id = str(calc.id)

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
            else:
                if os.path.isdir(os.path.join(SCR_DIR, self.id)):
                    move(os.path.join(SCR_DIR, self.id), os.path.join(REPORTS_DIR, self.id))
        except:
            pass
        if not os.path.isdir(SCR_DIR):
            rmtree(SCR_DIR)
        if not os.path.isdir(RESULTS_DIR):
            rmtree(RESULTS_DIR)


    def setUp(self):
        call_command('init_static_obj')
        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)
        if not os.path.isdir(RESULTS_DIR):
            os.mkdir(RESULTS_DIR)

    @classmethod
    def setUpClass(self):

        self.user = create_user("test")

        if not os.path.isdir(REPORTS_DIR):
            os.mkdir(REPORTS_DIR)

        self.project = create_project(self.user, "TestProject")

        app.loader.import_module('celery.contrib.testing.tasks')
        self.celery_worker = start_worker(app, perform_ping_check=False)
        self.celery_worker.__enter__()


    @classmethod
    def tearDownClass(self):
        #super().tearDownClass()
        self.celery_worker.__exit__(None, None, None)

def gen_test(in_file, _type, solvent):
    def test(self):
        order_id = create_calculation(in_file, _type, solvent, self.user, self.project)

        order = CalculationOrder.objects.get(pk=order_id)
        print("order ID: {}".format(order_id))
        c = self.run_calc(False, order_id)

        self.assertEqual(c, 0)
        #self.assertTrue(c.result_ensemble != None)

        calc_path = os.path.join(SCR_DIR, str(order.calculation_set.all()[0].id))

        if _type == "Geometrical Optimisation":
            with open(os.path.join(calc_path, "xtb_opt.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("normal termination of xtb") != -1)

        elif _type == "Crest":
            with open(os.path.join(calc_path, "crest.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("CREST terminated normally.") != -1)
        elif _type == "Constrained Optimisation":
            pass
        elif _type == "UV-Vis Calculation":
            with open(os.path.join(calc_path, "xtb4stda.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("wall time for all") != -1)

            with open(os.path.join(calc_path, "stda.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-2].find("sTDA done.") != -1)
        elif _type == "MO Generation":
            with open(os.path.join(calc_path, "xtb_opt.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("normal termination of xtb") != -1)
            with open(os.path.join(calc_path, "orca_mo.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-2].find("ORCA TERMINATED NORMALLY") != -1)
        elif _type == "Frequency Calculation":
            with open(os.path.join(calc_path, "xtb_freq.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("normal termination of xtb") != -1)
        elif _type == "TS Optimisation":
            with open(os.path.join(calc_path, "xtb_ts.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-2].find("ORCA TERMINATED NORMALLY") != -1)
        elif _type == "NMR Prediction":
            pass
        else:
            assert 1 == -1
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
            "Geometrical Optimisation",
            #"Constrained Optimisation",
            "Crest",
            "Frequency Calculation",
            "TS Optimisation",
            "UV-Vis Calculation",
        ]

for _type in TYPES:
    solvent = "Vacuum"
    for f in input_files:
        in_name = f.split('.')[0]
        test_name = "test_{}_{}_{}".format(in_name, _type.replace(' ', '_'), solvent)
        test = gen_test(os.path.join(tests_dir, f), _type, solvent)
        setattr(JobTestCase, test_name, test)

for solv in SOLVENTS:
    for type in ["Geometrical Optimisation", "Crest", "UV-Vis Calculation"]:
        in_name = input_files[0].split('.')[0]
        test_name = "test_{}_{}_{}".format(in_name, type, solv)
        test = gen_test(os.path.join(tests_dir, f), type, solv)
        setattr(JobTestCase, test_name, test)

