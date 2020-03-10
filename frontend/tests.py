from django.test import TestCase

from django.urls import reverse
import datetime
from django.utils import timezone

from .models import Profile
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.test import Client

def create_challenge(path, days):
    """
    Creates a challenge with given text and published it with a `days` days offset
    """
    time = timezone.now() + datetime.timedelta(days=days)
    #User.objects.create_user('test_user{}'.format(time))

    #user = User.objects.get(username='test_user1')
    #author = Profile(user)
    #return Challenge.objects.create(path=path, pub_date=time, reward=1, correct_answer='1')


def create_user(username):
    u = User.objects.create_user(username=username, password="test1234")
    c = Profile(u)
    c.save()
    return c

