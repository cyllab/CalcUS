import glob
import os
from django.core.management.base import BaseCommand
from frontend.models import *

try:
    os.environ['LAB_TEST']
except:
    is_test = False
else:
    is_test = True

class Command(BaseCommand):
    help = 'Wipes the database of calculations and projects'


    def handle(self, *args, **options):
        a = input("Are you sure you want to wipe the database?")
        if a == 'yes':
            for m in Molecule.objects.all():
                m.delete()
            for c in Calculation.objects.all():
                c.delete()
            for p in Project.objects.all():
                p.delete()
