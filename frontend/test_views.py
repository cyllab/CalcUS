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


import json
import time
import os
import copy
from shutil import copyfile, rmtree

from django.core.management import call_command
from django.contrib.auth import authenticate
from django.test import TestCase, Client
from django.http import HttpRequest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from .gen_calc import gen_calc, gen_param
from .calcusliveserver import SCR_DIR
from .constants import *
from .models import *
from . import views

tests_dir = os.path.join("/".join(__file__.split("/")[:-1]), "tests/")

basic_params = {
    "file_structure": [""],
    "calc_combine_files": [""],
    "calc_parse_filenames": [""],
    "calc_mol_name": ["Test"],
    "calc_name": ["Test"],
    "calc_solvent": ["Vacuum"],
    "calc_charge": ["0"],
    "calc_multiplicity": ["1"],
    "calc_project": ["New Project"],
    "new_project_name": ["Test"],
    "calc_software": ["xtb"],
    "calc_theory_level": [""],
    "calc_type": ["Geometrical Optimisation"],
    "constraint_mode_1": ["Freeze"],
    "constraint_type_1": ["Distance"],
    "calc_constraint_1_1": [""],
    "calc_constraint_1_2": [""],
    "calc_constraint_1_3": [""],
    "calc_constraint_1_4": [""],
    "calc_scan_1_1": [""],
    "calc_scan_1_2": [""],
    "calc_scan_1_3": [""],
    "calc_resource": ["Local"],
    "constraint_num": ["1"],
    "structure": [
        "Molecule from ChemDoodle Web Components\r\n\r\nhttp://www.ichemlabs.com\r\n  6  6  0  0  0  0            999 V2000\r\n    0.0000    1.0000    0.0000 C   0  0  0  0  0  0\r\n    0.8660    0.5000    0.0000 C   0  0  0  0  0  0\r\n    0.8660   -0.5000    0.0000 C   0  0  0  0  0  0\r\n    0.0000   -1.0000    0.0000 C   0  0  0  0  0  0\r\n   -0.8660   -0.5000    0.0000 C   0  0  0  0  0  0\r\n   -0.8660    0.5000    0.0000 C   0  0  0  0  0  0\r\n  1  2  1  0  0  0  0\r\n  2  3  2  0  0  0  0\r\n  3  4  1  0  0  0  0\r\n  4  5  2  0  0  0  0\r\n  5  6  1  0  0  0  0\r\n  6  1  2  0  0  0  0\r\nM  END"
    ],
    "test": ["true"],
}

basic_flowchart_params = {
    "calc_solvent": ["Vacuum"],
    "calc_charge": ["0"],
    "calc_multiplicity": ["1"],
    "calc_software": ["xtb"],
    "calc_theory_level": [""],
    "calc_type": ["Geometrical Optimisation"],
    "constraint_mode_1": ["Freeze"],
    "constraint_type_1": ["Distance"],
    "calc_constraint_1_1": [""],
    "calc_constraint_1_2": [""],
    "calc_constraint_1_3": [""],
    "calc_constraint_1_4": [""],
    "calc_scan_1_1": [""],
    "calc_scan_1_2": [""],
    "calc_scan_1_3": [""],
    "calc_resource": ["Local"],
}
LARGE_DRAWING = """Molecule from ChemDoodle Web Components

http://www.ichemlabs.com
 15 17  0  0  0  0            999 V2000
   -1.7321    0.2500    0.0000 C   0  0  0  0  0  0
   -0.8660   -0.2500    0.0000 C   0  0  0  0  0  0
   -2.5981   -0.2500    0.0000 C   0  0  0  0  0  0
   -1.7321    1.2500    0.0000 C   0  0  0  0  0  0
   -0.8660   -1.2500    0.0000 C   0  0  0  0  0  0
    0.0000    0.2500    0.0000 C   0  0  0  0  0  0
   -2.5981   -1.2500    0.0000 C   0  0  0  0  0  0
   -0.8660    1.7500    0.0000 C   0  0  0  0  0  0
   -1.7321   -1.7500    0.0000 C   0  0  0  0  0  0
    0.0000    1.2500    0.0000 C   0  0  0  0  0  0
    0.8660   -0.2500    0.0000 C   0  0  0  0  0  0
    0.8660    1.7500    0.0000 C   0  0  0  0  0  0
    1.7321    0.2500    0.0000 C   0  0  0  0  0  0
    1.7321    1.2500    0.0000 C   0  0  0  0  0  0
    2.5981   -0.2500    0.0000 C   0  0  0  0  0  0
  1  2  1  0  0  0  0
  3  1  2  0  0  0  0
  1  4  1  0  0  0  0
  2  5  2  0  0  0  0
  6  2  1  0  0  0  0
  7  3  1  0  0  0  0
  4  8  2  0  0  0  0
  5  9  1  0  0  0  0
 10  6  2  0  0  0  0
 11  6  1  0  0  0  0
  9  7  2  0  0  0  0
  8 10  1  0  0  0  0
 10 12  1  0  0  0  0
 13 11  1  0  0  0  0
 12 14  1  0  0  0  0
 14 13  2  0  0  0  0
 15 13  1  0  0  0  0
M  END
"""


