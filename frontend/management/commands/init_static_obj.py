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
from django.core.management.base import BaseCommand
from django.conf import settings
import pathlib

filepath = pathlib.Path(__file__).parent.resolve()

showcase_dir = os.path.join(filepath.parent.parent, "showcases")
from frontend.models import *
from frontend.libxyz import format_xyz, parse_multixyz_from_file

try:
    os.environ["CALCUS_TEST"]
except:
    is_test = False
else:
    is_test = True


def get_showcase(name):
    with open(os.path.join(showcase_dir, name)) as f:
        data = "".join(f.readlines()).strip()
    return data


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

    def is_absent_property(self, name):
        try:
            prop = ShowcaseProperty.objects.get(name=name)
        except ShowcaseProperty.DoesNotExist:
            print(f"ShowcaseProperty {name} does not already exist")
            return True
        else:
            return False

    def is_absent_ensemble(self, label):
        try:
            e = ShowcaseEnsemble.objects.get(label=label)
        except ShowcaseEnsemble.DoesNotExist:
            print(f"ShowcaseEnsemble {label} does not already exist")
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
        prop_name,
        **kwargs,
    ):
        if self.is_absent(BasicStep, name):
            BasicStep.objects.create(
                name=name,
                short_name=short_name,
                prop_name=prop_name,
                **kwargs,
            )
        else:
            BasicStep.objects.filter(name=name).update(
                short_name=short_name,
                prop_name=prop_name,
                **kwargs,
            )

    def handle(self, *args, **options):
        ###BasicStep creations

        self.add_step(
            "Geometrical Optimisation",
            "opt",
            "Geometry",
            creates_ensemble=True,
        )

        self.add_step(
            "Conformational Search",
            "conf_search",
            "Conformer ensemble",
            creates_ensemble=True,
        )

        self.add_step(
            "Constrained Optimisation",
            "constr_opt",
            "Geometry with constraint",
            creates_ensemble=True,
        )

        self.add_step(
            "Frequency Calculation",
            "freq",
            "Vibrational modes, IR spectrum and thermochemistry",
            creates_ensemble=False,
        )

        self.add_step(
            "TS Optimisation",
            "optts",
            "Transition state geometry",
            creates_ensemble=True,
        )

        self.add_step(
            "UV-Vis Calculation",
            "uvvis",
            "UV-Vis spectrum",
            creates_ensemble=False,
        )

        self.add_step(
            "NMR Prediction",
            "nmr",
            "NMR spectrum",
            creates_ensemble=False,
        )

        self.add_step(
            "Single-Point Energy",
            "sp",
            "Electronic energy",
            creates_ensemble=False,
        )

        self.add_step(
            "MO Calculation",
            "mo",
            "Molecular Orbitals",
            creates_ensemble=False,
        )

        self.add_step(
            "Minimum Energy Path",
            "mep",
            "Minimum Energy Path",
            creates_ensemble=True,
        )

        self.add_step(
            "Constrained Conformational Search",
            "constr_conf_search",
            "Conformer ensemble with constraint",
            creates_ensemble=True,
        )

        self.add_step(
            "ESP Calculation",
            "esp",
            "Electrostatic potential map",
            creates_ensemble=False,
        )

        self.add_step(
            "Fast Conformational Search",
            "fast_conf_search",
            "Preliminary conformer ensemble",
            creates_ensemble=True,
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

        if not settings.IS_TEST:
            if self.is_absent_property("mo"):
                molden = get_showcase("mo_molden")
                mo_diagram = get_showcase("mo_diagram")
                prop = ShowcaseProperty.objects.create(
                    name="mo", molden=molden, mo_diagram=mo_diagram
                )

            if self.is_absent_ensemble("acetylsalicylic_acid"):
                e = ShowcaseEnsemble.objects.create(label="acetylsalicylic_acid")
                params = Parameters.objects.create(charge=0, multiplicity=1)
                multixyz, E = parse_multixyz_from_file(
                    os.path.join(showcase_dir, "Acetylsalicylic_Acid.xyz")
                )
                for ind, (xyz, ener) in enumerate(zip(multixyz, E)):
                    _xyz = format_xyz(xyz)
                    s = Structure.objects.create(
                        parent_ensemble=e, xyz_structure=_xyz, number=ind + 1
                    )
                    prop = ShowcaseProperty.objects.create(
                        energy=ener, parent_structure=s, parameters=params
                    )
