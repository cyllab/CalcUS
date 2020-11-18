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

    def handle(self, *args, **options):
        ###BasicStep creations

        ###Template:
        #name = "Geometrical Optimisation"
        #if self.is_absent(BasicStep, name):
        #    self.print("Adding BasicStep: {}".format(name))
        #    a = BasicStep.objects.create(name=name)

        name = "Geometrical Optimisation"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Optimizing geometry", error_message="Failed to optimize geometry", creates_ensemble=True, avail_xtb=True, avail_Gaussian=True, avail_ORCA=True)

        name = "Conformational Search"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Finding conformers", error_message="Failed to find the conformers", creates_ensemble=True, avail_xtb=True)

        '''
        name = "Crest Pre NMR"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Finding conformers", error_message="Failed to find the conformers", creates_ensemble=True, avail_xtb=True)
        '''

        name = "Constrained Optimisation"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Optimizing geometry", error_message="Failed to optimize geometry", creates_ensemble=True, avail_xtb=True, avail_Gaussian=True, avail_ORCA=True)

        name = "Frequency Calculation"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Calculating frequencies", error_message="Failed to calculate frequencies", avail_xtb=True, avail_Gaussian=True, avail_ORCA=True)

        name = "TS Optimisation"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Optimizing the transition state", error_message="Failed to optimize the transition state", creates_ensemble=True, avail_xtb=True, avail_Gaussian=True, avail_ORCA=True)

        name = "UV-Vis Calculation"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Calculating UV-Vis spectrum", error_message="Failed to calculate the UV-Vis spectrum", avail_xtb=True)

        name = "NMR Prediction"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Calculating NMR shifts", error_message="Failed to calculate the NMR shifts", avail_Gaussian=True, avail_ORCA=True)

        name = "Single-Point Energy"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Calculating single-point energy", error_message="Failed to calculate single-point energy", avail_Gaussian=True, avail_ORCA=True, avail_xtb=True)

        '''
        name = "Enso"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Calculating NMR Spectrum", error_message="Failed to calculate the NMR spectrum")


        name = "Anmr"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Creating the final NMR Spectrum", error_message="Failed to create the final NMR spectrum", avail_xtb=True)

        '''

        name = "MO Calculation"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Creating the Molecular Orbitals", error_message="Failed to create the Molecular Orbitals", avail_ORCA=True)

        name = "Minimum Energy Path"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Finding the minimum energy path", creates_ensemble=True, error_message="Failed to converge the minimum energy path", avail_xtb=True)

        name = "Constrained Conformational Search"
        if self.is_absent(BasicStep, name):
            self.print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name, desc="Generating conformers", error_message="Failed to generate conformers", creates_ensemble=True, avail_xtb=True)


        ###Finishing the process

        title = "NHC-Catalysed Condensation"
        if self.is_absent_title(Example, title):
            self.print("Adding Example: {}".format(title))
            a = Example.objects.create(title=title, page_path="nhc_condensation.html")

        title = "NMR Prediction (Quick)"
        if self.is_absent_title(Recipe, title):
            self.print("Adding Recipe: {}".format(title))
            a = Recipe.objects.create(title=title, page_path="nmr_prediction_quick.html")