class CalculationLaunchTests(TestCase):
    def setUp(self):
        call_command("init_static_obj")
        self.email = "Tester@test.com"
        self.password = "test1234"

        self.user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
        )
        self.group = ResearchGroup.objects.create(name="Test group", PI=self.user)
        self.client = Client()
        self.client.force_login(self.user)

    def tearDown(self):
        pass

    def test_get_launch_page(self):
        response = self.client.get("/launch/", follow=True)
        assert (
            response.content.decode("utf-8").find("Please login to see this page") == -1
        )
        self.assertEqual(response.status_code, 200)

    def test_submit_empty(self):
        response = self.client.post("/submit_calculation", data={}, follow=True)
        assert (
            response.content.decode("utf-8").find("Please login to see this page") == -1
        )
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_correct(self):
        response = self.client.post(
            "/submit_calculation/", data=basic_params, follow=True
        )
        self.assertNotContains(response, "Error while submitting your calculation")

    def test_submit_long_name(self):
        params = basic_params.copy()
        params["calc_name"] = "A" * 200
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_long_project_name(self):
        params = basic_params.copy()
        params["calc_project"] = "A" * 200
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_mol_name(self):
        params = basic_params.copy()
        params["calc_mol_name"] = ""
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_charge(self):
        params = basic_params.copy()
        params["calc_charge"] = ""
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_project(self):
        params = basic_params.copy()
        params["calc_project"] = ""
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_software(self):
        params = basic_params.copy()
        params["calc_software"] = ""
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_type(self):
        params = basic_params.copy()
        params["calc_type"] = ""
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_empty_resource(self):
        params = basic_params.copy()
        params["calc_resource"] = ""
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_mol_name(self):
        params = basic_params.copy()
        del params["calc_mol_name"]
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_charge(self):
        params = basic_params.copy()
        del params["calc_charge"]
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_project(self):
        params = basic_params.copy()
        del params["calc_project"]
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_software(self):
        params = basic_params.copy()
        del params["calc_software"]
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_type(self):
        params = basic_params.copy()
        del params["calc_type"]
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_no_resource(self):
        params = basic_params.copy()
        del params["calc_resource"]
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_no_theory(self):
        params = basic_params.copy()
        params["calc_software"] = "ORCA"
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_gaussian_valid_specification(self):
        params = basic_params.copy()
        params["calc_software"] = "Gaussian"
        params["specifications"] = "opt(loose)"
        params["calc_theory_level"] = "DFT"
        params["calc_functional"] = "M06-2X"
        params["calc_basis_set"] = "Def2-SVP"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertNotContains(response, "Error while submitting your calculation")

    def test_constrained_opt_no_constraint(self):
        params = basic_params.copy()
        params["calc_type"] = "Constrained Optimisation"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_empty_theory(self):
        params = basic_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = ""
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_DFT_no_functional(self):
        params = basic_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "DFT"
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_DFT_no_basis_set(self):
        params = basic_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "DFT"
        params["calc_functional"] = "M06-2X"
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_DFT_empty_functional(self):
        params = basic_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "DFT"
        params["calc_functional"] = ""
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_DFT_correct(self):
        params = basic_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "DFT"
        params["calc_functional"] = "M06-2X"
        params["calc_basis_set"] = "Def2-SVP"
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertNotContains(response, "Error while submitting your calculation")

    def test_submit_ORCA_DFT_empty_basis_set(self):
        params = basic_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "DFT"
        params["calc_functional"] = "M06-2X"
        params["calc_basis_set"] = ""
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_clean_name1(self):
        params = basic_params.copy()
        params["calc_mol_name"] = "name"
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertNotContains(response, "Error while submitting your calculation")

        o = CalculationOrder.objects.latest("id")
        self.assertEqual(o.ensemble.parent_molecule.name, "name")

    def test_clean_name2(self):
        params = basic_params.copy()
        params["calc_mol_name"] = "<br>name"
        response = self.client.post("/submit_calculation/", data=params, follow=True)

        self.assertNotContains(response, "Error while submitting your calculation")
        o = CalculationOrder.objects.latest("id")
        self.assertEqual(o.ensemble.parent_molecule.name, "&lt;br&gt;name")

    def test_clean_name3(self):
        params = basic_params.copy()
        params["calc_mol_name"] = "name/details-."
        response = self.client.post("/submit_calculation/", data=params, follow=True)

        self.assertNotContains(response, "Error while submitting your calculation")
        o = CalculationOrder.objects.latest("id")
        self.assertEqual(o.ensemble.parent_molecule.name, "name/details-.")


"""
class FlowchartLaunchTests(TestCase):
    def setUp(self):
        call_command("init_static_obj")
        self.email = "Tester@test.com"
        self.password = "test1234"

        self.user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
        )
        self.group = ResearchGroup.objects.create(name="Test group", PI=self.user)
        self.client = Client()
        self.client.force_login(self.user)

    def test_verify_correct_flowchart(self):
        response = self.client.post(
            "/verify_flowchart_calculation/", data=basic_flowchart_params, follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_verify_no_calc_type(self):
        params = basic_flowchart_params.copy()
        del params["calc_type"]
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_calc_type_name(self):
        params = basic_flowchart_params.copy()
        params["calc_type"] = "Not a calculation name"
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_no_calc_charge(self):
        params = basic_flowchart_params.copy()
        del params["calc_charge"]
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_calc_charge(self):
        params = basic_flowchart_params.copy()
        params["calc_charge"] = "1.1"
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_no_calc_multiplicity(self):
        params = basic_flowchart_params.copy()
        del params["calc_multiplicity"]
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_calc_multiplicity_1(self):
        params = basic_flowchart_params.copy()
        params["calc_multiplicity"] = "1.1"
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_calc_multiplicity_2(self):
        params = basic_flowchart_params.copy()
        params["calc_multiplicity"] = "-1"
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_calc_solvent_vacuum(self):
        params = basic_flowchart_params.copy()
        params["calc_solvent"] = "Vacuum"
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_verify_no_calc_software(self):
        params = basic_flowchart_params.copy()
        del params["calc_software"]
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_empty_calc_software(self):
        params = basic_flowchart_params.copy()
        params["calc_software"] = ""
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_ORCA_no_theory(self):
        params = basic_flowchart_params.copy()
        params["calc_software"] = "ORCA"
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_gaussian_valid_specification(self):
        params = basic_flowchart_params.copy()
        params["calc_software"] = "Gaussian"
        params["specifications"] = "opt(loose)"
        params["calc_theory_level"] = "DFT"
        params["calc_functional"] = "M06-2X"
        params["calc_basis_set"] = "Def2-SVP"

        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_verify_constrained_opt_no_constraint(self):
        params = basic_flowchart_params.copy()
        params["calc_type"] = "Constrained Optimisation"

        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_verify_ORCA_empty_theory(self):
        params = basic_flowchart_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = ""
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_ORCA_DFT_no_functional(self):
        params = basic_flowchart_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "DFT"
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_ORCA_DFT_no_basis_set(self):
        params = basic_flowchart_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "DFT"
        params["calc_functional"] = "M06-2X"
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_ORCA_DFT_empty_functional(self):
        params = basic_flowchart_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "DFT"
        params["calc_functional"] = ""
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_ORCA_DFT_correct(self):
        params = basic_flowchart_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "DFT"
        params["calc_functional"] = "M06-2X"
        params["calc_basis_set"] = "Def2-SVP"
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_verify_ORCA_DFT_empty_basis_set(self):
        params = basic_flowchart_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "DFT"
        params["calc_functional"] = "M06-2X"
        params["calc_basis_set"] = ""
        response = self.client.post(
            "/verify_flowchart_calculation/", data=params, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_create_flowchart(self):
        flowchart_data = {}
        flowchart_data["flowchart_name"] = "Test Name"
        flowchart_data["flowchart_data"] = "Sample Data"
        calc_name_list = ["Constrained Optimisation", "Geometrical Optimisation"]
        flowchart_data["calc_name[]"] = calc_name_list
        calc_id = ["0", "1"]
        flowchart_data["calc_id[]"] = calc_id
        calc_parent_id = ["-1", "0"]
        flowchart_data["calc_parent_id[]"] = calc_parent_id
        calc_para_list = [None, None]
        para_json = json.dumps(calc_para_list)
        flowchart_data["calc_para_array"] = para_json
        response = self.client.post(
            "/create_flowchart/", data=flowchart_data, follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_load_flowchart_params(self):
        flowchart_data = {}
        flowchart_data["flowchart_name"] = "Test Name"
        flowchart_data["flowchart_data"] = "Sample Data"
        calc_name_list = ["", "Geometrical Optimisation"]
        flowchart_data["calc_name[]"] = calc_name_list
        calc_id = ["0", "1"]
        flowchart_data["calc_id[]"] = calc_id
        calc_parent_id = ["-1", "0"]
        flowchart_data["calc_parent_id[]"] = calc_parent_id
        para_list = []
        params = basic_flowchart_params.copy()
        params["para_calc_id"] = ["1"]
        for i in params:
            temp_dict = {}
            temp_dict["name"] = i
            temp_dict["value"] = params[i][0]
            para_list.append(temp_dict)
        print(para_list)
        calc_para_list = [None, para_list]
        para_json = json.dumps(calc_para_list)
        flowchart_data["calc_para_array"] = para_json
        response_1 = self.client.post(
            "/create_flowchart/", data=flowchart_data, follow=True
        )
        for i in Flowchart.objects.all():
            response_2 = self.client.post(f"/load_flowchart_params/{i.id}")
            self.assertEqual(response_2.status_code, 200)
"""


