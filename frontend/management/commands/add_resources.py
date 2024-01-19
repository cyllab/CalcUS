import os
from django.core.management.base import BaseCommand

from frontend.models import *
from frontend.environment_variables import *
from frontend.tasks import run_calc
from frontend.helpers import get_random_string


class Command(BaseCommand):
    help = "Runs a calculation"

    def add_arguments(self, parser):
        parser.add_argument("email", type=str)
        parser.add_argument("time", type=int)

    def handle(self, *args, **options):
        email = options["email"]
        time = options["time"]
        try:
            u = User.objects.get(email=email)
        except User.DoesNotExist:
            raise Exception(f"Could not find user with email {email}")
        random_code = get_random_string(64)

        res = ResourceAllocation.objects.create(
            code=random_code, note=ResourceAllocation.MANUAL, allocation_seconds=time
        )
        res.redeem(u)
