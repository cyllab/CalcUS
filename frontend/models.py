from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from django import template
import random, string

register = template.Library()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    calculation_time_used = models.PositiveIntegerField(default=0)

    is_PI = models.BooleanField(default=False)
    is_SU = models.BooleanField(default=False)

    groups = models.ForeignKey('ResearchGroup', on_delete=models.CASCADE, blank=True, null=True, related_name='members')

    code = models.CharField(max_length=16)

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
        for i in self.group.members.all():
            users.append(i)
        users.append(self.group.PI)
        return users

class BasicStep(models.Model):
    name = models.CharField(max_length=100)
    desc = models.CharField(max_length=500, default="")
    error_message = models.CharField(max_length=500, default="")

    def __repr__(self):
        return self.id

class Step(models.Model):
    step_model = models.ForeignKey(BasicStep, on_delete=models.CASCADE)
    parent_step = models.ForeignKey('Step', on_delete=models.CASCADE, blank=True, null=True)
    parent_procedure = models.ForeignKey('Procedure', on_delete=models.CASCADE, blank=True, null=True, related_name="initial_steps")

    from_procedure = models.ForeignKey('Procedure', on_delete=models.CASCADE)

    parameters = models.ForeignKey('Parameters', on_delete=models.CASCADE, blank=True, null=True)

    same_dir = models.BooleanField(default=False)

    def __repr__(self):
        return self.id

    @property
    def name(self):
        return self.step_model.name

class Procedure(models.Model):
    name = models.CharField(max_length=100)

    has_nmr = models.BooleanField(default=False)
    has_freq = models.BooleanField(default=False)
    has_uvvis = models.BooleanField(default=False)
    has_mo = models.BooleanField(default=False)

class Ensemble(models.Model):
    name = models.CharField(max_length=100, default="Nameless ensemble")

    def __repr__(self):
        return self.id

class Structure(models.Model):
    parent_ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True)

    mol_structure = models.CharField(default="", max_length=5000000)
    xyz_structure = models.CharField(default="", max_length=5000000)
    sdf_structure = models.CharField(default="", max_length=5000000)

    number = models.PositiveIntegerField(default=0)
    energy = models.FloatField(default=0)
    free_energy = models.FloatField(default=0)

    degeneracy = models.PositiveIntegerField(default=0)
    rel_energy = models.FloatField(default=0)
    boltzmann_weight = models.FloatField(default=1.)
    homo_lumo_gap = models.FloatField(default=0)

    def __repr__(self):
        return self.id



class Parameters(models.Model):
    name = models.CharField(max_length=100, default="Nameless parameters")
    charge = models.IntegerField()
    multiplicity = models.IntegerField()
    solvent = models.CharField(max_length=100, default='vacuum')
    solvation_model = models.CharField(max_length=100, default='gbsa')
    program = models.CharField(max_length=100, default='xtb')
    basis_set = models.CharField(max_length=100, default='min')
    method = models.CharField(max_length=100, default='GFN2-xTB')
    misc = models.CharField(max_length=1000, default='')

    def __repr__(self):
        return self.id

class Calculation(models.Model):

    CALC_STATUSES = {
            "Queued" : 0,
            "Running" : 1,
            "Done" : 2,
            "Error" : 3,
            }

    INV_CALC_STATUSES = {v: k for k, v in CALC_STATUSES.items()}

    name = models.CharField(max_length=100)

    ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True)

    result_ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True, related_name='result_of')

    error_message = models.CharField(max_length=400, default="")
    current_status = models.CharField(max_length=400, default="")

    num_steps = models.IntegerField(default=0)
    current_step = models.IntegerField(default=0)

    date = models.DateTimeField('date', null=True, blank=True)
    date_finished = models.DateTimeField('date', null=True, blank=True)

    execution_time = models.PositiveIntegerField(default=0)

    status = models.PositiveIntegerField(default=0)

    author = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)

    weighted_energy = models.FloatField(default=0.)

    global_parameters = models.ForeignKey(Parameters, on_delete=models.CASCADE, blank=True, null=True)
    procedure = models.ForeignKey(Procedure, on_delete=models.CASCADE, blank=True, null=True)

    constraints = models.CharField(max_length=400, default="", blank=True, null=True)

    unseen = models.BooleanField(default=True)

    has_scan = models.BooleanField(default=False)

    @property
    def has_freq(self):
        return self.procedure.has_freq

    @property
    def has_uvvis(self):
        return self.procedure.has_uvvis

    @property
    def has_nmr(self):
        return self.procedure.has_nmr

    @property
    def has_mo(self):
        return self.procedure.has_mo

    def __repr__(self):
        return self.id

    @property
    def text_status(self):
        return self.INV_CALC_STATUSES[self.status]


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(16))
    if created:
        Profile.objects.create(user=instance, code=code)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


