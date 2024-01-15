import os
from django.core.management.base import BaseCommand

from frontend.models import *
from frontend.environment_variables import *
from frontend.tasks import run_calc


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

        nproc = os.getenv("OMP_NUM_THREADS")[0]
        if nproc > 1:
            os.system("/calcus/scripts/set_shm.sh")

        try:
            ret = run_calc(calc.id)
        except Exception as e:
            raise Exception(f"Calculation {calc.id} finished with exception {str(e)}")

        if ret != 0:
            print(f"Calculation {calc.id} finished with code {ret}")
            calc.refresh_from_db()
            calc.status = 3
            calc.save()
