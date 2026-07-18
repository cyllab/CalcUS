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
import selenium
import datetime
import shutil
from unittest import mock, skipIf

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from django.conf import settings
from django.utils import timezone

from .models import (
    Calculation,
    ClassGroup,
    Molecule,
    Project,
    ResearchGroup,
    ResourceAllocation,
    Subscription,
    User,
)
from .storage_backends.calculation_outputs import has_outputs, read_all_output_files
from .calcusliveserver import CalcusCloudLiveServer

GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"


@skipIf(GITHUB_ACTIONS, "Tests not suitable for GitHub Actions")
class CloudCalculationTests(CalcusCloudLiveServer):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.user)
        self.user.allocated_seconds = 100
        self.user.save()

    def test_xtb_accessible(self):
        resp = shutil.which("xtb")
        self.assertEqual(resp, "/binaries/xtb/bin/xtb")

    def test_crest_accessible(self):
        resp = shutil.which("crest")
        self.assertEqual(resp, "/binaries/crest")

    def test_multiwfn_accessible(self):
        resp = shutil.which("Multiwfn")
        self.assertEqual(resp, "/binaries/Multiwfn")

    def test_stda_accessible(self):
        resp = shutil.which("stda")
        self.assertEqual(resp, "/binaries/stda")

    def test_xtb4stda_accessible(self):
        resp = shutil.which("xtb4stda")
        self.assertEqual(resp, "/binaries/xtb4stda")

    def test_xtbiff_accessible(self):
        resp = shutil.which("xtbiff")
        self.assertEqual(resp, "/binaries/xtbiff")

    def test_dummy_not_accessible(self):
        resp = shutil.which("xtb2")
        self.assertEqual(resp, None)

    def test_opt(self):
        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
            "interface": "simple",
        }

        self.assertEqual(self.user.billed_seconds, 0)

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

        calc = Calculation.objects.latest("pk")
        self.assertTrue(has_outputs(calc))

        data = read_all_output_files(calc)

        assert "calc" in data


@skipIf(GITHUB_ACTIONS, "Tests not suitable for GitHub Actions")
class CalculationTimeBillingTests(CalcusCloudLiveServer):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.user)
        self.user.allocated_seconds = 100
        self.user.save()

    def test_opt(self):
        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
            "interface": "simple",
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
            "interface": "simple",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

        self.user.refresh_from_db()
        self.assertNotEqual(self.user.billed_seconds, 0)

    def test_proj(self):
        proj = Project.objects.create(author=self.user, name="TestProj")

        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "TestProj",
            "in_file": "CH4.mol",
            "interface": "simple",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())

        self.user.refresh_from_db()
        self.assertNotEqual(self.user.billed_seconds, 0)

    def test_no_time(self):
        self.user.allocated_seconds = 0
        self.user.save()

        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
            "interface": "simple",
        }

        self.assertEqual(self.user.billed_seconds, 0)

        self.lget("/launch/")
        self.calc_input_params(params)

        with self.assertRaises(Exception) as ex:
            self.calc_launch()

        self.assertEqual(
            str(ex.exception),
            "Got error while submitting calculation: Could not submit the calculation: You have insufficient calculation time to launch a calculation",
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.billed_seconds, 0)

    def test_no_time_left(self):
        self.user.billed_seconds = 100
        self.user.save()

        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
            "interface": "simple",
        }

        self.lget("/launch/")
        self.calc_input_params(params)

        with self.assertRaises(Exception) as ex:
            self.calc_launch()

        self.assertEqual(
            str(ex.exception),
            "Got error while submitting calculation: Could not submit the calculation: You have insufficient calculation time to launch a calculation",
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.billed_seconds, 100)

    def test_time_busted(self):
        self.user.billed_seconds = 1000
        self.user.save()

        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
            "interface": "simple",
        }

        self.lget("/launch/")
        self.calc_input_params(params)

        with self.assertRaises(Exception) as ex:
            self.calc_launch()

        self.assertEqual(
            str(ex.exception),
            "Got error while submitting calculation: Could not submit the calculation: You have insufficient calculation time to launch a calculation",
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.billed_seconds, 1000)