class FileInputTests(TestCase):
    def setUp(self):
        call_command("init_static_obj")
        self.email = "Tester@test.com"
        self.password = "test1234"

        self.user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
        )
        self.group = ResearchGroup.objects.create(name="Test group", PI=self.user)
        self.client = Client()
        self.client.force_login(self.user)

    def test_single_file(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz = bytes(f.read(), "UTF-8")

        f = SimpleUploadedFile("Cl.xyz", xyz, content_type="chemical/x-xyz")

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "-1"
        params["file_structure"] = [f]
        params["calc_combine_files"] = ("",)
        params["calc_parse_filenames"] = ""

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 1)
        self.assertEqual(Molecule.objects.count(), 1)
        self.assertEqual(Ensemble.objects.count(), 1)

    def test_parse_charge_no_filename(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz = bytes(f.read(), "UTF-8")

        f = SimpleUploadedFile("Cl.xyz", xyz, content_type="chemical/x-xyz")

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "0"
        params["file_structure"] = [f]
        params["calc_combine_files"] = ("",)
        params["calc_parse_filenames"] = ""

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 0)
        self.assertEqual(Molecule.objects.count(), 0)
        self.assertEqual(Ensemble.objects.count(), 0)

    def test_parse_charge_filename(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz = bytes(f.read(), "UTF-8")

        f = SimpleUploadedFile("Cl_anion.xyz", xyz, content_type="chemical/x-xyz")
        f2 = SimpleUploadedFile("Cl_anion2.xyz", xyz, content_type="chemical/x-xyz")

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "0"
        params["file_structure"] = [f, f2]
        params["calc_combine_files"] = ("",)
        params["calc_parse_filenames"] = "on"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 2)
        self.assertEqual(Molecule.objects.count(), 2)
        self.assertEqual(Ensemble.objects.count(), 2)

    def test_parse_mult_filename(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz = bytes(f.read(), "UTF-8")

        f = SimpleUploadedFile("Cl_radical.xyz", xyz, content_type="chemical/x-xyz")
        f2 = SimpleUploadedFile("Cl_radical_2.xyz", xyz, content_type="chemical/x-xyz")

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "0"
        params["calc_multiplicity"] = "1"
        params["file_structure"] = [f, f2]
        params["calc_combine_files"] = ("",)
        params["calc_parse_filenames"] = "on"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 2)
        self.assertEqual(Molecule.objects.count(), 2)
        self.assertEqual(Ensemble.objects.count(), 2)

    def test_two_files(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz_a = bytes(f.read(), "UTF-8")
        with open(os.path.join(tests_dir, "I.xyz")) as f:
            xyz_b = bytes(f.read(), "UTF-8")

        f_a = SimpleUploadedFile("Cl.xyz", xyz_a, content_type="chemical/x-xyz")
        f_b = SimpleUploadedFile("I.xyz", xyz_b, content_type="chemical/x-xyz")

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "-1"
        params["file_structure"] = [f_a, f_b]
        params["calc_combine_files"] = ("",)
        params["calc_parse_filenames"] = ""

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 2)
        self.assertEqual(Molecule.objects.count(), 2)
        self.assertEqual(Ensemble.objects.count(), 2)

    def test_two_files_force_combine(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz_a = bytes(f.read(), "UTF-8")
        with open(os.path.join(tests_dir, "I.xyz")) as f:
            xyz_b = bytes(f.read(), "UTF-8")

        f_a = SimpleUploadedFile("Cl.xyz", xyz_a, content_type="chemical/x-xyz")
        f_b = SimpleUploadedFile("I.xyz", xyz_b, content_type="chemical/x-xyz")

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "-1"
        params["file_structure"] = [f_a, f_b]
        params["calc_combine_files"] = ("on",)
        params["calc_parse_filenames"] = ""

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 1)
        self.assertEqual(Molecule.objects.count(), 1)
        self.assertEqual(Ensemble.objects.count(), 1)

    def test_two_files_parse_names_different(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz_a = bytes(f.read(), "UTF-8")
        with open(os.path.join(tests_dir, "I.xyz")) as f:
            xyz_b = bytes(f.read(), "UTF-8")

        f_a = SimpleUploadedFile("Cl.xyz", xyz_a, content_type="chemical/x-xyz")
        f_b = SimpleUploadedFile("I.xyz", xyz_b, content_type="chemical/x-xyz")

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "-1"
        params["file_structure"] = [f_a, f_b]
        params["calc_combine_files"] = ("",)
        params["calc_parse_filenames"] = "on"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 2)
        self.assertEqual(Molecule.objects.count(), 2)
        self.assertEqual(Ensemble.objects.count(), 2)

    def test_two_files_parse_names_same(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz = bytes(f.read(), "UTF-8")

        f_a = SimpleUploadedFile("CH4_conf1.xyz", xyz, content_type="chemical/x-xyz")
        f_b = SimpleUploadedFile("CH4_conf2.xyz", xyz, content_type="chemical/x-xyz")

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "-1"
        params["file_structure"] = [f_a, f_b]
        params["calc_combine_files"] = ("",)
        params["calc_parse_filenames"] = "on"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 1)
        self.assertEqual(Molecule.objects.count(), 1)
        self.assertEqual(Ensemble.objects.count(), 1)

    def test_two_files_parse_names_same_with_period(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz = bytes(f.read(), "UTF-8")

        f_a = SimpleUploadedFile(
            "CH4.stuff_conf1.xyz", xyz, content_type="chemical/x-xyz"
        )
        f_b = SimpleUploadedFile(
            "CH4.stuff_conf2.xyz", xyz, content_type="chemical/x-xyz"
        )

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "-1"
        params["file_structure"] = [f_a, f_b]
        params["calc_combine_files"] = ("",)
        params["calc_parse_filenames"] = "on"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 1)
        self.assertEqual(Molecule.objects.count(), 1)
        self.assertEqual(Ensemble.objects.count(), 1)

    def test_two_files_parse_names_different_with_period(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz = bytes(f.read(), "UTF-8")

        f_a = SimpleUploadedFile(
            "CH4.stuff_conf1.xyz", xyz, content_type="chemical/x-xyz"
        )
        f_b = SimpleUploadedFile(
            "CH4.stoff_conf2.xyz", xyz, content_type="chemical/x-xyz"
        )

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "-1"
        params["file_structure"] = [f_a, f_b]
        params["calc_combine_files"] = ("",)
        params["calc_parse_filenames"] = "on"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 2)
        self.assertEqual(Molecule.objects.count(), 2)
        self.assertEqual(Ensemble.objects.count(), 2)

    def test_two_files_parse_names_different_with_period2(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz = bytes(f.read(), "UTF-8")

        f_a = SimpleUploadedFile(
            "CH4.stuff_conf1.xyz", xyz, content_type="chemical/x-xyz"
        )
        f_b = SimpleUploadedFile(
            "CH3.stuff_conf2.xyz", xyz, content_type="chemical/x-xyz"
        )

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "-1"
        params["file_structure"] = [f_a, f_b]
        params["calc_combine_files"] = ("",)
        params["calc_parse_filenames"] = "on"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 2)
        self.assertEqual(Molecule.objects.count(), 2)
        self.assertEqual(Ensemble.objects.count(), 2)

    def test_two_files_parse_names_different_bug(self):
        with open(os.path.join(tests_dir, "Cl.xyz")) as f:
            xyz = bytes(f.read(), "UTF-8")

        structures = []
        for name in [
            "a)Int1_OAc_cis_chair_conf1.xyz",
            "a)Int1_OAc_cis_flat_conf2.xyz",
            "a)Int1_OAc_trans_ext_conf2.xyz",
            "a)Int1_OAc_trans_para_conf1.xyz",
            "b)Int1_OAc_cis_chair_conf1.xyz",
            "b)Int1_OAc_cis_flat_conf2.xyz",
            "b)Int1_OAc_trans_ext_conf2.xyz",
            "b)Int1_OAc_trans_para_conf1.xyz",
        ]:
            structures.append(
                SimpleUploadedFile(name, xyz, content_type="chemical/x-xyz")
            )

        params = basic_params.copy()
        params["structure"] = ""
        params["calc_charge"] = "-1"
        params["file_structure"] = structures
        params["calc_combine_files"] = ("",)
        params["calc_parse_filenames"] = "on"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Error while submitting your calculation")

        self.assertEqual(CalculationOrder.objects.count(), 8)
        self.assertEqual(Molecule.objects.count(), 8)
        self.assertEqual(Ensemble.objects.count(), 8)


