import glob
import os
from django.core.management.base import BaseCommand
from frontend.models import *


class Command(BaseCommand):
    help = 'Refreshes the cached information about projects and molecules, such as the calculation statistics'


    def handle(self, *args, **options):
        for proj in Project.objects.all():
            num = 0
            completed = 0
            queued = 0
            running = 0
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

            save = False
            if proj.num_calc != num:
                proj.num_calc = num
                save = True
            if proj.num_calc_queued != queued:
                proj.num_calc_queued = queued
                save = True
            if proj.num_calc_running != running:
                proj.num_calc_running = running
                save = True
            if proj.num_calc_completed != completed:
                proj.num_calc_completed = completed
                save = True
            if save:
                proj.save()
