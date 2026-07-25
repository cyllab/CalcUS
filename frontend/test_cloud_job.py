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
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase

from .cloud_job import create_container_job, submit_cloud_job
from .helpers import can_run_in_sync_gunicorn_timeout


class SubmitCloudJobRoutingTests(SimpleTestCase):
    def setUp(self):
        self.calc = mock.Mock()
        self.calc.id = "calc-1"

    def test_single_core_uses_http_when_within_gunicorn_timeout(self):
        with mock.patch.dict(os.environ, {"GUNICORN_TIMEOUT": "60"}):
            with mock.patch("frontend.cloud_job.job_triage", return_value=(1, 10)):
                with mock.patch(
                    "frontend.cloud_job.send_gcloud_task"
                ) as send_task, mock.patch(
                    "frontend.cloud_job.create_container_job"
                ) as create_container_job:
                    submit_cloud_job(self.calc)

        send_task.assert_called_once_with("/cloud_calc/", "calc-1")
        create_container_job.assert_not_called()

    def test_single_core_uses_http_in_test_environment(self):
        with mock.patch("frontend.cloud_job.IS_TEST", True), mock.patch(
            "frontend.cloud_job.job_triage", return_value=(1, 300)
        ), mock.patch("frontend.cloud_job.send_gcloud_task") as send_task, mock.patch(
            "frontend.cloud_job.create_container_job"
        ) as create_container_job:
            submit_cloud_job(self.calc)

        send_task.assert_called_once_with("/cloud_calc/", "calc-1")
        create_container_job.assert_not_called()

    @mock.patch("frontend.cloud_job.IS_TEST", False)
    def test_single_core_uses_batch_when_exceeding_gunicorn_timeout(self):
        # Exercise production routing. Integration tests intentionally keep
        # single-core jobs on the Cloud Tasks emulator.
        with mock.patch.dict(os.environ, {"GUNICORN_TIMEOUT": "30"}):
            with mock.patch("frontend.cloud_job.job_triage", return_value=(1, 31)):
                with mock.patch(
                    "frontend.cloud_job.send_gcloud_task"
                ) as send_task, mock.patch(
                    "frontend.cloud_job.create_container_job"
                ) as create_container_job:
                    submit_cloud_job(self.calc)

        create_container_job.assert_called_once_with(self.calc, 1, 31)
        send_task.assert_not_called()

    def test_multi_core_still_uses_batch(self):
        with mock.patch.dict(os.environ, {"GUNICORN_TIMEOUT": "1000"}):
            with mock.patch("frontend.cloud_job.job_triage", return_value=(4, 10)):
                with mock.patch(
                    "frontend.cloud_job.send_gcloud_task"
                ) as send_task, mock.patch(
                    "frontend.cloud_job.create_container_job"
                ) as create_container_job:
                    submit_cloud_job(self.calc)

        create_container_job.assert_called_once_with(self.calc, 4, 10)
        send_task.assert_not_called()

    def test_batch_job_uses_configured_spot_retry_count(self):
        calc = mock.Mock()
        calc.id = "calc-1"
        calc.order.author.user_type = "trial"
        batch = mock.MagicMock()

        cloud_settings = {
            "COMPUTE_IMAGE": "compute-image",
            "COMPUTE_SERVICE_ACCOUNT": "compute@example.com",
            "GCP_PROJECT_ID": "test-project",
            "GCP_LOCATION": "us-central1",
            "GCP_BATCH_SPOT_MAX_RETRIES": 5,
        }
        with mock.patch("frontend.cloud_job.batch_v1", batch, create=True):
            with mock.patch.multiple(settings, create=True, **cloud_settings):
                create_container_job(calc, 4, 60)

        self.assertEqual(batch.TaskSpec.return_value.max_retry_count, 5)
        environment = batch.Environment.return_value.variables
        variables = environment.update.call_args.args[0]
        self.assertEqual(variables["CALCUS_BATCH_MAX_RETRIES"], "5")


class GunicornTimeoutHelperTests(SimpleTestCase):
    def test_can_run_in_sync_gunicorn_timeout(self):
        with mock.patch.dict(os.environ, {"GUNICORN_TIMEOUT": "60"}):
            self.assertTrue(can_run_in_sync_gunicorn_timeout(29))
            self.assertFalse(can_run_in_sync_gunicorn_timeout(30))

    def test_can_run_in_sync_gunicorn_timeout_invalid_value(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(can_run_in_sync_gunicorn_timeout(10))

        with mock.patch.dict(os.environ, {"GUNICORN_TIMEOUT": "invalid"}):
            self.assertFalse(can_run_in_sync_gunicorn_timeout(10))