@skipIf(GITHUB_ACTIONS, "Tests not suitable for GitHub Actions")
class StudentTests(CalcusCloudLiveServer):
    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.user)

        self.student = User.objects.create_user(
            email="Student@uni.com", password=self.password
        )
        self.student.member_of = g
        self.student.calc_type_property = False
        self.student.save()

        self.login("Student@uni.com", self.password)

    def test_opt(self):
        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
            "interface": "simple",
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

        params = {
            "mol_name": "my_mol",
            "type": "Geometrical Optimisation",
            "project": "TestProj",
            "in_file": "CH4.mol",
            "interface": "simple",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.lget("/calculations/")
        self.wait_latest_calc_done(10)
        self.assertTrue(self.latest_calc_successful())


@skipIf(GITHUB_ACTIONS, "Tests not suitable for GitHub Actions")
class CalculationManagementTests(CalcusCloudLiveServer):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.user)
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
            "interface": "simple",
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


@skipIf(GITHUB_ACTIONS, "Tests not suitable for GitHub Actions")
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


@skipIf(GITHUB_ACTIONS, "Tests not suitable for GitHub Actions")
class AccountTests(CalcusCloudLiveServer):

    def test_register_researcher(self):
        self.logout()
        self.register(
            "researcher", "selenium@calcus.cloud", "MySuperSafePassword", False
        )
        u = User.objects.latest("pk")
        self.assertEqual(u.email, "selenium@calcus.cloud")
        self.assertFalse(u.opted_in_emails)

        self.assertEqual(u.project_set.count(), 1)
        proj = u.project_set.first()
        self.assertEqual(proj.name, "My Main Project")

    def test_register_researcher_emails(self):
        self.logout()
        self.register(
            "researcher", "selenium@calcus.cloud", "MySuperSafePassword", True
        )

        u = User.objects.latest("pk")
        self.assertEqual(u.email, "selenium@calcus.cloud")
        self.assertTrue(u.opted_in_emails)


@skipIf(GITHUB_ACTIONS, "Tests not suitable for GitHub Actions")
class GroupTests(CalcusCloudLiveServer):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_create_research_group(self):
        sub = Subscription.objects.create(
            subscriber=self.user,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1),
        )

        self.create_research_group("Test Group")

        self.assertEqual(ResearchGroup.objects.count(), 1)

        g = ResearchGroup.objects.latest("pk")
        self.assertEqual(g.PI, self.user)

        self.assertEqual(
            len(
                self.driver.find_elements(
                    By.CSS_SELECTOR, "#research_group_div > div.column"
                )
            ),
            1,
        )

    def test_create_research_group_no_subscription(self):
        self.create_research_group("Test Group")

        self.assertEqual(ResearchGroup.objects.count(), 0)

    def test_dissolve_research_group(self):
        sub = Subscription.objects.create(
            subscriber=self.user,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1),
        )

        self.create_research_group("Test Group")

        self.assertEqual(ResearchGroup.objects.count(), 1)

        self.dissolve_research_group()

        self.assertEqual(ResearchGroup.objects.count(), 0)

    def test_create_class(self):
        sub = Subscription.objects.create(
            subscriber=self.user,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1),
        )

        self.create_class("Test Class")

        self.assertEqual(ClassGroup.objects.count(), 1)

        g = ClassGroup.objects.latest("pk")
        self.assertEqual(g.professor, self.user)

    def test_create_class_no_subscription(self):
        self.create_class("Test Class")

        self.assertEqual(ResearchGroup.objects.count(), 0)

    def test_dissolve_class(self):
        sub = Subscription.objects.create(
            subscriber=self.user,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1),
        )

        self.create_class("Test Class")

        self.assertEqual(ClassGroup.objects.count(), 1)

        self.dissolve_class("Test Class")

        self.assertEqual(ClassGroup.objects.count(), 0)


