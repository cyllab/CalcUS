import glob
import os
from django.core.management.base import BaseCommand
from frontend.models import *

class Command(BaseCommand):
    help = 'Initializes the procedures'

    def is_absent(self, cls, name):

        try:
            a = cls.objects.get(name=name)
        except cls.DoesNotExist:
            return True
        else:
            return False

    def handle(self, *args, **options):
        ###BasicStep creations

        ###Template:
        #name = "Geometrical Optimisation"
        #if self.is_absent(BasicStep, name):
        #    print("Adding BasicStep: {}".format(name))
        #    a = BasicStep.objects.create(name=name)

        name = "Geometrical Optimisation"
        if self.is_absent(BasicStep, name):
            print("Adding BasicStep: {}".format(name))
            a = BasicStep.objects.create(name=name)


        ###Procedure creations

        ###Template:
        #name = "Simple Optimisation"
        #if self.is_absent(Procedure, name):
        #    print("Adding Procedure: {}".format(name))
        #    a = Procedure.objects.create(name=name)

        name = "Simple Optimisation"
        if self.is_absent(Procedure, name):
            print("Adding Procedure: {}".format(name))
            a = Procedure.objects.create(name=name)
            a.save()

            s_opt = BasicStep.objects.get(name="Geometrical Optimisation")
            step1 = Step.objects.create(step_model=s_opt, parent_procedure=a, from_procedure=a)
            step1.save()

        ###Finishing the process
        self.verify

    def verify(self):
        for proc in Procedure.objects.all():
            assert proc.initial_steps != None

        for step in Step.objects.all():
            assert step.parent_step != None or step.parent_procedure != None

