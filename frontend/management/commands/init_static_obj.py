import glob
import os
from django.core.management.base import BaseCommand
from frontend.models import *

try:
    os.environ['CALCUS_TEST']
except:
    is_test = False
else:
    is_test = True

class Command(BaseCommand):
    help = 'Initializes the procedures'

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

    def add_step(self, name, short_name, creates_ensemble=False, avail_xtb=False, avail_Gaussian=False, avail_ORCA=False):
        if self.is_absent(BasicStep, name):
            BasicStep.objects.create(name=name, short_name=short_name, creates_ensemble=creates_ensemble, avail_xtb=avail_xtb, avail_Gaussian=avail_xtb, avail_ORCA=avail_ORCA)

    def handle(self, *args, **options):
        ###BasicStep creations

        self.add_step("Geometrical Optimisation", "opt", creates_ensemble=True, avail_xtb=True, avail_Gaussian=True, avail_ORCA=True)

        self.add_step("Conformational Search", "conf_search", creates_ensemble=True, avail_xtb=True, avail_Gaussian=False, avail_ORCA=False)

        self.add_step("Constrained Optimisation", "constr_opt", creates_ensemble=True, avail_xtb=True, avail_Gaussian=True, avail_ORCA=True)

        self.add_step("Frequency Calculation", "freq", creates_ensemble=False, avail_xtb=True, avail_Gaussian=True, avail_ORCA=True)

        self.add_step("TS Optimisation", "optts", creates_ensemble=True, avail_xtb=True, avail_Gaussian=True, avail_ORCA=True)

        self.add_step("UV-Vis Calculation", "uvvis", creates_ensemble=False, avail_xtb=True, avail_Gaussian=False, avail_ORCA=False)

        self.add_step("NMR Prediction", "nmr", creates_ensemble=False, avail_xtb=False, avail_Gaussian=True, avail_ORCA=True)

        self.add_step("Single-Point Energy", "sp", creates_ensemble=False, avail_xtb=True, avail_Gaussian=True, avail_ORCA=True)

        self.add_step("MO Calculation", "mo", creates_ensemble=False, avail_xtb=False, avail_Gaussian=False, avail_ORCA=True)

        self.add_step("Minimum Energy Path", "mep", creates_ensemble=True, avail_xtb=True, avail_Gaussian=False, avail_ORCA=False)

        self.add_step("Constrained Conformational Search", "constr_conf_search", creates_ensemble=True, avail_xtb=True, avail_Gaussian=False, avail_ORCA=False)

        title = "NHC-Catalysed Condensation"
        if self.is_absent_title(Example, title):
            self.print("Adding Example: {}".format(title))
            a = Example.objects.create(title=title, page_path="nhc_condensation.html")

        title = "NMR Prediction (Quick)"
        if self.is_absent_title(Recipe, title):
            self.print("Adding Recipe: {}".format(title))
            a = Recipe.objects.create(title=title, page_path="nmr_prediction_quick.html")

