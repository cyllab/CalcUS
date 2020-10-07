from .models import *
from . import views
from django.core.management import call_command
from django.test import TestCase, Client
from selenium import webdriver
from .calcusliveserver import CalcusLiveServer
from django.utils import timezone

import time
from .gen_calc import gen_param
import numpy as np
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
HEADLESS = os.getenv("CALCUS_HEADLESS")

from selenium.webdriver.chrome.options import Options

QUERY_TEST_XYZ = """35
Coordinates from ORCA-job ts
  I   1.10901725873641     -0.19335422897867      0.43405561114859
  C   0.72782144657430      0.22620903564727      2.54427882769295
  C   1.78165415646289      0.57084336103740      3.37528522279340
  C   -0.55347656349682      0.12580065685604      3.06245689640777
  C   1.55284366717891      0.83215698176423      4.71589954265945
  H   2.77870672518020      0.63423319416400      2.96375385869013
  C   -0.78396956405419      0.39081899396176      4.40108880079175
  H   -1.37352562334067     -0.15486462009308      2.41581318961741
  C   0.26923664705149      0.74600015051871      5.22813427591057
  H   2.37601978744786      1.10486452508383      5.35948677023295
  H   -1.78504430994252      0.31601035416896      4.79966111443712
  H   0.08886993967869      0.95226375363773      6.27260922912737
  C   -0.59306125773240      0.98913483021393      0.00861013564154
  C   -1.57195748061853      0.49812106346434     -0.83169507912442
  C   -0.69700795120372      2.23741285911511      0.59128723526037
  C   -2.68431992297129      1.28016266022018     -1.09393055529298
  H   -1.45995894821250     -0.47292458756066     -1.28796193149396
  C   -1.81277778183486      3.01199462158488      0.32206764568905
  H   0.08019115781109      2.59983331108970      1.24733057135369
  C   -2.80531916894655      2.53412096332062     -0.51785051682385
  H   -3.45635192375183      0.90621102285775     -1.74945509207168
  H   -1.90159413286925      3.99192755571960      0.76654236665004
  H   -3.67314772699881      3.14167985916399     -0.72637933645406
  O   1.13663322303447     -0.13950207592589     -1.75954581903270
  C   1.17857755821059     -1.16183062122417     -2.60301970208987
  C   1.21633110507809     -2.49355781852546     -2.18497125734341
  C   1.16240994786418     -0.89641187032917     -3.97777382337666
  C   1.23938568907858     -3.52139733522460     -3.10672497476494
  H   1.23351303735773     -2.70312559494142     -1.12288345056817
  C   1.18428977670116     -1.93102239376485     -4.88982334856045
  H   1.13185699842348      0.13299649622072     -4.30248576339136
  C   1.22230238610331     -3.24891910759014     -4.46372084558581
  H   1.27039514914777     -4.54519153589471     -2.76054503805149
  H   1.17148951578029     -1.70600352245762     -5.94716445985449
  H   1.23996698307245     -4.05469093730037     -5.18243030022379"""

tests_dir = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")

class QueryTests(TestCase):
    def test_single(self):
        main_e = Ensemble.objects.create()
        for i in range(1000):
            s = Structure.objects.create(parent_ensemble=main_e, xyz_structure=QUERY_TEST_XYZ, number=i+1)

        st = time.time()
        s = main_e.structure_set.get(number=500)
        et = time.time()
        print("Elapsed time for getting 1 structure from 1000 structures ensemble with 1 ensemble: {}".format(et-st))

    def test_many(self):
        for j in range(100):
            e = Ensemble.objects.create()
            for i in range(1000):
                s = Structure.objects.create(parent_ensemble=e, xyz_structure=TEST_XYZ, number=i+1)

        st = time.time()
        main_e = Ensemble.objects.get(pk=50)
        s = main_e.structure_set.get(number=500)
        et = time.time()
        print("Elapsed time for getting 1 structure from 1000 structures ensemble with 100 ensembles: {}".format(et-st))


STRUCTURES_FILES = ['ethanol.xyz', 'benzene.xyz', 'CH4.xyz', 'Cl.xyz', 'H2.xyz', 'pentane.xyz', 'propane.xyz', 'small_ts.xyz', 'carbo_cation.xyz', 'I.xyz']

PARAMETERS = {
            0: {
                'type': 'Frequency Calculation',
                'software': 'ORCA',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                },
            1: {
                'type': 'Single-Point Energy',
                'software': 'Gaussian',
                'theory': 'HF',
                'basis_set': 'Def2-SVP',
                },
            2: {
                'type': 'TS Optimisation',
                'software': 'ORCA',
                'theory': 'HF',
                'basis_set': 'Def2-TZVP',
                },
            3: {
                'type': 'TS Optimisation',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M06-2X',
                'basis_set': 'Def2SVP',
                },
            4: {
                'type': 'Single-Point Energy',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'B3LYP',
                'basis_set': 'Def2SVP',
                },
            5: {
                'type': 'Geometrical Optimisation',
                'software': 'ORCA',
                'theory': 'Semi-empirical',
                'method': 'AM1',
                },
            6: {
                'type': 'Geometrical Optimisation',
                'software': 'xtb',
                },
            7: {
                'type': 'Geometrical Optimisation',
                'software': 'ORCA',
                'theory': 'RI-MP2',
                'basis_set': 'cc-pVDZ',
                'additional_command': 'cc-pVDZ/C',
                },
            8: {
                'type': 'Geometrical Optimisation',
                'software': 'Gaussian',
                'theory': 'DFT',
                'functional': 'M06',
                'basis_set': 'Def2TZVP',
                },
            9: {
                'type': 'Single-Point Energy',
                'software': 'ORCA',
                'theory': 'DFT',
                'functional': 'M06',
                'basis_set': 'Def2TZVP',
                },
}

