import os
from unittest import mock
from shutil import copyfile, rmtree

from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.core.management import call_command

from frontend import tasks
from .libxyz import *
from .models import *
from .gen_calc import gen_calc
from .tasks import run_calc
from .calcusliveserver import SCR_DIR

base_cwd = os.getcwd()


class CalculationUnitTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patcher = mock.patch.dict(os.environ, {"CAN_USE_CACHED_LOGS": "true"})
        cls.patcher.start()

        super().setUpClass()

        if os.path.isdir(SCR_DIR):
            rmtree(SCR_DIR)

        os.mkdir(SCR_DIR)

    def setUp(self):
        os.chdir(base_cwd)
        call_command("init_static_obj")
        self.email = "TestRunner@test.com"
        self.password = "test1234"

        self.user = User.objects.create_user(
            email=self.email, password=self.password, is_PI=True
        )

        self.name_patcher = mock.patch.dict(os.environ, {"TEST_NAME": self.id()})
        self.name_patcher.start()

    def get_params(self, **modifications):
        params = self.params.copy()

        for k, v in modifications.items():
            params[k] = v

        return params

    def run_test(self, callback=None, **modifications):
        """
        Runs the calculation and then the callback (if any).
        Returns True if everything worked, otherwise it returns False or an error code value.
        """

        tasks.cache_ind = 1
        params = self.get_params(**modifications)

        calc = gen_calc(params, self.user)

        ret = run_calc(calc.id)

        calc.refresh_from_db()

        if ret.value != 0:
            print(f"Got return code {ret.value}")
            return False

        if calc.status != 2:
            print("Calculation did not succeed")
            return False

        if callback is not None:
            return callback(calc)

        return True

    def cb_has_n_conformers(self, num, calc):
        if calc.result_ensemble is None:
            print("The result ensemble is none")
            return False

        e_count = calc.result_ensemble.structure_set.count()
        if e_count != num:
            print(f"The result ensemble has {e_count} structures, not {num}")
            return False

        return True

    def cb_has_angle_value(self, ids, value, calc):
        for s in calc.result_ensemble.structure_set.all():
            s_xyz = parse_xyz_from_text(s.xyz_structure)
            ang = get_angle(s_xyz, *ids)
            if not np.isclose(ang, value, atol=0.5):
                print(f"Angle value of {ang:.2f} instead of around {value:.2f}")
                return False
        return True
