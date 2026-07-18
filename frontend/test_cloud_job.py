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

from django.test import SimpleTestCase

from .cloud_job import submit_cloud_job
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

    def test_single_core_uses_batch_when_exceeding_gunicorn_timeout(self):
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
