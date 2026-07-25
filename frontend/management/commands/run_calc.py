import os
import signal
from django.core.management.base import BaseCommand

from frontend.models import Calculation
from frontend.tasks import run_calc
from django.utils import timezone


def update_calculation_on_batch_termination(calc, attempt, max_retries):
    """Record a best-effort Batch retry transition before the VM stops."""
    calc.refresh_from_db()
    if calc.status not in (0, 1):
        return

    if attempt >= max_retries:
        calc.status = 3
        calc.current_status = ""
        calc.error_message = "The calculation was preempted after all Spot VM retries."
        calc.date_finished = timezone.now()
    else:
        calc.status = 0
        calc.current_status = "Spot VM preempted; waiting for retry"
        calc.error_message = ""
        calc.date_started = None
        calc.date_finished = None

    calc.save()


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

        if "CALCUS_BATCH_MAX_RETRIES" in os.environ:
            try:
                attempt = int(os.getenv("BATCH_TASK_RETRY_ATTEMPT", "0"))
                max_retries = int(os.environ["CALCUS_BATCH_MAX_RETRIES"])
            except ValueError:
                attempt = 0
                max_retries = 5

            def handle_termination(signum, frame):
                update_calculation_on_batch_termination(calc, attempt, max_retries)
                raise SystemExit(128 + signum)

            signal.signal(signal.SIGTERM, handle_termination)

        nproc = int(os.getenv("OMP_NUM_THREADS")[0])
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
