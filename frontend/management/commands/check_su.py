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

su_name = os.environ.get("CALCUS_SU_NAME", "")


class Command(BaseCommand):
    help = "Verifies if the default superuser account is created"

    def handle(self, *args, **options):
        if su_name == "":
            print("No superuser name provided, creation aborted")
            return
        try:
            su = User.objects.get(username=su_name)
        except User.DoesNotExist:
            su = User.objects.create_superuser(username=su_name, password="default")
            print("Superuser with name '{}' created".format(su_name))
        else:
            print("Superuser account found, creation aborted")
