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


class Command(BaseCommand):
    help = "Refreshes the cached information about projects and molecules, such as the calculation statistics"

    def handle(self, *args, **options):
        for profile in Profile.objects.all():
            profile.unseen_calculations = 0
            for o in profile.calculationorder_set.all():
                if o.new_status:
                    profile.unseen_calculations += 1
            profile.save()

        for proj in Project.objects.all():
            dnum = {}
            dcompleted = {}
            dqueued = {}
            drunning = {}

            molecules = proj.molecule_set.all()
            num = 0
            completed = 0
            queued = 0
            running = 0

            for mol in molecules:
                dnum[mol.id] = 0
                dcompleted[mol.id] = 0
                dqueued[mol.id] = 0
                drunning[mol.id] = 0

            for o in proj.calculationorder_set.all():
                num += o.calculation_set.count()
                for c in o.calculation_set.all():
                    s = c.status
                    if s == 0:
                        queued += 1
                    elif s == 1:
                        running += 1
                    else:
                        completed += 1
                if o.ensemble != None:
                    mol = o.ensemble.parent_molecule
                    if mol is not None:
                        dnum[mol.id] += o.calculation_set.count()
                        for c in o.calculation_set.all():
                            s = c.status
                            if s == 0:
                                dqueued[mol.id] += 1
                            elif s == 1:
                                drunning[mol.id] += 1
                            else:
                                dcompleted[mol.id] += 1
                elif o.structure != None:
                    mol = o.structure.parent_ensemble.parent_molecule
                    if mol is not None:
                        dnum[mol.id] += o.calculation_set.count()
                        for c in o.calculation_set.all():
                            s = c.status
                            if s == 0:
                                dqueued[mol.id] += 1
                            elif s == 1:
                                drunning[mol.id] += 1
                            else:
                                dcompleted[mol.id] += 1

            proj.num_calc = num
            proj.num_calc_queued = queued
            proj.num_calc_running = running
            proj.num_calc_completed = completed
            proj.save()

            for mol in molecules:
                mol.num_calc = dnum[mol.id]
                mol.num_calc_queued = dqueued[mol.id]
                mol.num_calc_running = drunning[mol.id]
                mol.num_calc_completed = dcompleted[mol.id]
                mol.save()