class RestrictionTests(TestCase):
    def setUp(self):
        call_command("init_static_obj")
        self.email = "Tester@test.com"
        self.password = "test1234"

        self.user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
        )
        self.group = ResearchGroup.objects.create(name="Test group", PI=self.user)
        self.client = Client()
        self.client.force_login(self.user)

        self.prev_LOCAL_MAX_ATOMS = settings.LOCAL_MAX_ATOMS
        self.prev_LOCAL_ALLOWED_THEORY_LEVELS = copy.deepcopy(
            settings.LOCAL_ALLOWED_THEORY_LEVELS
        )
        self.prev_LOCAL_ALLOWED_STEPS = copy.deepcopy(settings.LOCAL_ALLOWED_STEPS)

        settings.LOCAL_MAX_ATOMS = 15
        settings.LOCAL_ALLOWED_THEORY_LEVELS = ["xtb", "semiempirical"]
        settings.LOCAL_ALLOWED_STEPS = [
            "Single-Point Energy",
            "Geometrical Optimisation",
        ]

    def tearDown(self):
        # The settings would effect next tests
        settings.LOCAL_MAX_ATOMS = self.prev_LOCAL_MAX_ATOMS
        settings.LOCAL_ALLOWED_THEORY_LEVELS = self.prev_LOCAL_ALLOWED_THEORY_LEVELS
        settings.LOCAL_ALLOWED_STEPS = self.prev_LOCAL_ALLOWED_STEPS

    def test_baseline_drawing(self):
        params = basic_params.copy()
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertNotContains(response, "Error while submitting your calculation")

    def test_baseline_file(self):
        params = basic_params.copy()
        with open(os.path.join(tests_dir, "H2.xyz")) as f:
            del params["structure"]
            params["file_structure"] = f
            response = self.client.post(
                "/submit_calculation/", data=params, follow=True
            )

        self.assertNotContains(response, "Error while submitting your calculation")

    def test_limit_size_file(self):
        params = basic_params.copy()
        with open(os.path.join(tests_dir, "benzene.xyz")) as f:
            del params["structure"]
            params["file_structure"] = f
            response = self.client.post(
                "/submit_calculation/", data=params, follow=True
            )

        self.assertNotContains(response, "Error while submitting your calculation")

    def test_too_large_file(self):
        params = basic_params.copy()
        with open(os.path.join(tests_dir, "pentane.xyz")) as f:
            del params["structure"]
            params["file_structure"] = f
            response = self.client.post(
                "/submit_calculation/", data=params, follow=True
            )

        self.assertContains(response, "Error while submitting your calculation")

    def test_too_large_drawing(self):
        params = basic_params.copy()

        params["structure"] = LARGE_DRAWING
        response = self.client.post("/submit_calculation/", data=params, follow=True)

        self.assertContains(response, "Error while submitting your calculation")

    def test_forbidden_dft(self):
        params = basic_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "DFT"
        params["calc_functional"] = "M06-2X"
        params["calc_basis_set"] = "Def2-SVP"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_forbidden_hf(self):
        params = basic_params.copy()
        params["calc_software"] = "ORCA"
        params["calc_theory_level"] = "HF"
        params["calc_basis_set"] = "Def2-SVP"

        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_forbidden_conf_search(self):
        params = basic_params.copy()
        params["calc_type"] = "Conformational Search"
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_forbidden_freq(self):
        params = basic_params.copy()
        params["calc_type"] = "Frequency Calculation"
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertContains(response, "Error while submitting your calculation")

    def test_allowed_sp(self):
        params = basic_params.copy()
        params["calc_type"] = "Single-Point Energy"
        response = self.client.post("/submit_calculation/", data=params, follow=True)
        self.assertNotContains(response, "Error while submitting your calculation")


