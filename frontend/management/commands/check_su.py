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

from django.core.management.base import BaseCommand
from frontend.models import *

su_email = os.environ.get("CALCUS_SU_EMAIL", "")


class Command(BaseCommand):
    help = "Verifies if the default superuser account is created"

    def handle(self, *args, **options):
        if su_email == "":
            print("No superuser name provided, creation aborted")
            return
        try:
            su = User.objects.get(email=su_email)
        except User.DoesNotExist:
            su = User.objects.create_superuser(email=su_email, password="default")
            print(f"Superuser with email '{su_email}' created")
        else:
            print("Superuser account found, creation aborted")
