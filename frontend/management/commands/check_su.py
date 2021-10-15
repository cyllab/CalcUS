from django.core.management.base import BaseCommand
from frontend.models import *

su_name = os.environ.get("CALCUS_SU_NAME", '')
class Command(BaseCommand):
    help = 'Verifies if the default superuser account is created'

    def handle(self, *args, **options):
        if su_name == '':
            print("No superuser name provided, creation aborted")
            return
        try:
            su = User.objects.get(username=su_name)
        except User.DoesNotExist:
            su = User.objects.create_superuser(username=su_name, password="calcus_default_password")
            print("Superuser with name '{}' created".format(su_name))
        else:
            print("Superuser account found, creation aborted")
