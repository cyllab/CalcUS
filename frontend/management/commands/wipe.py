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

import glob
import os
from django.core.management.base import BaseCommand
from frontend.models import *

try:
    os.environ["CALCUS_TEST"]
except:
    is_test = False
else:
    is_test = True


class Command(BaseCommand):
    help = "Wipes the database of calculations and projects"

    def handle(self, *args, **options):
        a = input("Are you sure you want to wipe the database?")
        if a == "yes":
            for m in Molecule.objects.all():
                m.delete()
            for c in Calculation.objects.all():
                c.delete()
            for p in Project.objects.all():
                p.delete()
