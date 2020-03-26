from django.core.management.base import BaseCommand, CommandError
from frontend.models import Example
from django.utils import timezone

class Command(BaseCommand):
    help = 'Adds an example to the database'

    def add_arguments(self, parser):
        parser.add_argument('page', type=str)

    def handle(self, *args, **options):
        with open(options['page']) as f:
            fname = options['page'].split('/')[-1]
            for line in f.readlines():
                if line.find("<title>") != -1:
                    title = line.split('<title>')[-1].split('</title>')[0]
            example = Example.objects.create(title=title, page_path=fname)
            example.save()
            print("Added page '{}'".format(title))
