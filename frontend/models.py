from django.db import models
import datetime
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from django import template

register = template.Library()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    calculation_time_used = models.PositiveIntegerField(default=0)

    is_PI = models.BooleanField(default=False)
    is_SU = models.BooleanField(default=False)

    groups = models.ForeignKey('ResearchGroup', on_delete=models.CASCADE, blank=True, null=True, related_name='members')
    @property
    def username(self):
        return self.user.username

    def __str__(self):
        return self.user.username

    @property
    def accesses(self):
        accesses = []
        if self.groups != None:
            for acc in self.groups.clusteraccess_set.all():
                accesses.append(acc)
        for i in self.clusteraccess_owner.all():
            accesses.append(i)
        return accesses

class Example(models.Model):
    title = models.CharField(max_length=100)
    page_path = models.CharField(max_length=100)


class ClusterCommand(models.Model):
    issuer = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)

class ResearchGroup(Group):
    group_name = models.CharField(max_length=100)
    PI = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True, related_name="researchgroup_PI")

class PIRequest(models.Model):
    issuer = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    group_name = models.CharField(max_length=100)
    date_issued = models.DateTimeField('date')

class Project(models.Model):
    name = models.CharField(max_length=100)
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

class ClusterAccess(models.Model):
    private_key_path = models.CharField(max_length=100)
    public_key_path = models.CharField(max_length=100)
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True, related_name="clusteraccess_owner")
    group = models.ForeignKey(ResearchGroup, on_delete=models.CASCADE, blank=True, null=True)

    cluster_address = models.CharField(max_length=200, blank=True)
    cluster_username = models.CharField(max_length=50, blank=True)

    @property
    def num_claimed_keys(self):
        count = 0
        for i in self.clusterpersonalkey_set.all():
            if i.claimer is not None:
                count += 1
        return count

    @property
    def users(self):
        users = []
        for i in self.clusterpersonalkey_set.all():
            if i.claimer is not None:
                users.append(i.claimer)
        return users

class ClusterPersonalKey(models.Model):
    key = models.CharField(max_length=100)
    issuer = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True, related_name="clusterpersonalkey_issuer")
    claimer = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True, related_name="clusterpersonalkey_claimer")
    date_issued = models.DateTimeField('date')
    date_claimed = models.DateTimeField('date', blank=True, null=True)
    access = models.ForeignKey(ClusterAccess, on_delete=models.CASCADE, blank=True, null=True)

class Calculation(models.Model):

    CALC_TYPES = {
            "Geometrical Optimisation" : 0,
            "Conformer Search" : 1,
            "UV/Vis Spectrum Prediction": 2,
            "NMR Spectrum Prediction": 3,
            "Opt+Freq": 4,
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
    current_status = models.CharField(max_length=400, default="")

    num_steps = models.IntegerField(default=0)
    current_step = models.IntegerField(default=0)

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
    free_energy = models.FloatField(default=0)

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


