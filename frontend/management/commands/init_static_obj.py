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
    help = "Initializes the procedures"

    def is_absent(self, cls, name):
        try:
            a = cls.objects.get(name=name)
        except cls.DoesNotExist:
            return True
        else:
            return False

    def is_absent_title(self, cls, title):
        try:
            a = cls.objects.get(title=title)
        except cls.DoesNotExist:
            return True
        else:
            return False

    def print(self, txt):
        if not is_test:
            print(txt)

    def add_step(
        self,
        name,
        short_name,
        creates_ensemble=False,
        avail_xtb=False,
        avail_Gaussian=False,
        avail_ORCA=False,
    ):
        if self.is_absent(BasicStep, name):
            BasicStep.objects.create(
                name=name,
                short_name=short_name,
                creates_ensemble=creates_ensemble,
                avail_xtb=avail_xtb,
                avail_Gaussian=avail_Gaussian,
                avail_ORCA=avail_ORCA,
            )
        else:
            BasicStep.objects.filter(name=name).update(
                short_name=short_name,
                creates_ensemble=creates_ensemble,
                avail_xtb=avail_xtb,
                avail_Gaussian=avail_Gaussian,
                avail_ORCA=avail_ORCA,
            )

    def handle(self, *args, **options):
        ###BasicStep creations

        self.add_step(
            "Geometrical Optimisation",
            "opt",
            creates_ensemble=True,
            avail_xtb=True,
            avail_Gaussian=True,
            avail_ORCA=True,
        )

        self.add_step(
            "Conformational Search",
            "conf_search",
            creates_ensemble=True,
            avail_xtb=True,
            avail_Gaussian=False,
            avail_ORCA=False,
        )

        self.add_step(
            "Constrained Optimisation",
            "constr_opt",
            creates_ensemble=True,
            avail_xtb=True,
            avail_Gaussian=True,
            avail_ORCA=True,
        )

        self.add_step(
            "Frequency Calculation",
            "freq",
            creates_ensemble=False,
            avail_xtb=True,
            avail_Gaussian=True,
            avail_ORCA=True,
        )

        self.add_step(
            "TS Optimisation",
            "optts",
            creates_ensemble=True,
            avail_xtb=True,
            avail_Gaussian=True,
            avail_ORCA=True,
        )

        self.add_step(
            "UV-Vis Calculation",
            "uvvis",
            creates_ensemble=False,
            avail_xtb=True,
            avail_Gaussian=True,
            avail_ORCA=False,
        )

        self.add_step(
            "NMR Prediction",
            "nmr",
            creates_ensemble=False,
            avail_xtb=False,
            avail_Gaussian=True,
            avail_ORCA=True,
        )

        self.add_step(
            "Single-Point Energy",
            "sp",
            creates_ensemble=False,
            avail_xtb=True,
            avail_Gaussian=True,
            avail_ORCA=True,
        )

        self.add_step(
            "MO Calculation",
            "mo",
            creates_ensemble=False,
            avail_xtb=False,
            avail_Gaussian=False,
            avail_ORCA=True,
        )

        self.add_step(
            "Minimum Energy Path",
            "mep",
            creates_ensemble=True,
            avail_xtb=True,
            avail_Gaussian=False,
            avail_ORCA=False,
        )

        self.add_step(
            "Constrained Conformational Search",
            "constr_conf_search",
            creates_ensemble=True,
            avail_xtb=True,
            avail_Gaussian=False,
            avail_ORCA=False,
        )

        title = "NHC-Catalysed Condensation"
        if self.is_absent_title(Example, title):
            self.print(f"Adding Example: {title}")
            a = Example.objects.create(title=title, page_path="nhc_condensation.html")

        title = "NMR Prediction (Quick)"
        if self.is_absent_title(Recipe, title):
            self.print(f"Adding Recipe: {title}")
            a = Recipe.objects.create(
                title=title, page_path="nmr_prediction_quick.html"
            )
