import glob
import os
import time
import unittest

from django.test import TestCase
from django.utils import timezone
from .models import Profile, Calculation, Structure, Project
from django.contrib.auth.models import User
from shutil import copyfile, rmtree
from .tasks import geom_opt, conf_search, uvvis_simple, nmr_enso

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

FUNCTIONS = {
        0: geom_opt,
        1: conf_search,
        2: uvvis_simple,
        3: nmr_enso,
        }
class TestInstance(unittest.TestCase):
    pass

def create_user(username):
    p, u = User.objects.get_or_create(username=username, password="test1234")
    return p


def create_calculation(in_file, type, solvent, user, project):
    name = "Test"
    fname = in_file.split('/')[-1]
    ext = fname.split('.')[-1]

    charge = 0
    if fname.find("anion"):
        charge = -1
    elif fname.find("dianion"):
        charge = -2
    elif fname.find("cation"):
        charge = 1
    elif fname.find("dication"):
        charge = 2

    c = Calculation.objects.create(name=name, date=timezone.now(), type=type, status=0, charge=charge, solvent=solvent)

    user.profile.calculation_set.add(c)
    project.calculation_set.add(c)

    c.save()
    project.save()
    user.profile.save()

    id = str(c.id)
    scr = os.path.join(SCR_DIR, id)

    os.mkdir(scr)
    copyfile(in_file, os.path.join(scr, "initial.{}".format(ext)))

    return c

def create_project(user, name):
    p, created = Project.objects.get_or_create(name=name, author=user.profile)
    p.save()
    return p

class JobTestCase(TestCase):

    def run_calc(self, f, args):
        calc_obj = Calculation.objects.get(pk=args[0])

        calc_obj.status = 1
        calc_obj.save()

        os.chdir(os.path.join(SCR_DIR, str(args[0])))
        _args = list(args)
        _args.append(calc_obj)

        ti = time.time()

        retval = f(*_args)

        tf = time.time()
        execution_time = tf - ti

        job_id = args[0]

        calc_obj = Calculation.objects.get(pk=job_id)
        calc_obj.execution_time = int(execution_time)
        calc_obj.date_finished = timezone.now()

        if retval == 0:
            calc_obj.status = 2
        else:
            calc_obj.status = 3
            calc_obj.error_message = "Unknown error"

        calc_obj.save()

        author = calc_obj.author
        author.calculation_time_used += execution_time
        author.save()

    def setUp(self):
        self.user = create_user("test")

        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)
        if not os.path.isdir(RESULTS_DIR):
            os.mkdir(RESULTS_DIR)

        self.project = create_project(self.user, "TestProject")

    def tearDown(self):
        if os.path.isdir(SCR_DIR):
            rmtree(SCR_DIR)
        if os.path.isdir(RESULTS_DIR):
            rmtree(RESULTS_DIR)

def gen_test(in_file, type, solvent):
    def test(self):
        c = create_calculation(in_file, type, solvent, self.user, self.project)

        self.run_calc(FUNCTIONS[type], [c.id, False, c.charge, solvent])

        id = str(c.id)
        obj = Calculation.objects.get(pk=c.id)

        self.assertEqual(obj.status, 2)

        calc_path = os.path.join(SCR_DIR, id)

        if type == 0:
            self.assertTrue(os.path.isfile(os.path.join(calc_path, "xtbopt.xyz")))
            with open(os.path.join(calc_path, "xtb_opt.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("normal termination of xtb"))
        elif type == 1:
            self.assertTrue(os.path.isfile(os.path.join(calc_path, "xtbopt.xyz")))
            with open(os.path.join(calc_path, "xtb_opt.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("normal termination of xtb"))

            with open(os.path.join(calc_path, "crest.out")) as f:
                lines = f.readlines()
            self.assertTrue(lines[-1].find("CREST terminated normally."))

    return test


input_files = glob.glob(tests_dir + '*.*')

TYPES = [0, 1, 2, 3]

for type in TYPES:
    solvent = "Vacuum"
    for f in input_files:
        in_name = f.split('.')[0].split('/')[-1]
        test_name = "test_{}_{}_{}".format(in_name, type, solvent)
        test = gen_test(f, type, solvent)
        setattr(JobTestCase, test_name, test)

for solv in SOLVENTS:
    for f in [input_files[i] for i in [0, 4, 6]]:
        for type in TYPES:
            in_name = f.split('.')[0].split('/')[-1]
            test_name = "test_{}_{}_{}".format(in_name, type, solv)
            test = gen_test(f, type, solvent)
            setattr(JobTestCase, test_name, test)