class PermissionTestsStudent(TestCase):
    def setUp(self):
        call_command("init_static_obj")
        self.email = "Tester@test.com"
        self.password = "test1234"

        self.user = User.objects.create_user(
            email=self.email,
            password=self.password,
        )

        self.PI = User.objects.create_user(
            email="PI@test.com",
            password=self.password,
        )
        self.group = ResearchGroup.objects.create(name="Test group", PI=self.PI)

        self.client = Client()
        self.client.force_login(self.user)

    def test_project_public_nonmember(self):
        p = Project.objects.create(name="Public Project", author=self.PI, private=0)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get(f"/projects/{self.PI.id}")
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f"/projects/{self.PI.id}/Public Project")
        self.assertEqual(response.status_code, 302)

        response = self.client.get(f"/molecule/{m.id}")
        self.assertEqual(response.status_code, 302)

        response = self.client.get(f"/ensemble/{e.id}")
        self.assertEqual(response.status_code, 302)

        response = self.client.get(f"/download_structures/{e.id}")
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f"/download_structures/{e.id}/0")
        self.assertEqual(response.status_code, 404)

    def test_project_public(self):
        self.user.member_of = self.group
        self.user.save()

        p = Project.objects.create(name="Public Project", author=self.PI, private=0)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get(f"/projects/{self.PI.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/projects/{self.PI.id}/Public Project")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/molecule/{m.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/ensemble/{e.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/download_structures/{e.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/download_structures/{e.id}/0")
        self.assertEqual(response.status_code, 200)

    def test_project_private(self):
        self.user.member_of = self.group
        self.user.save()

        p = Project.objects.create(name="Public Project", author=self.PI, private=1)
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get(f"/projects/{self.PI.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/projects/{self.PI.id}/Public Project")
        self.assertEqual(response.status_code, 302)

        response = self.client.get(f"/molecule/{m.id}")
        self.assertEqual(response.status_code, 302)

        response = self.client.get(f"/ensemble/{e.id}")
        self.assertEqual(response.status_code, 302)

        response = self.client.get(f"/download_structures/{e.id}")
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f"/download_structures/{e.id}/0")
        self.assertEqual(response.status_code, 404)


class PermissionTestsPI(TestCase):
    def setUp(self):
        call_command("init_static_obj")
        self.email = "Tester@test.com"
        self.password = "test1234"

        self.user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.student = User.objects.create_user(
            email="Student@test.com", password=self.password
        )

        self.group = ResearchGroup.objects.create(name="Test group", PI=self.user)

        self.client = Client()
        self.client.force_login(self.user)

    def test_project_public_nonmember(self):
        p = Project.objects.create(
            name="Public Project", author=self.student, private=0
        )
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get(f"/projects/{self.student.id}")
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f"/projects/{self.student.id}/Public Project")
        self.assertEqual(response.status_code, 302)

        response = self.client.get(f"/molecule/{m.id}")
        self.assertEqual(response.status_code, 302)

        response = self.client.get(f"/ensemble/{e.id}")
        self.assertEqual(response.status_code, 302)

        response = self.client.get(f"/download_structures/{e.id}")
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f"/download_structures/{e.id}/0")
        self.assertEqual(response.status_code, 404)

    def test_project_public(self):
        self.student.member_of = self.group
        self.student.save()

        p = Project.objects.create(
            name="Public Project", author=self.student, private=0
        )
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get(f"/projects/{self.student.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/projects/{self.student.id}/Public Project")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/molecule/{m.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/ensemble/{e.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/download_structures/{e.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/download_structures/{e.id}/0")
        self.assertEqual(response.status_code, 200)

    def test_project_private(self):
        self.student.member_of = self.group
        self.student.save()

        p = Project.objects.create(
            name="Public Project", author=self.student, private=1
        )
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.get(f"/projects/{self.student.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/projects/{self.student.id}/Public Project")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/molecule/{m.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/ensemble/{e.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/download_structures/{e.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/download_structures/{e.id}/0")
        self.assertEqual(response.status_code, 200)

    def test_delete_project_user(self):
        self.student.member_of = self.group
        self.student.save()

        p = Project.objects.create(
            name="Public Project", author=self.student, private=1
        )
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.post("/delete_project/", {"id": p.id})
        self.assertEqual(response.status_code, 403)

    def test_delete_molecule_user(self):
        self.student.member_of = self.group
        self.student.save()

        p = Project.objects.create(
            name="Public Project", author=self.student, private=1
        )
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.post("/delete_molecule/", {"id": m.id})
        self.assertEqual(response.status_code, 403)

    def test_delete_ensemble_user(self):
        self.student.member_of = self.group
        self.student.save()

        p = Project.objects.create(
            name="Public Project", author=self.student, private=1
        )
        m = Molecule.objects.create(name="Public Molecule", project=p, inchi="dummy")
        e = Ensemble.objects.create(name="Public Ensemble", parent_molecule=m)
        s = Structure.objects.create(parent_ensemble=e, number=0)
        p.save()
        m.save()
        e.save()
        s.save()

        response = self.client.post("/delete_ensemble/", {"id": e.id})
        self.assertEqual(response.status_code, 403)


class AnalysisTests(TestCase):
    def setUp(self):
        call_command("init_static_obj")
        self.email = "Tester@test.com"
        self.password = "test1234"

        self.user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
        )
        self.group = ResearchGroup.objects.create(name="Test group", PI=self.user)
        self.client = Client()
        self.client.force_login(self.user)

        self.client = Client()
        self.client.force_login(self.user)

    def test_boltzmann_weighting_Ha(self):
        self.user.pref_units = 2  # Hartree
        self.user.save()

        proj = Project.objects.create(name="TestProj", author=self.user)
        mol = Molecule.objects.create(name="Mol1", project=proj)
        e = Ensemble.objects.create(name="Confs", parent_molecule=mol)

        structs = [
            [-16.82945685, 9],
            [-16.82855278, 36],
            [-16.82760256, 7],
            [-16.82760254, 9],
            [-16.82760156, 2],
            [-16.82558904, 33],
            [-16.82495672, 1],
        ]  # From CREST (GFN2-xTB)
        rel_energies = [i[0] + 16.82945685 for i in structs]

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs):
            s = Structure.objects.create(
                parent_ensemble=e, number=ind + 1, degeneracy=structs[ind][1]
            )
            prop = Property.objects.create(
                parameters=params, energy=structs[ind][0], parent_structure=s
            )
            prop.save()
            s.save()
        e.save()
        proj.save()
        mol.save()
        ref_weights = [0.34724, 0.53361, 0.03796, 0.04880, 0.01082, 0.02125, 0.00033]

        response = self.client.post(
            "/download_project/",
            {
                "id": proj.id,
                "data": "summary",
                "scope": "all",
                "details": "full",
                "folders": False,
            },
        )
        csv = response.content.decode("utf-8")

        lines = csv.split("\n")
        ind = 0
        while lines[ind].find(",,Confs") == -1:
            ind += 1
        ind += 1

        while lines[ind].strip() != "":
            *_, num, degeneracy, energy, rel_energy, weight, free_energy = lines[
                ind
            ].split(",")

            self.assertTrue(
                np.isclose(float(energy), structs[int(num) - 1][0], atol=0.0001)
            )
            self.assertTrue(
                np.isclose(float(weight), ref_weights[int(num) - 1], atol=0.001)
            )
            self.assertTrue(
                np.isclose(float(rel_energy), rel_energies[int(num) - 1], atol=0.0001)
            )
            self.assertEqual(float(free_energy), 0.0)
            ind += 1

    def test_boltzmann_weighting_Ha2(self):
        self.user.pref_units = 2  # Hartree
        self.user.save()

        proj = Project.objects.create(name="TestProj", author=self.user)
        mol = Molecule.objects.create(name="Mol1", project=proj)
        e = Ensemble.objects.create(name="Confs", parent_molecule=mol)

        structs = [
            [-37.76591, 1],
            [-37.76575, 1],
            [-37.76533, 1],
        ]  # From CREST (GFN2-xTB)
        rel_energies = [i[0] + 37.76591 for i in structs]

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs):
            s = Structure.objects.create(
                parent_ensemble=e, number=ind + 1, degeneracy=structs[ind][1]
            )
            prop = Property.objects.create(
                parameters=params, energy=structs[ind][0], parent_structure=s
            )
            prop.save()
            s.save()
        e.save()
        proj.save()
        mol.save()
        ref_weights = [0.42044, 0.35261, 0.22695]

        response = self.client.post(
            "/download_project/",
            {
                "id": proj.id,
                "data": "summary",
                "scope": "all",
                "details": "full",
                "folders": False,
            },
        )
        csv = response.content.decode("utf-8")

        lines = csv.split("\n")
        ind = 0
        while lines[ind].find(",,Confs") == -1:
            ind += 1
        ind += 1

        while lines[ind].strip() != "":
            *_, num, degeneracy, energy, rel_energy, weight, free_energy = lines[
                ind
            ].split(",")

            self.assertTrue(
                np.isclose(float(energy), structs[int(num) - 1][0], atol=0.0001)
            )
            self.assertTrue(
                np.isclose(float(weight), ref_weights[int(num) - 1], atol=0.01)
            )
            self.assertTrue(
                np.isclose(float(rel_energy), rel_energies[int(num) - 1], atol=0.0001)
            )
            self.assertEqual(float(free_energy), 0.0)
            ind += 1

    def test_boltzmann_weighting_kJ(self):
        self.user.pref_units = 0  # kJ/mol
        self.user.save()

        proj = Project.objects.create(name="TestProj", author=self.user)
        mol = Molecule.objects.create(name="Mol1", project=proj)
        e = Ensemble.objects.create(name="Confs", parent_molecule=mol)

        structs = [
            [-16.82945685, 9],
            [-16.82855278, 36],
            [-16.82760256, 7],
            [-16.82760254, 9],
            [-16.82760156, 2],
            [-16.82558904, 33],
            [-16.82495672, 1],
        ]  # From CREST (GFN2-xTB)
        rel_energies = [i[0] + 16.82945685 for i in structs]

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs):
            s = Structure.objects.create(
                parent_ensemble=e, number=ind + 1, degeneracy=structs[ind][1]
            )
            prop = Property.objects.create(
                parameters=params, energy=structs[ind][0], parent_structure=s
            )
            prop.save()
            s.save()
        e.save()
        proj.save()
        mol.save()
        ref_weights = [0.34724, 0.53361, 0.03796, 0.04880, 0.01082, 0.02125, 0.00033]

        response = self.client.post(
            "/download_project/",
            {
                "id": proj.id,
                "data": "summary",
                "scope": "all",
                "details": "full",
                "folders": False,
            },
        )
        csv = response.content.decode("utf-8")

        lines = csv.split("\n")
        ind = 0
        while lines[ind].find(",,Confs") == -1:
            ind += 1
        ind += 1

        while lines[ind].strip() != "":
            *_, num, degeneracy, energy, rel_energy, weight, free_energy = lines[
                ind
            ].split(",")

            self.assertTrue(
                np.isclose(
                    float(energy), structs[int(num) - 1][0] * HARTREE_FVAL, atol=0.1
                )
            )
            self.assertTrue(
                np.isclose(float(weight), ref_weights[int(num) - 1], atol=0.001)
            )
            self.assertTrue(
                np.isclose(
                    float(rel_energy),
                    rel_energies[int(num) - 1] * HARTREE_FVAL,
                    atol=0.1,
                )
            )
            self.assertEqual(float(free_energy), 0.0)

            ind += 1

    def test_boltzmann_weighting_kcal(self):
        self.user.pref_units = 1  # kcal/mol
        self.user.save()

        proj = Project.objects.create(name="TestProj", author=self.user)
        mol = Molecule.objects.create(name="Mol1", project=proj)
        e = Ensemble.objects.create(name="Confs", parent_molecule=mol)

        structs = [
            [-16.82945685, 9],
            [-16.82855278, 36],
            [-16.82760256, 7],
            [-16.82760254, 9],
            [-16.82760156, 2],
            [-16.82558904, 33],
            [-16.82495672, 1],
        ]  # From CREST (GFN2-xTB)
        rel_energies = [i[0] + 16.82945685 for i in structs]

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs):
            s = Structure.objects.create(
                parent_ensemble=e, number=ind + 1, degeneracy=structs[ind][1]
            )
            prop = Property.objects.create(
                parameters=params, energy=structs[ind][0], parent_structure=s
            )
            prop.save()
            s.save()
        e.save()
        proj.save()
        mol.save()
        ref_weights = [0.34724, 0.53361, 0.03796, 0.04880, 0.01082, 0.02125, 0.00033]

        response = self.client.post(
            "/download_project/",
            {
                "id": proj.id,
                "data": "summary",
                "scope": "all",
                "details": "full",
                "folders": False,
            },
        )
        csv = response.content.decode("utf-8")

        lines = csv.split("\n")
        ind = 0
        while lines[ind].find(",,Confs") == -1:
            ind += 1
        ind += 1

        while lines[ind].strip() != "":
            *_, num, degeneracy, energy, rel_energy, weight, free_energy = lines[
                ind
            ].split(",")

            self.assertTrue(
                np.isclose(
                    float(energy),
                    structs[int(num) - 1][0] * HARTREE_TO_KCAL_F,
                    atol=0.001,
                )
            )
            self.assertTrue(
                np.isclose(float(weight), ref_weights[int(num) - 1], atol=0.001)
            )
            self.assertTrue(
                np.isclose(
                    float(rel_energy),
                    rel_energies[int(num) - 1] * HARTREE_TO_KCAL_F,
                    atol=0.01,
                )
            )
            self.assertEqual(float(free_energy), 0.0)

            ind += 1

    def test_boltzmann_weighting_missing_structures(self):
        self.user.pref_units = 2  # Hartree
        self.user.save()

        proj = Project.objects.create(name="TestProj", author=self.user)
        mol = Molecule.objects.create(name="Mol1", project=proj)
        e = Ensemble.objects.create(name="Confs", parent_molecule=mol)

        structs = [
            [-16.82945685, 9],
            [-16.82855278, 36],
            [-16.82760256, 7],
            [-16.82760254, 9],
            [-16.82760156, 2],
            [-16.82558904, 33],
            [-16.82495672, 1],
        ]  # From CREST (GFN2-xTB)
        rel_energies = [i[0] + 16.82945685 for i in structs]

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs[:-3]):
            s = Structure.objects.create(
                parent_ensemble=e, number=ind + 1, degeneracy=structs[ind][1]
            )
            prop = Property.objects.create(
                parameters=params, energy=structs[ind][0], parent_structure=s
            )
            prop.save()
            s.save()

        for ind, _s in enumerate(structs[-3:]):
            s = Structure.objects.create(
                parent_ensemble=e, number=ind + 5, degeneracy=structs[ind][1]
            )
            s.save()

        e.save()
        proj.save()
        mol.save()
        ref_weights = [0.359, 0.551, 0.039, 0.050]  # Generated by working code

        response = self.client.post(
            "/download_project/",
            {
                "id": proj.id,
                "data": "summary",
                "scope": "all",
                "details": "full",
                "folders": False,
            },
        )
        csv = response.content.decode("utf-8")

        lines = csv.split("\n")
        ind = 0
        while lines[ind].find(",,Confs") == -1:
            ind += 1
        ind += 1

        while lines[ind].strip() != "":
            *_, num, degeneracy, energy, rel_energy, weight, free_energy = lines[
                ind
            ].split(",")
            self.assertTrue(
                np.isclose(float(energy), structs[int(num) - 1][0], atol=0.0001)
            )
            self.assertTrue(
                np.isclose(float(weight), ref_weights[int(num) - 1], atol=0.001)
            )
            self.assertTrue(
                np.isclose(float(rel_energy), rel_energies[int(num) - 1], atol=0.0001)
            )
            self.assertEqual(float(free_energy), 0.0)
            ind += 1

    def test_summary(self):
        self.user.pref_units = 2
        self.user.save()

        proj = Project.objects.create(name="TestProj", author=self.user)
        mol = Molecule.objects.create(name="Mol1", project=proj)
        e = Ensemble.objects.create(name="Confs", parent_molecule=mol)

        structs = [
            [-16.82945685, 9],
            [-16.82855278, 36],
            [-16.82760256, 7],
            [-16.82760254, 9],
            [-16.82760156, 2],
            [-16.82558904, 33],
            [-16.82495672, 1],
        ]  # From CREST (GFN2-xTB)
        ref_w_e = -16.82871

        params = Parameters.objects.create(charge=0, multiplicity=1)
        for ind, _s in enumerate(structs):
            s = Structure.objects.create(
                parent_ensemble=e, number=ind + 1, degeneracy=structs[ind][1]
            )
            prop = Property.objects.create(
                parameters=params, energy=structs[ind][0], parent_structure=s
            )
            prop.save()
            s.save()

        response = self.client.post(
            "/download_project/",
            {
                "id": proj.id,
                "data": "summary",
                "scope": "all",
                "details": "summary",
                "folders": False,
            },
        )

        csv = response.content.decode("utf-8")

        lines = csv.split("\n")
        ind = 0
        while lines[ind].find(",,Confs") == -1:
            ind += 1

        *_, w_e, w_f_e = lines[ind].split(",")
        self.assertTrue(np.isclose(float(w_e), ref_w_e, atol=0.0001))


