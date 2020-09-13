import glob
import os
from django.core.management.base import BaseCommand
from frontend.models import *


class Command(BaseCommand):
    help = 'Refreshes the cached information about projects and molecules, such as the calculation statistics'


    def handle(self, *args, **options):
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

