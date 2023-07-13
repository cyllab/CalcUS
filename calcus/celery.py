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


from __future__ import absolute_import, unicode_literals

import os
from datetime import datetime
from django.conf import settings

if "CALCUS_CLOUD" not in os.environ:
    from celery import Celery
    from celery.schedules import crontab

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calcus.settings")

    if "CI" in os.environ:
        app = Celery(
            "calcus",
            backend="redis://localhost:6379/1",
            broker="redis://localhost:6379/0",
        )
    else:
        app = Celery(
            "calcus", backend="redis://redis:6379/1", broker="redis://redis:6379/0"
        )

    app.autodiscover_tasks()

    @app.task(bind=True)
    def debug_task(self):
        print(f"Request: {self.request!r}")

    if not settings.IS_TEST:
        app.conf.beat_schedule = {
            "backup-db": {
                "task": "frontend.tasks.backup_db",
                "schedule": crontab(hour=16, minute=30),
                "options": {
                    "expires": int(settings.DBBACKUP_INTERVAL * 24 * 3600),
                },
            },
        }

        if settings.PING_SATELLITE.lower() == "true":
            app.conf.beat_schedule = {
                "ping-satellite": {
                    "task": "frontend.tasks.ping_satellite",
                    "schedule": crontab(minute=(datetime.now().minute + 1) % 60),
                    "options": {
                        "expires": 3600,
                    },
                },
            }