class CalculationTests(TestCase):
    def tearDown(self):
        if os.path.isdir(SCR_DIR):
            rmtree(SCR_DIR)

    def setUp(self):
        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)

        call_command("init_static_obj")
        self.email = "Tester@test.com"
        self.password = "test1234"

        self.user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
        )
        self.group = ResearchGroup.objects.create(name="Test group", PI=self.user)
        self.client = Client()
        self.client.force_login(self.user)

    def test_Gaussian_frames1(self):
        params = {
            "calc_name": "test",
            "type": "Constrained Optimisation",
            "constraints": [["Scan", "Angle", [1, 2, 3], [120, 130, 10]]],  # Dummy
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "software": "Gaussian",
            "in_file": "CH4.xyz",
            "theory": "Semi-empirical",
            "method": "AM1",
        }

        calc = gen_calc(params, self.user)
        calc.status = 1
        calc.save()
        if os.path.isdir(os.path.join(SCR_DIR, str(calc.id))):
            rmtree(os.path.join(SCR_DIR, str(calc.id)))
        os.mkdir(os.path.join(SCR_DIR, str(calc.id)))
        copyfile(
            os.path.join(tests_dir, "Gaussian_scan1.log"),
            os.path.join(SCR_DIR, str(calc.id), "calc.log"),
        )

        response = self.client.post(f"/get_calc_data/{calc.id}")

        data = response.content.decode("utf-8")
        xyz, rmsd, opt = data.split(";")
        sxyz = [
            i.strip() for i in xyz.split("\n") if i.strip() != ""
        ]  # This removes the title lines from the xyz
        num_atoms = int(sxyz[0])

        self.assertEqual(len(sxyz) % (num_atoms + 1), 0)
        num_frames = int(len(sxyz) / (num_atoms + 1))
        self.assertEqual(num_frames, 19)

        srmsd = [i.strip() for i in rmsd.split("\n") if i.strip() != ""][1:]

        self.assertEqual(num_frames, len(srmsd))

    def test_Gaussian_frames2(self):
        params = {
            "calc_name": "test",
            "type": "Constrained Optimisation",
            "constraints": [["Scan", "Angle", [1, 2, 3], [120, 130, 10]]],  # Dummy
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "software": "Gaussian",
            "in_file": "CH4.xyz",
            "theory": "Semi-empirical",
            "method": "AM1",
        }

        calc = gen_calc(params, self.user)
        calc.status = 1
        calc.save()
        os.mkdir(os.path.join(SCR_DIR, str(calc.id)))
        copyfile(
            os.path.join(tests_dir, "Gaussian_scan2.log"),
            os.path.join(SCR_DIR, str(calc.id), "calc.log"),
        )

        response = self.client.post(f"/get_calc_data/{calc.id}")

        data = response.content.decode("utf-8")
        xyz, rmsd, opt = data.split(";")
        sxyz = [
            i.strip() for i in xyz.split("\n") if i.strip() != ""
        ]  # This removes the title lines from the xyz
        num_atoms = int(sxyz[0])

        self.assertEqual(len(sxyz) % (num_atoms + 1), 0)
        num_frames = int(len(sxyz) / (num_atoms + 1))
        self.assertEqual(num_frames, 25)

        srmsd = [i.strip() for i in rmsd.split("\n") if i.strip() != ""][1:]

        self.assertEqual(num_frames, len(srmsd))

    def test_Gaussian_frames3(self):
        params = {
            "calc_name": "test",
            "type": "Constrained Optimisation",
            "constraints": [["Scan", "Angle", [1, 2, 3], [120, 130, 10]]],  # Dummy
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "software": "Gaussian",
            "in_file": "CH4.xyz",
            "theory": "Semi-empirical",
            "method": "AM1",
        }

        calc = gen_calc(params, self.user)
        calc.status = 1
        calc.save()
        os.mkdir(os.path.join(SCR_DIR, str(calc.id)))
        copyfile(
            os.path.join(tests_dir, "Gaussian_scan3.log"),
            os.path.join(SCR_DIR, str(calc.id), "calc.log"),
        )

        response = self.client.post(f"/get_calc_data/{calc.id}")

        data = response.content.decode("utf-8")
        xyz, rmsd, opt = data.split(";")
        sxyz = [
            i.strip() for i in xyz.split("\n") if i.strip() != ""
        ]  # This removes the title lines from the xyz
        num_atoms = int(sxyz[0])

        self.assertEqual(len(sxyz) % (num_atoms + 1), 0)
        num_frames = int(len(sxyz) / (num_atoms + 1))
        self.assertEqual(num_frames, 31)

        srmsd = [i.strip() for i in rmsd.split("\n") if i.strip() != ""][1:]

        self.assertEqual(num_frames, len(srmsd))