ENERGIES = [-5.0, -10.0, -50.0, -60.0, -200.0, -500.0, -750.0, -1000.0, -1200.0, -2000.0]
FREE_ENERGIES = [-2.0, -8.0, -40.0, -50.0, -100.0, -700.0, -800.0, -1100.0, -1300.0, -2200.0]
VARIATIONS = [0.05, 0.02, 0.1, 0.001, 0.3, 0.23, 0.324, 0.48, 0.60, 0.80]

class PageLoadingTests(CalcusLiveServer):

    def setUp(self):
        call_command('init_static_obj')
        self.username = "Tester"
        self.password = "test1234"

        u = User.objects.create_superuser(username=self.username, password=self.password)
        u.profile.is_PI = True
        u.save()
        self.profile = Profile.objects.get(user__username=self.username)

        self.group = ResearchGroup.objects.create(name="Test group", PI=self.profile)
        self.group.save()

        for i in range(5):
            u = User.objects.create(username="TestUser{}".format(i), password=self.password)
            u.save()
            p = Profile.objects.get(user=u)
            p.member_of = self.group
            p.save()

        #for i in range(5):
        for i in range(1):
            proj = Project.objects.create(name="TestProject{}".format(i), author=self.profile)
            proj.save()
            #for j in range(10):
            for j in range(5):
                mol = Molecule.objects.create(name="TestMolecule{}".format(j), inchi=str(10*i+j), project=proj)
                mol.save()
                #for k in range(10):
                for k in range(5):
                    e = Ensemble.objects.create(name="TestEnsemble{}".format(k), parent_molecule=mol)
                    e.save()

                    s_file = STRUCTURES_FILES[j]
                    params = PARAMETERS[k]
                    params['in_file'] = s_file
                    p = gen_param(params)
                    o = CalculationOrder.objects.create(parameters=p, project=proj, author=self.profile)
                    for l in range(5):
                        s = Structure.objects.create(parent_ensemble=e, number=l+1, xyz_structure=self.get_xyz(s_file))
                        s.save()
                        calc = self.gen_calc(e, params, o)
                        calc.status = self.get_status(i, j, k, l)
                        calc.date = timezone.now()
                        calc.save()
                        prop = Property.objects.create(parent_structure=s, energy=self.get_energy(j, l), free_energy=self.get_free_energy(j, l), parameters=calc.parameters)
                        prop.save()
        self.login(self.username, self.password)
        print("Startup complete")

    def gen_calc(self, e, params, order):
        step = BasicStep.objects.get(name=params['type'])

        p = gen_param(params)

        with open(os.path.join(tests_dir, params['in_file'])) as f:
            lines = f.readlines()
            xyz_structure = ''.join(lines)

        s = Structure.objects.create(xyz_structure=xyz_structure, parent_ensemble=e)

        calc = Calculation.objects.create(structure=s, step=step, parameters=p, order=order)

        if 'constraints' in params.keys():
            calc.constraints = params['constraints']

        return calc

    def get_status(self, i, j, k, l):
        return i*j*k*l % 4

    def get_energy(self, j, l):
        return ENERGIES[j] + VARIATIONS[l]

    def get_free_energy(self, j, l):
        return FREE_ENERGIES[j] + VARIATIONS[l]

    def get_xyz(self, name):
        with open(os.path.join(tests_dir, name)) as f:
            xyz = ''.join(f.readlines())
        return xyz

    def get_time_to_url(self, url):
        ti = time.time()
        self.driver.get('{}{}'.format(self.live_server_url, url))
        self.wait_for_ajax()
        tf = time.time()
        return tf-ti

    def benchmark_url(self, url):
        times = []
        for i in range(50):
            times.append(self.get_time_to_url(url))
        return np.mean(times), np.std(times)

    def test_page_loading_time(self):
        print("Home: {:.5f} ± {:.5f}".format(*self.benchmark_url("/home/")))
        print("Projects: {:.5f} ± {:.5f}".format(*self.benchmark_url("/projects/")))
        print("Project X: {:.5f} ± {:.5f}".format(*self.benchmark_url("/projects/{}/{}/".format(self.profile.user.username, Project.objects.first().name))))
        print("Calculations: {:.5f} ± {:.5f}".format(*self.benchmark_url("/calculations/")))
        print("Analysis: {:.5f} ± {:.5f}".format(*self.benchmark_url("/analyse/{}".format(Project.objects.first().id))))

