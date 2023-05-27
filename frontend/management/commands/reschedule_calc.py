import glob
import os
from django.core.management.base import BaseCommand

from frontend.models import *
from frontend.environment_variables import *
from frontend.cloud_job import submit_cloud_job


class Command(BaseCommand):
    help = "Runs a calculation"

    def add_arguments(self, parser):
        parser.add_argument("calc_id", type=str)

    def handle(self, *args, **options):
        calc_id = options["calc_id"]
        try:
            calc = Calculation.objects.get(pk=calc_id)
        except Calculation.DoesNotExist:
            raise Exception(f"Could not find calculation number {calc_id}")

        if calc.status == 2:  # If successful
            print(
                f"Calculation {calc_id} has already completed successfully! This shouldn't happen"
            )
            return

        submit_cloud_job(calc)

        calc.status = 0
        calc.save()

        print(f"Calculation {calc_id} has been rescheduled")