class MiscTests(TestCase):
    def tearDown(self):
        if os.path.isdir(SCR_DIR):
            rmtree(SCR_DIR)

    def setUp(self):
        if not os.path.isdir(SCR_DIR):
            os.mkdir(SCR_DIR)

        call_command("init_static_obj")
        self.email = "Tester@test.com"
        self.password = "test1234"

        self.user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
        )
        self.group = ResearchGroup.objects.create(name="Test group", PI=self.user)
        self.client = Client()
        self.client.force_login(self.user)


"""
    def test_related_calculations(self):
        proj = Project.objects.create(name="Test project", author=self.user)
        mol = Molecule.objects.create(name="Test Molecule", project=proj)
        e1 = Ensemble.objects.create(name="Test Ensemble", parent_molecule=mol)
        s1 = Structure.objects.create(parent_ensemble=e1)

        p1 = {
                'charge': '0',
                'multiplicity': '1',
                'software': 'xtb',
        }
        p2 = {
                'charge': '1',
                'multiplicity': '2',
                'software': 'xtb',
        }

        param1 = gen_param(p1)
        param2 = gen_param(p2)

        e2 = Ensemble.objects.create(name="Result Ensemble", parent_molecule=mol)
        s2 = Structure.objects.create(parent_ensemble=e2)

        o1 = CalculationOrder.objects.create(author=self.user, project=proj)
        calc1 = Calculation.objects.create(order=o1, structure=s1, result_ensemble=e2)

        o2 = CalculationOrder.objects.create(author=self.user, project=proj)
        calc2 = Calculation.objects.create(order=o2, structure=s2, result_ensemble=e2)

        related = self.client.get("/get_related_calculations/{}".format(e2.pk))
        print(related.content)
"""


