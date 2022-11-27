"""
This file of part of CalcUS.

Copyright (C) 2020-2022 Raphaël Robidas

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""


import os
import time
import sys
import glob
import selenium
import datetime
from unittest import mock
from shutil import copyfile, rmtree

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys

from django.core.management import call_command
from django.contrib.auth.models import User, Group
from django.conf import settings

from .models import *
from .libxyz import *
from .calcusliveserver import CalcusCloudLiveServer, SCR_DIR, tests_dir


class XtbCalculationTests(CalcusCloudLiveServer):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.user)
        g.save()
        self.user.allocated_seconds = 100
        self.user.save()

    def test_opt(self):
        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
        }

        self.assertEqual(self.user.billed_seconds, 0)

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

        self.user.refresh_from_db()
        self.assertNotEqual(self.user.billed_seconds, 0)

    def test_sp(self):
        params = {
            "mol_name": "my_mol",
            "type": "Single-Point Energy",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_proj(self):
        proj = Project.objects.create(author=self.user, name="TestProj")
        proj.save()

        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "TestProj",
            "in_file": "CH4.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_freq(self):
        params = {
            "mol_name": "my_mol",
            "type": "Frequency Calculation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "carbo_cation.mol",
            "charge": "1",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()

    def test_freq_solv_GBSA(self):
        params = {
            "mol_name": "my_mol",
            "type": "Frequency Calculation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "carbo_cation.mol",
            "charge": "1",
            "solvent": "Chloroform",
            "solvation_model": "GBSA",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()

    def test_freq_solv_ALPB(self):
        params = {
            "mol_name": "my_mol",
            "type": "Frequency Calculation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "carbo_cation.mol",
            "charge": "1",
            "solvent": "Chloroform",
            "solvation_model": "ALPB",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()

    def test_conf_search(self):
        params = {
            "mol_name": "my_mol",
            "type": "Conformational Search",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "ethanol.sdf",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

    def test_conf_search_gfnff(self):
        params = {
            "mol_name": "my_mol",
            "type": "Conformational Search",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "ethanol.sdf",
            "specifications": "--gfnff",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

    def test_conf_search_invalid_specification(self):
        params = {
            "mol_name": "my_mol",
            "type": "Conformational Search",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "ethanol.sdf",
            "specifications": "--gfn2-ff",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertFalse(self.latest_calc_successful())

    def test_conf_search_gfnff_sp(self):
        params = {
            "mol_name": "my_mol",
            "type": "Conformational Search",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "ethanol.sdf",
            "specifications": "--gfn2//gfnff",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(120)
        self.assertTrue(self.latest_calc_successful())

    """
    # ORCA does not support initial Hessian calculations on TS optimization with xtb specifically
    def test_ts(self):
        params = {
            "mol_name": "my_mol",
            "type": "TS Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "ts.xyz",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())
    """

    def test_scan_distance(self):
        params = {
            "mol_name": "my_mol",
            "type": "Constrained Optimisation",
            "constraints": [["Scan", "Distance", [1, 2], [1.5, 2.0, 10]]],
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_scan_angle(self):
        params = {
            "mol_name": "my_mol",
            "type": "Constrained Optimisation",
            "constraints": [["Scan", "Angle", [1, 2, 3], [120, 130, 10]]],
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_scan_dihedral(self):
        params = {
            "mol_name": "my_mol",
            "type": "Constrained Optimisation",
            "constraints": [["Scan", "Dihedral", [1, 2, 3, 4], [0, 10, 10]]],
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 10)

    def test_freeze_distance(self):
        params = {
            "mol_name": "my_mol",
            "type": "Constrained Optimisation",
            "constraints": [["Freeze", "Distance", [1, 4]]],
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.wait_for_ajax()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_distance2(self):
        params = {
            "mol_name": "my_mol",
            "type": "Constrained Optimisation",
            "constraints": [
                ["Freeze", "Distance", [1, 4]],
                ["Freeze", "Distance", [2, 3]],
            ],
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.wait_for_ajax()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_angle(self):
        params = {
            "mol_name": "my_mol",
            "type": "Constrained Optimisation",
            "constraints": [["Freeze", "Angle", [1, 2, 3]]],
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_freeze_dihedral(self):
        params = {
            "mol_name": "my_mol",
            "type": "Constrained Optimisation",
            "constraints": [["Freeze", "Dihedral", [1, 2, 3, 4]]],
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(150)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_ensemble_second_step(self):
        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "carbo_cation.xyz",
            "charge": "1",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.launch_ensemble_next_step()

        params2 = {
            "type": "Frequency Calculation",
            # project and charge implicit
        }
        self.calc_input_params(params2)

        charge = self.driver.find_element(By.NAME, "calc_charge")
        self.assertEqual(charge.get_attribute("value"), params["charge"])

        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_ensemble_second_step_mult(self):
        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "enolate_anion.mol",
            "charge": "0",
            "multiplicity": "2",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.launch_ensemble_next_step()

        params2 = {
            "type": "Frequency Calculation",
            # project and multiplicity implicit
        }
        self.calc_input_params(params2)

        mult = self.driver.find_element(By.NAME, "calc_multiplicity")
        self.assertEqual(mult.get_attribute("value"), params["multiplicity"])

    def test_structure_second_step(self):
        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "carbo_cation.xyz",
            "charge": "1",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.launch_structure_next_step()

        params2 = {
            "type": "Frequency Calculation",
            # project and charge implicit
        }

        charge = self.driver.find_element(By.NAME, "calc_charge")
        self.assertEqual(charge.get_attribute("value"), params["charge"])

        self.calc_input_params(params2)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

    def test_multiple_structures_second_step(self):
        in_files = [f"batch/benzene{i:02d}.xyz" for i in range(1, 5)]
        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_files": in_files,
            "combine": True,
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(100)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()

        self.select_conformers([2, 3])

        self.launch_structure_next_step()

        params2 = {
            "type": "Single-Point Energy",
        }

        self.calc_input_params(params2)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(100)

        self.details_latest_order()
        num = self.get_number_calc_in_order()
        self.assertEqual(num, 2)

        order = CalculationOrder.objects.latest("id")
        calcs = order.calculation_set.all()
        self.assertIn(calcs[0].structure.number, [2, 3])
        self.assertIn(calcs[1].structure.number, [2, 3])
        self.assertNotEqual(calcs[0].structure.number, calcs[1].structure.number)

    """
    def test_NEB_from_file(self):
        params = {
            "mol_name": "my_mol",
            "type": "Minimum Energy Path",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "software": "xtb",
            "in_file": "elimination_substrate.xyz",
            "aux_file": "elimination_product.xyz",
            "charge": "-1",
            "specifications": "--nimages 3",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 5)

    def test_NEB_from_structure(self):
        params = {
            "mol_name": "elimination_substrate",
            "name": "start",
            "type": "Constrained Optimisation",
            "constraints": [["Scan", "Distance", [1, 4], [1.1, 3.5, 10]]],
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "software": "xtb",
            "in_file": "elimination_substrate.xyz",
            "charge": "-1",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.launch_structure_next_step()

        params = {
            "name": "my_ensemble",
            "type": "Minimum Energy Path",
            "project": "SeleniumProject",
            "software": "xtb",
            "aux_structure": ["elimination_substrate", "elimination_substrate", 4],
            "specifications": "--nimages 3",
        }

        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())

    def test_NEB_hybrid(self):
        params = {
            "mol_name": "elimination_substrate",
            "type": "Constrained Optimisation",
            "constraints": [["Scan", "Distance", [1, 4], [1.1, 3.5, 10]]],
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "software": "xtb",
            "in_file": "elimination_substrate.xyz",
            "charge": "-1",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())

        self.lget("/launch/")
        params = {
            "name": "my_ensemble",
            "type": "Minimum Energy Path",
            "project": "SeleniumProject",
            "software": "xtb",
            "aux_structure": ["elimination_substrate", "elimination_substrate", 4],
            "in_file": "elimination_substrate.xyz",
            "specifications": "--nimages 3",
            "charge": "-1",
        }

        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())
    """

    def test_constrained_conf_search(self):
        params = {
            "mol_name": "my_mol",
            "type": "Constrained Conformational Search",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "pentane.mol",
            "constraints": [["Freeze", "Angle", [1, 5, 8]]],
        }

        self.lget("/launch/")

        xyz = parse_xyz_from_file(os.path.join(tests_dir, "pentane.xyz"))
        ang0 = get_angle(xyz, 1, 5, 8)

        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(1200)
        self.assertTrue(self.latest_calc_successful())

        e = Ensemble.objects.latest("id")
        for s in e.structure_set.all():
            s_xyz = parse_xyz_from_text(s.xyz_structure)
            ang = get_angle(xyz, 1, 5, 8)
            self.assertTrue(np.isclose(ang, ang0, atol=0.5))

    @mock.patch.dict(os.environ, {"CACHE_POST_WAIT": "15"})
    def test_parse_cancelled_calc(self):
        params = {
            "mol_name": "my_mol",
            "type": "Constrained Optimisation",
            "constraints": [["Scan", "Angle", [5, 2, 13], [90, 180, 200]]],
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "Ph2I_cation.mol",
            "charge": "1",
        }

        self.assertEqual(self.user.billed_seconds, 0)

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_running(5)
        time.sleep(5)
        self.details_latest_order()
        self.cancel_all_calc()

        self.lget("/calculations/")
        self.wait_latest_calc_error(10)
        time.sleep(5)

        self.click_latest_calc()
        self.wait_for_ajax()
        self.assertGreaterEqual(self.get_number_conformers(), 1)

        self.user.refresh_from_db()
        self.assertNotEqual(self.user.billed_seconds, 0)

    def test_default_settings_from_ensemble(self):
        params = {
            "mol_name": "my_mol",
            "in_file": "Ph2I_cation.xyz",
            "software": "xtb",
            "type": "Geometrical Optimisation",
            "charge": "1",
            "solvent": "dcm",
            "solvation_model": "GBSA",
            "project": "New Project",
            "new_project_name": "Proj",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()

        self.lget("/calculations")
        self.wait_latest_calc_done(120)
        self.click_latest_calc()

        self.launch_ensemble_next_step()

        solvent = self.driver.find_element(By.NAME, "calc_solvent")
        charge = self.driver.find_element(By.NAME, "calc_charge")
        solvation_model = Select(
            self.driver.find_element(By.NAME, "calc_solvation_model")
        )
        software = self.driver.find_element(By.ID, "calc_software")

        self.assertEqual(solvent.get_attribute("value"), params["solvent"])
        self.assertEqual(charge.get_attribute("value"), params["charge"])
        self.assertEqual(
            solvation_model.first_selected_option.text, params["solvation_model"]
        )
        self.assertEqual(software.get_attribute("value"), params["software"])

    def test_default_settings_from_structure(self):
        params = {
            "mol_name": "my_mol",
            "in_file": "Ph2I_cation.xyz",
            "software": "xtb",
            "type": "Geometrical Optimisation",
            "charge": "1",
            "solvent": "dcm",
            "solvation_model": "GBSA",
            "project": "New Project",
            "new_project_name": "Proj",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()

        self.lget("/calculations")
        self.wait_latest_calc_done(120)
        self.click_latest_calc()

        self.launch_structure_next_step()

        solvent = self.driver.find_element(By.NAME, "calc_solvent")
        charge = self.driver.find_element(By.NAME, "calc_charge")
        solvation_model = Select(
            self.driver.find_element(By.NAME, "calc_solvation_model")
        )
        software = self.driver.find_element(By.ID, "calc_software")

        self.assertEqual(solvent.get_attribute("value"), params["solvent"])
        self.assertEqual(charge.get_attribute("value"), params["charge"])
        self.assertEqual(
            solvation_model.first_selected_option.text, params["solvation_model"]
        )
        self.assertEqual(software.get_attribute("value"), params["software"])

    def test_default_settings_from_frame(self):
        params = {
            "mol_name": "my_mol",
            "in_file": "Ph2I_cation.xyz",
            "software": "xtb",
            "type": "Geometrical Optimisation",
            "charge": "1",
            "solvent": "dcm",
            "solvation_model": "GBSA",
            "project": "New Project",
            "new_project_name": "Proj",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()

        self.lget("/calculations")
        self.wait_latest_calc_done(120)
        self.details_latest_order()
        self.details_first_calc()
        self.launch_frame_next_step()

        solvent = self.driver.find_element(By.NAME, "calc_solvent")
        charge = self.driver.find_element(By.NAME, "calc_charge")
        solvation_model = Select(
            self.driver.find_element(By.NAME, "calc_solvation_model")
        )
        software = self.driver.find_element(By.ID, "calc_software")

        self.assertEqual(solvent.get_attribute("value"), params["solvent"])
        self.assertEqual(charge.get_attribute("value"), params["charge"])
        self.assertEqual(
            solvation_model.first_selected_option.text, params["solvation_model"]
        )
        self.assertEqual(software.get_attribute("value"), params["software"])


class StudentTests(CalcusCloudLiveServer):
    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.user)

        self.student = User.objects.create_user(
            email="Student@uni.com", password=self.password
        )
        self.student.member_of = g
        self.student.save()

        self.login("Student@uni.com", self.password)

    def test_opt(self):
        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
        self.click_latest_calc()
        self.assertEqual(self.get_number_conformers(), 1)

    def test_proj(self):
        proj = Project.objects.create(author=self.student, name="TestProj")
        proj.save()

        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "TestProj",
            "in_file": "CH4.mol",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())