@skipIf(GITHUB_ACTIONS, "Tests not suitable for GitHub Actions")
class StripeTests(CalcusCloudLiveServer):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        self.__class__._restart_driver()
        super().setUp()

    def test_subscribe_valid(self):
        self.assertFalse(self.user.is_subscriber)
        self.assertEqual(self.user.allocated_seconds, 100)

        self.assertEqual(self.user.stripe_cus_id, "")
        self.subscribe("researcher", self.user.email, "4242424242424242")

        for i in range(4):
            self.user.refresh_from_db()
            time.sleep(0.5)
            if self.user.is_subscriber:
                break

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_subscriber)
        self.assertEqual(
            self.user.allocated_seconds, settings.SUBSCRIBER_COMP_SECONDS + 100
        )
        self.assertNotEqual(self.user.stripe_cus_id, "")

        sub = self.user.active_subscription
        self.assertTrue(sub is not None)

        end = timezone.make_aware(datetime.datetime.utcnow()) + datetime.timedelta(
            days=31
        )
        self.assertTrue(sub.end_date - end < datetime.timedelta(minutes=5))

    def test_subscribe_valid_team(self):
        self.assertFalse(self.user.is_subscriber)
        self.assertEqual(self.user.allocated_seconds, 100)

        self.assertEqual(self.user.stripe_cus_id, "")
        self.subscribe("team", self.user.email, "4242424242424242")

        for i in range(4):
            self.user.refresh_from_db()
            time.sleep(0.5)
            if self.user.is_subscriber:
                break

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_subscriber)
        self.assertTrue(self.user.stripe_will_renew)
        self.assertEqual(
            self.user.allocated_seconds, settings.SUBSCRIBER_TEAM_COMP_SECONDS + 100
        )
        self.assertNotEqual(self.user.stripe_cus_id, "")

        sub = self.user.active_subscription
        self.assertTrue(sub is not None)

        end = timezone.make_aware(datetime.datetime.utcnow()) + datetime.timedelta(
            days=31
        )
        self.assertTrue(sub.end_date - end < datetime.timedelta(minutes=5))

    def test_subscribe_invalid(self):
        self.assertFalse(self.user.is_subscriber)
        self.assertEqual(self.user.allocated_seconds, 100)

        self.assertEqual(self.user.stripe_cus_id, "")
        with self.assertRaises(selenium.common.exceptions.TimeoutException):
            self.subscribe("researcher", self.user.email, "4000000000000002")

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_subscriber)
        self.assertEqual(self.user.allocated_seconds, 100)

        sub = self.user.active_subscription
        self.assertTrue(sub is None)

    def test_subscribe_and_cancel(self):
        self.assertFalse(self.user.is_subscriber)
        self.assertEqual(self.user.allocated_seconds, 100)

        self.assertEqual(self.user.stripe_cus_id, "")
        self.subscribe("researcher", self.user.email, "4242424242424242")

        for i in range(8):
            self.user.refresh_from_db()
            time.sleep(0.5)
            if self.user.is_subscriber:
                break

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_subscriber)
        self.assertTrue(self.user.stripe_will_renew)

        self.lget("/profile/")

        btn = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located((By.ID, "manage_sub"))
        )
        btn.click()

        cancel_btn = WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-test="cancel-subscription"]')
            )
        )
        cancel_btn.click()
        confirm_btn = WebDriverWait(self.driver, 2).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="confirm"]'))
        )
        confirm_btn.send_keys(Keys.ENTER)

        try:
            reason_btn = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'button[name="cancellation_reason_cancel"]')
                )
            )
            reason_btn.click()
        except selenium.common.exceptions.TimeoutException:
            pass

        self.lget("/profile/")

        self.user.refresh_from_db()
        self.assertFalse(self.user.stripe_will_renew)

    # Subscribe without being logged in or having an account
    # Test duplicated webhook calls?

    def tearDown(self):
        # Confirm we want to leave the Stripe website, if necessary
        self.driver.get(f"{self.live_server_url}/")
        try:
            self.driver.switch_to.alert.accept()
        except selenium.common.exceptions.NoAlertPresentException:
            pass

    def test_subscribe_yearly(self):
        self.assertFalse(self.user.is_subscriber)
        self.assertEqual(self.user.allocated_seconds, 100)

        self.assertEqual(self.user.stripe_cus_id, "")
        self.subscribe("researcher", self.user.email, "4242424242424242", length="year")

        for i in range(8):
            self.user.refresh_from_db()
            time.sleep(0.5)
            if self.user.is_subscriber:
                break

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_subscriber)
        self.assertEqual(
            self.user.allocated_seconds, settings.SUBSCRIBER_COMP_SECONDS + 100
        )
        self.assertNotEqual(self.user.stripe_cus_id, "")

        sub = self.user.active_subscription
        self.assertTrue(sub is not None)

        end = timezone.make_aware(datetime.datetime.utcnow()) + datetime.timedelta(
            days=366
        )
        self.assertTrue(sub.end_date - end < datetime.timedelta(minutes=5))

    def test_subscribe_not_logged_in_existing_account(self):
        self.logout()

        self.subscribe("researcher", self.user.email, "4242424242424242")

        for i in range(8):
            time.sleep(0.5)
            self.user.refresh_from_db()
            if self.user.is_subscriber:
                break

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_subscriber)
        self.assertEqual(
            self.user.allocated_seconds, settings.SUBSCRIBER_COMP_SECONDS + 100
        )
        self.assertNotEqual(self.user.stripe_cus_id, "")

        sub = self.user.active_subscription
        self.assertTrue(sub is not None)

        end = timezone.make_aware(datetime.datetime.utcnow()) + datetime.timedelta(
            days=31
        )
        self.assertTrue(sub.end_date - end < datetime.timedelta(minutes=5))

    def test_subscribe_not_logged_in_new_account(self):
        self.logout()

        self.subscribe("researcher", "selenium_work@calcus.cloud", "4242424242424242")

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_subscriber)
        self.assertNotEqual(
            self.user.allocated_seconds, settings.SUBSCRIBER_COMP_SECONDS
        )
        self.assertEqual(self.user.stripe_cus_id, "")

        last_user = User.objects.latest("pk")
        self.assertEqual(last_user.email, "selenium_work@calcus.cloud")
        self.assertTrue(last_user.is_subscriber)
        self.assertEqual(last_user.allocated_seconds, settings.SUBSCRIBER_COMP_SECONDS)
        self.assertNotEqual(last_user.stripe_cus_id, "")

        sub = last_user.active_subscription
        self.assertTrue(sub is not None)

        end = timezone.make_aware(datetime.datetime.utcnow()) + datetime.timedelta(
            days=31
        )
        self.assertTrue(sub.end_date - end < datetime.timedelta(minutes=5))

    def test_subscribe_significant_time_allocated(self):
        self.assertFalse(self.user.is_subscriber)
        self.user.allocated_seconds = 3600 * 400
        self.user.save()

        self.assertEqual(self.user.stripe_cus_id, "")
        self.subscribe("researcher", self.user.email, "4242424242424242")

        for i in range(8):
            self.user.refresh_from_db()
            time.sleep(0.5)
            if self.user.is_subscriber:
                break

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_subscriber)
        self.assertEqual(self.user.allocated_seconds, 3600 * 400 + 3600 * 60)
        self.assertNotEqual(self.user.stripe_cus_id, "")

        sub = self.user.active_subscription
        self.assertTrue(sub is not None)

        end = timezone.make_aware(datetime.datetime.utcnow()) + datetime.timedelta(
            days=31
        )
        self.assertTrue(sub.end_date - end < datetime.timedelta(minutes=5))

    def test_subscribe_twice(self):
        import stripe

        self.assertFalse(self.user.is_subscriber)
        self.assertEqual(self.user.stripe_cus_id, "")
        self.assertEqual(self.user.allocated_seconds, 100)

        self.subscribe("researcher", self.user.email, "4242424242424242")

        for i in range(8):
            self.user.refresh_from_db()
            time.sleep(0.5)
            if self.user.is_subscriber:
                break

        self.user.refresh_from_db()

        first_id = self.user.stripe_cus_id

        self.assertEqual(ResourceAllocation.objects.count(), 1)
        customer = stripe.Customer.retrieve(self.user.stripe_cus_id)
        subs = stripe.Subscription.list(
            customer=self.user.stripe_cus_id, status="active"
        )
        self.assertEqual(len(subs["data"]), 1)

        # The "subscribe" button will be disabled
        with self.assertRaises(selenium.common.exceptions.TimeoutException):
            self.subscribe("researcher", self.user.email, "4242424242424242")

        self.user.refresh_from_db()
        self.assertEqual(self.user.stripe_cus_id, first_id)

        subs = stripe.Subscription.list(
            customer=self.user.stripe_cus_id, status="active"
        )
        self.assertEqual(len(subs["data"]), 1)

        self.assertEqual(ResourceAllocation.objects.count(), 1)

    # TODO: make this work
    """
    def test_custom_subscription(self):
        import stripe

        self.assertFalse(self.user.is_subscriber)
        self.assertEqual(self.user.stripe_cus_id, "")
        self.assertEqual(self.user.allocated_seconds, 100)

        link =stripe.PaymentLink.create(
                line_items=[{"price": "price_1OZaSiDOp6QF0VwnB2VHIad8", "quantity": 1}]
        )


        self.driver.get(link["url"])


        #### duplicated
        email = self.user.email
        card_number = "4242424242424242"

        #
        cardNumber = WebDriverWait(self.driver, 4).until(
            EC.presence_of_element_located((By.ID, "cardNumber"))
        )
        cardNumber.send_keys(card_number)

        # The email is autofilled if the user is logged in
        try:
            email_field = self.driver.find_element(By.ID, "email")
            if not email_field.get_property("readonly"):
                email_field.send_keys(email)
        except selenium.common.exceptions.NoSuchElementException:
            # It seems like the filled field does not have the same ID
            pass

        self.driver.find_element(By.ID, "cardExpiry").send_keys("0140")
        self.driver.find_element(By.ID, "cardCvc").send_keys("123")
        self.driver.find_element(By.ID, "billingName").send_keys("Selenium Robot")
        self.driver.find_element(By.ID, "billingPostalCode").send_keys("123 456")

        self.driver.find_element(By.CSS_SELECTOR, ".SubmitButton").click()


        ##### END DUP

        for i in range(10):
            self.user.refresh_from_db()
            time.sleep(1)
            if self.user.is_subscriber:
                break

        self.user.refresh_from_db()
        self.lget("/profile/")

        first_id = self.user.stripe_cus_id

        self.assertEqual(ResourceAllocation.objects.count(), 1)
        customer = stripe.Customer.retrieve(self.user.stripe_cus_id)
        subs = stripe.Subscription.list(customer=self.user.stripe_cus_id, status="active")
        self.assertEqual(len(subs['data']), 1)

        # The "subscribe" button will be disabled
        with self.assertRaises(selenium.common.exceptions.TimeoutException):
            self.subscribe("researcher", email, card_number)

        self.user.refresh_from_db()
        self.assertEqual(self.user.stripe_cus_id, first_id)

        subs = stripe.Subscription.list(customer=self.user.stripe_cus_id, status="active")
        self.assertEqual(len(subs['data']), 1)

        self.assertEqual(ResourceAllocation.objects.count(), 1)

        alloc = ResourceAllocation.objects.first()
        self.assertEqual(alloc.allocation_seconds, 120*3600)
        
        self.assertEqual(self.user.allocated_seconds, 120*3600)
    """