class CloudTests(TestCase):
    def setUp(self):
        super().setUp()
        settings.IS_CLOUD = True
        settings.GCP_LOCATION = "us-central1"
        settings.GCP_PROJECT_ID = "test-project"
        settings.GCP_SERVICE_ACCOUNT_EMAIL = "selenium@calcus.cloud"
        settings.COMPUTE_SMALL_HOST_URL = "http://cloud-compute:8001"
        settings.ACTION_HOST_URL = "http://cloud-compute:8001"
        settings.ALLOW_REMOTE_CALC = False
        settings.LOCAL_MAX_ATOMS = 60

        settings.LOCAL_ALLOWED_THEORY_LEVELS = [
            "xtb",
        ]

        self.email = "Tester@test.com"
        self.password = "test1234"

        self.user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
        )
        self.group = ResearchGroup.objects.create(name="Test group", PI=self.user)
        self.client = Client()
        self.client.force_login(self.user)

    def tearDown(self):
        super().tearDown()

        settings.IS_CLOUD = False
        settings.ALLOW_REMOTE_CALC = True
        settings.LOCAL_MAX_ATOMS = -1
        settings.LOCAL_ALLOWED_THEORY_LEVELS = ["ALL"]
        settings.LOCAL_ALLOWED_STEPS = ["ALL"]

    def test_refill(self):
        self.assertEqual(self.user.allocated_seconds, 0)
        headers = {"HTTP_X_CLOUDSCHEDULER": "something"}
        response = self.client.post("/cloud_refills/", **headers)

        self.user.refresh_from_db()
        self.assertEqual(self.user.allocated_seconds, 300)

    def test_no_double_refill(self):
        self.assertEqual(self.user.allocated_seconds, 0)
        headers = {"HTTP_X_CLOUDSCHEDULER": "something"}
        response = self.client.post("/cloud_refills/", **headers)

        self.user.refresh_from_db()
        self.assertEqual(self.user.allocated_seconds, 300)

        response = self.client.post("/cloud_refills/", **headers)

        self.user.refresh_from_db()
        self.assertEqual(self.user.allocated_seconds, 300)

    def test_no_early_refill(self):
        last_refill = timezone.now() - timezone.timedelta(days=10)
        self.user.last_free_refill = last_refill
        self.user.save()

        self.assertEqual(self.user.allocated_seconds, 0)
        headers = {"HTTP_X_CLOUDSCHEDULER": "something"}
        response = self.client.post("/cloud_refills/", **headers)

        self.user.refresh_from_db()
        self.assertEqual(self.user.allocated_seconds, 0)
        self.assertEqual(self.user.last_free_refill, last_refill)

    def test_refill_cap(self):
        self.user.allocated_seconds = 100
        self.user.save()

        headers = {"HTTP_X_CLOUDSCHEDULER": "something"}
        response = self.client.post("/cloud_refills/", **headers)

        self.user.refresh_from_db()
        self.assertEqual(self.user.allocated_seconds, 300)

    def test_refill_above_cap(self):
        self.user.allocated_seconds = 500
        self.user.save()

        headers = {"HTTP_X_CLOUDSCHEDULER": "something"}
        response = self.client.post("/cloud_refills/", **headers)

        self.user.refresh_from_db()
        self.assertEqual(self.user.allocated_seconds, 500)
