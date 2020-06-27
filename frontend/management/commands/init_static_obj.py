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
            a = BasicStep.objects.create(name=name, desc="Calculating UV-Vis spectrum", error_message="Failed to calculate the UV-Vis spectrum", avail_xtb=True, avail_Gaussian=True, avail_ORCA=True)

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



        ###Procedure creations

        ###Template:
        #name = "Simple Optimisation"
        #if self.is_absent(Procedure, name):
        #    self.print("Adding Procedure: {}".format(name))
        #    a = Procedure.objects.create(name=name)

        '''
        name = "Simple Optimisation"
        if self.is_absent(Procedure, name):
            self.print("Adding Procedure: {}".format(name))
            a = Procedure.objects.create(name=name)
            a.avail_xtb = True
            a.avail_Gaussian = True

            s_opt = BasicStep.objects.get(name="Geometrical Optimisation")
            step1 = Step.objects.create(step_model=s_opt, parent_procedure=a, from_procedure=a)
            step1.save()
            a.save()

        name = "Conformational Search"
        if self.is_absent(Procedure, name):
            self.print("Adding Procedure: {}".format(name))
            a = Procedure.objects.create(name=name)

            a.avail_xtb = True
            s_opt = BasicStep.objects.get(name="Crest")
            step1 = Step.objects.create(step_model=s_opt, parent_procedure=a, from_procedure=a)
            step1.save()
            a.save()

        name = "Constrained Optimisation"
        if self.is_absent(Procedure, name):
            self.print("Adding Procedure: {}".format(name))
            a = Procedure.objects.create(name=name)
            a.avail_xtb = True
            a.avail_Gaussian = True

            s_opt = BasicStep.objects.get(name="Constrained Optimisation")
            step1 = Step.objects.create(step_model=s_opt, parent_procedure=a, from_procedure=a)
            step1.save()
            a.save()

        name = "Opt+Freq"
        if self.is_absent(Procedure, name):
            self.print("Adding Procedure: {}".format(name))
            a = Procedure.objects.create(name=name)

            a.avail_xtb = True
            a.avail_Gaussian = True

            s_opt = BasicStep.objects.get(name="Geometrical Optimisation")
            step1 = Step.objects.create(step_model=s_opt, parent_procedure=a, from_procedure=a)
            step1.save()

            s_freq = BasicStep.objects.get(name="Frequency Calculation")
            step2 = Step.objects.create(step_model=s_freq, parent_step=step1, from_procedure=a)
            step2.save()

            a.save()

        name = "TS+Freq"
        if self.is_absent(Procedure, name):
            self.print("Adding Procedure: {}".format(name))
            a = Procedure.objects.create(name=name)

            a.avail_xtb = True
            a.avail_Gaussian = True

            s_opt = BasicStep.objects.get(name="TS Optimisation")
            step1 = Step.objects.create(step_model=s_opt, parent_procedure=a, from_procedure=a)
            step1.save()

            s_freq = BasicStep.objects.get(name="Frequency Calculation")
            step2 = Step.objects.create(step_model=s_freq, parent_step=step1, from_procedure=a)
            step2.save()

            a.save()

        name = "Simple UV-Vis"
        if self.is_absent(Procedure, name):
            self.print("Adding Procedure: {}".format(name))
            a = Procedure.objects.create(name=name)

            a.avail_xtb = True
            s_opt = BasicStep.objects.get(name="Geometrical Optimisation")
            step1 = Step.objects.create(step_model=s_opt, parent_procedure=a, from_procedure=a)
            step1.save()

            s_freq = BasicStep.objects.get(name="UV-Vis Calculation")
            step2 = Step.objects.create(step_model=s_freq, parent_step=step1, from_procedure=a)
            step2.save()

            a.save()

        name = "MO Generation"
        if self.is_absent(Procedure, name):
            self.print("Adding Procedure: {}".format(name))
            a = Procedure.objects.create(name=name)

            a.avail_ORCA = True

            s_opt = BasicStep.objects.get(name="Geometrical Optimisation")
            step1 = Step.objects.create(step_model=s_opt, parent_procedure=a, from_procedure=a)
            step1.save()

            s_freq = BasicStep.objects.get(name="MO Calculation")
            step2 = Step.objects.create(step_model=s_freq, parent_step=step1, from_procedure=a)
            step2.save()

            a.save()

        name = "NMR Prediction"
        if self.is_absent(Procedure, name):
            self.print("Adding Procedure: {}".format(name))
            a = Procedure.objects.create(name=name)

            a.avail_xtb = True

            s_crest = BasicStep.objects.get(name="Crest Pre NMR")
            step1 = Step.objects.create(step_model=s_crest, parent_procedure=a, from_procedure=a)
            step1.save()

            s_enso = BasicStep.objects.get(name="Enso")
            step2 = Step.objects.create(step_model=s_enso, parent_step=step1, from_procedure=a, same_dir=True)
            step2.save()

            s_anmr = BasicStep.objects.get(name="Anmr")
            step3 = Step.objects.create(step_model=s_anmr, parent_step=step2, from_procedure=a, same_dir=True)
            step3.save()

            a.save()
        '''
        ###Finishing the process
        #self.verify()

        title = "Example 1: Simple equilibrium calculation"
        if self.is_absent_title(Example, title):
            self.print("Adding Example: {}".format(title))
            a = Example.objects.create(title=title, page_path="example1.html")

        title = "Example 2: Diaryliodonium complexation energies"
        if self.is_absent_title(Example, title):
            self.print("Adding Example: {}".format(title))
            a = Example.objects.create(title=title, page_path="example2.html")

        title = "Geometrical Optimisation"
        if self.is_absent_title(Exercise, title):
            self.print("Adding Exercise: {}".format(title))
            a = Exercise.objects.create(title=title, page_path="geometrical_optimisation.html")
            q1 = Question.objects.create(exercise=a, question="What is the equilibrium carbon-carbon bond length?", answer=1.38, tolerance=0.01)
            q2 = Question.objects.create(exercise=a, question="What is the equilibrium angle between three consecutive carbons?", answer=120.0, tolerance=0.5)

        title = "Frequency Calculation"
        if self.is_absent_title(Exercise, title):
            self.print("Adding Exercise: {}".format(title))
            a = Exercise.objects.create(title=title, page_path="frequency.html")
            q1 = Question.objects.create(exercise=a, question="What is the wavenumber of the lowest vibration mode?", answer=368.35, tolerance=3.)

        title = "Conformational Search"
        if self.is_absent_title(Exercise, title):
            self.print("Adding Exercise: {}".format(title))
            a = Exercise.objects.create(title=title, page_path="conformational_search.html")
            q1 = Question.objects.create(exercise=a, question="What is the free energy of the most stable conformer (Ha)?", answer=18.69417171, tolerance=0.0005)
            q2 = Question.objects.create(exercise=a, question="What is the weighted free energy of the ensemble (Ha)?", answer=-18.69355, tolerance=0.0005)

        title = "Constrained Optimisation"
        if self.is_absent_title(Exercise, title):
            self.print("Adding Exercise: {}".format(title))
            a = Exercise.objects.create(title=title, page_path="constrained_optimisation.html")
            q1 = Question.objects.create(exercise=a, question="What is the carbon-carbon distance near the transition state?", answer=1.94, tolerance=0.03)

        title = "Transition State Optimisation"
        if self.is_absent_title(Exercise, title):
            self.print("Adding Exercise: {}".format(title))
            a = Exercise.objects.create(title=title, page_path="transition_state.html")
            q1 = Question.objects.create(exercise=a, question="What is the wavenumber of the negative vibration mode of the transition state?", answer=-492.77, tolerance=10.)
            q2 = Question.objects.create(exercise=a, question="What is the free energy barrier of the rearrangement (kJ/mol)?", answer=92.98, tolerance=3.)


        title = "NMR Prediction (Quick)"
        if self.is_absent_title(Recipe, title):
            self.print("Adding Recipe: {}".format(title))
            a = Recipe.objects.create(title=title, page_path="nmr_prediction_quick.html")

    def verify(self):
        for proc in Procedure.objects.all():
            assert proc.initial_steps != None
            for step in proc.step_set.all():
                if step.step_model.name == "Frequency Calculation":
                    proc.has_freq = True
                elif step.step_model.name == "Anmr" or step.step_model.name == "Enso":
                    proc.has_nmr = True
                elif step.step_model.name == "UV-Vis Calculation":
                    proc.has_uvvis = True
                elif step.step_model.name == "MO Calculation":
                    proc.has_mo = True
        proc.save()

        for step in Step.objects.all():
            assert step.parent_step != None or step.parent_procedure != None