@skipIf(GITHUB_ACTIONS, "Tests not suitable for GitHub Actions")
class GeneralIntegrationTests(CalcusCloudLiveServer):
    def setUp(self):
        super().setUp()

        g = ResearchGroup.objects.create(name="Test Group", PI=self.user)

        self.login(self.email, self.password)
        self.user.allocated_seconds = 10000
        self.user.save()

    def test_selective_delete(self):
        self.assertTrue(self.try_assert_number_unseen_calcs(0, 3))
        params = {
            "mol_name": "H2",
            "name": "H2",
            "type": "Geometrical Optimisation",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "H2.sdf",
            "interface": "simple",
        }

        self.lget("/launch/")
        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(60)

        self.assertTrue(self.try_assert_number_unseen_calcs(1, 3))
        self.assertTrue(self.get_number_unseen_calcs_manually(), 1)
        self.click_latest_calc()
        self.launch_ensemble_next_step()

        with self.assertRaises(selenium.common.exceptions.NoSuchElementException):
            load_mol = self.driver.find_element(By.ID, "nih_name")

        params = {
            "type": "Frequency Calculation",
            "project": "SeleniumProject",
            "interface": "simple",
        }
        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(60)

        self.assertTrue(self.try_assert_number_unseen_calcs(1, 3))
        self.assertEqual(self.get_number_unseen_calcs_manually(), 1)

        self.lget("/launch/")
        params = {
            "mol_name": "Ethanol",
            "name": "Ethanol",
            "type": "Geometrical Optimisation",
            "project": "SeleniumProject",
            "in_file": "ethanol.xyz",
            "interface": "simple",
        }
        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(150)
        self.assertEqual(self.get_number_calc_orders(), 3)
        self.assertTrue(self.try_assert_number_unseen_calcs(2, 3))
        self.assertEqual(self.get_number_unseen_calcs_manually(), 2)

        self.lget("/projects/")
        n_mol = self.get_number_calcs_in_project("SeleniumProject")

        self.assertEqual(n_mol, 2)

        self.click_project("SeleniumProject")

        n_e = self.get_number_calcs_in_molecule("H2")

        self.assertEqual(n_e, 2)

        n_e = self.get_number_calcs_in_molecule("Ethanol")

        self.assertEqual(n_e, 2)

        self.delete_molecule("Ethanol")
        self.lget("/calculations/")
        ind = 0
        while ind < 5:
            if self.get_number_calc_orders() == 2:
                break
            ind += 1
            time.sleep(1)
            self.lget("/calculations/")
        self.assertEqual(self.get_number_calc_orders(), 2)

        self.lget("/projects/")
        self.assertEqual(self.get_number_projects(), 1)
        self.assertTrue(self.try_assert_number_unseen_calcs(1, 3))

        n_mol = self.get_number_calcs_in_project("SeleniumProject")
        self.assertEqual(n_mol, 1)

        self.click_project("SeleniumProject")
        self.assertEqual(self.get_number_molecules(), 1)

        n_e = self.get_number_calcs_in_molecule("H2")
        self.assertEqual(n_e, 2)

        self.click_molecule("H2")
        self.assertEqual(self.get_number_ensembles(), 2)

        self.lget("/launch/")
        params = {
            "mol_name": "Methane",
            "type": "Geometrical Optimisation",
            "project": "SeleniumProject",
            "in_file": "CH4.xyz",
            "interface": "simple",
        }
        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(150)
        self.assertEqual(self.get_number_calc_orders(), 3)
        self.assertTrue(self.try_assert_number_unseen_calcs(2, 3))
        self.assertEqual(self.get_number_unseen_calcs_manually(), 2)

        self.lget("/launch/")
        params = {
            "mol_name": "Ammonia",
            "name": "NH3",
            "type": "Geometrical Optimisation",
            "project": "SeleniumProject",
            "in_file": "NH3.mol",
            "interface": "simple",
        }
        self.calc_input_params(params)
        self.calc_launch()
        self.wait_latest_calc_done(150)
        self.assertEqual(self.get_number_calc_orders(), 4)
        self.assertTrue(self.try_assert_number_unseen_calcs(3, 3))
        self.assertEqual(self.get_number_unseen_calcs_manually(), 3)

        self.lget("/projects/")
        n_mol = self.get_number_calcs_in_project("SeleniumProject")

        self.assertEqual(n_mol, 3)

        self.click_project("SeleniumProject")
        self.click_molecule("Ammonia")
        self.delete_ensemble("NH3")
        self.driver.refresh()
        self.assertEqual(self.get_number_ensembles(), 1)
        self.delete_ensemble("File Upload")  # Should not delete molecule

        self.lget("/calculations/")

        self.assertEqual(self.get_number_calc_orders(), 3)
        self.assertTrue(self.try_assert_number_unseen_calcs(2, 3))
        self.assertEqual(self.get_number_unseen_calcs_manually(), 2)

        self.lget("/projects/")
        self.delete_project("SeleniumProject")
        time.sleep(2)
        self.lget("/projects/")
        self.assertTrue(self.try_assert_number_unseen_calcs(0, 3))

    # Some elements might be hidden in the cloud version.
    # We want to check if general actions still work.
    def test_create_empty_project(self):
        self.setup_test_group()
        self.lget("/projects/")

        self.create_empty_project()

        self.wait_for_ajax()

        self.assertEqual(self.get_number_projects(), 1)
        self.assertEqual(self.get_name_projects()[0], "My Project")

    def test_rename_project(self):
        self.setup_test_group()
        self.lget("/projects/")

        self.create_empty_project()

        self.wait_for_ajax()

        project = self.get_projects()[0]
        self.rename_project(project, "Test Project")
        self.lget("/projects/")

        self.assertEqual(self.get_number_projects(), 1)

        ind = 0
        while ind < 3:
            if self.get_name_projects()[0] == "Test Project":
                break
            ind += 1
            time.sleep(1)
        self.assertEqual(self.get_name_projects()[0], "Test Project")

    def test_rename_project2(self):
        self.setup_test_group()
        self.lget("/projects/")

        self.create_empty_project()

        self.wait_for_ajax()

        project = self.get_projects()[0]
        self.rename_project2(project, "Test Project")
        self.lget("/projects/")

        self.assertEqual(self.get_number_projects(), 1)

        ind = 0
        while ind < 3:
            if self.get_name_projects()[0] == "Test Project":
                break
            ind += 1
            time.sleep(1)

    def test_rename_molecule(self):
        self.setup_test_group()
        self.lget("/projects/")

        proj = Project.objects.create(name="Test Project", author=self.user)
        mol = Molecule.objects.create(name="Test molecule", project=proj)
        self.lget("/projects/")
        self.click_project("Test Project")

        mol = self.get_molecules()[0]
        self.rename_molecule(mol, "My Molecule")

        self.lget("/projects/")
        self.click_project("Test Project")

        self.assertEqual(self.get_number_molecules(), 1)
        self.assertEqual(self.get_name_molecules()[0], "My Molecule")

    def test_rename_molecule2(self):
        self.setup_test_group()
        self.lget("/projects/")

        proj = Project.objects.create(name="Test Project", author=self.user)
        mol = Molecule.objects.create(name="Test molecule", project=proj)
        self.lget("/projects/")
        self.click_project("Test Project")

        mol = self.get_molecules()[0]
        self.rename_molecule2(mol, "My Molecule")

        self.lget("/projects/")
        self.click_project("Test Project")

        self.assertEqual(self.get_number_molecules(), 1)
        self.assertEqual(self.get_name_molecules()[0], "My Molecule")
