from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calcus.settings')

username = settings.RABBITMQ_USERNAME
password = settings.RABBITMQ_PASSWORD

app = Celery('calcus', backend="amqp", broker='amqp://{}:{}@localhost//'.format(username, password))

app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
