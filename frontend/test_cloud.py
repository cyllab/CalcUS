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


class CalculationManagementTests(CalcusCloudLiveServer):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.user)
        g.save()
        self.user.allocated_seconds = 100
        self.user.save()

    @mock.patch.dict(os.environ, {"CACHE_POST_WAIT": "15"})
    def test_relaunch_calc(self):
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
        time.sleep(2)
        self.details_latest_order()
        self.cancel_all_calc()
        self.lget("/calculations/")
        self.wait_latest_calc_error(15)

        self.details_latest_order()
        self.relaunch_all_calc()
        self.lget("/calculations/")
        self.wait_latest_calc_done(15)

        c = Calculation.objects.latest("id")
        self.assertEqual(c.status, 2)


class ResourceTests(CalcusCloudLiveServer):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_redeem_code(self):
        r = ResourceAllocation.objects.create(code="ABCD", allocation_seconds=100)
        self.assertEqual(r.redeemer, None)

        self.assertEqual(self.user.allocated_seconds, 100)

        self.redeem_code("ABCD")

        self.user.refresh_from_db()
        self.assertEqual(self.user.allocated_seconds, 200)

        r.refresh_from_db()
        self.assertEqual(r.redeemer, self.user)

    def test_redeem_invalid_code(self):
        self.assertEqual(self.user.allocated_seconds, 100)

        with self.assertRaises(Exception) as ex:
            self.redeem_code("ABCD")

        self.assertEqual(
            str(ex.exception), "Error while redeeming code: Invalid code given"
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.allocated_seconds, 100)

    def test_redeem_code_twice(self):
        r = ResourceAllocation.objects.create(code="ABCD", allocation_seconds=100)
        self.assertEqual(r.redeemer, None)

        self.assertEqual(self.user.allocated_seconds, 100)

        self.redeem_code("ABCD")

        self.user.refresh_from_db()
        self.assertEqual(self.user.allocated_seconds, 200)

        with self.assertRaises(Exception) as ex:
            self.redeem_code("ABCD")

        self.assertEqual(
            str(ex.exception), "Error while redeeming code: Code already redeemed"
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.allocated_seconds, 200)

    def test_redeem_nothing(self):
        self.assertEqual(self.user.allocated_seconds, 100)

        with self.assertRaises(Exception) as ex:
            self.redeem_code("")

        self.assertEqual(str(ex.exception), "Error while redeeming code: No code given")

    def test_redeem_claimed_code(self):
        self.student = User.objects.create_user(
            email="Student@uni.com", password=self.password
        )
        r = ResourceAllocation.objects.create(
            code="ABCD", allocation_seconds=100, redeemer=self.student
        )

        with self.assertRaises(Exception) as ex:
            self.redeem_code("ABCD")

        self.assertEqual(
            str(ex.exception), "Error while redeeming code: Code already redeemed"
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.allocated_seconds, 100)

        r.refresh_from_db()
        self.assertEqual(r.redeemer, self.student)
