from django.db import models
from django.utils import timezone
import datetime
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from django import template

register = template.Library()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    calculation_time_used = models.PositiveIntegerField(default=0)

    @property
    def username(self):
        return self.user.username

    def __str__(self):
        return self.user.username

class Project(models.Model):
    name = models.CharField(max_length=100)
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

class Calculation(models.Model):

    CALC_TYPES = {
            "Geometrical Optimisation" : 0,
            "Conformer Search" : 1,
            "UV/Vis Spectrum Prediction": 2,
            "NMR Spectrum Prediction": 3,
            }

    CALC_STATUSES = {
            "Queued" : 0,
            "Running" : 1,
            "Done" : 2,
            "Error" : 3,
            }

    INV_CALC_TYPES = {v: k for k, v in CALC_TYPES.items()}
    INV_CALC_STATUSES = {v: k for k, v in CALC_STATUSES.items()}

    name = models.CharField(max_length=100)

    error_message = models.CharField(max_length=400, default="")

    date = models.DateTimeField('date')
    date_finished = models.DateTimeField('date', default=datetime.datetime.now, blank=True)

    charge = models.IntegerField()
    solvent = models.CharField(max_length=100, default='vacuum')

    type = models.PositiveIntegerField()
    execution_time = models.PositiveIntegerField(default=0)

    status = models.PositiveIntegerField()

    author = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)

    weighted_energy = models.FloatField(default=0.)


    def __repr__(self):
        return self.id

    @property
    def text_type(self):
        return self.INV_CALC_TYPES[self.type]

    @property
    def text_status(self):
        return self.INV_CALC_STATUSES[self.status]


class Structure(models.Model):
    number = models.PositiveIntegerField()
    energy = models.FloatField()

    degeneracy = models.PositiveIntegerField(default=0)
    rel_energy = models.FloatField()
    boltzmann_weight = models.FloatField()
    homo_lumo_gap = models.FloatField()

    result_of = models.ForeignKey(Calculation, on_delete=models.CASCADE, blank=True, null=True)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


