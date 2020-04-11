from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from django import template
import random, string

from .constants import *

register = template.Library()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    calculation_time_used = models.PositiveIntegerField(default=0)

    is_PI = models.BooleanField(default=False)

    member_of = models.ForeignKey('ResearchGroup', on_delete=models.CASCADE, blank=True, null=True, related_name='members')

    code = models.CharField(max_length=16)

    @property
    def username(self):
        return self.user.username

    def __str__(self):
        return self.user.username

    @property
    def group(self):
        if self.is_PI:
            return self.researchgroup_PI
        else:
            return self.member_of

    @property
    def accesses(self):
        accesses = []
        if self.group != None:
            for acc in self.group.all()[0].clusteraccess_set.all():
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

    def __repr__(self):
        return self.name

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

    avail_xtb = models.BooleanField(default=False)
    avail_Gaussian = models.BooleanField(default=False)
    avail_ORCA = models.BooleanField(default=False)

    creates_ensemble = models.BooleanField(default=False)
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


    avail_xtb = models.BooleanField(default=False)
    avail_Gaussian = models.BooleanField(default=False)
    avail_orca = models.BooleanField(default=False)

class Ensemble(models.Model):
    name = models.CharField(max_length=100, default="Nameless ensemble")
    parent_molecule = models.ForeignKey('Molecule', on_delete=models.CASCADE, blank=True, null=True)

    hidden = models.BooleanField(default=False)
    def __repr__(self):
        return self.id

    @property
    def unique_parameters(self):
        unique = []
        structs = self.structure_set.all()
        for s in structs:
            for p in s.properties.all():
                if p.parameters not in unique:
                    unique.append(p.parameters)
        return unique

    def relative_energy(self, structure, params):
        lowest = 0
        try:
            main_p = structure.properties.get(parameters=params)
        except Property.DoesNotExist:
            return '-'

        for s in self.structure_set.all():
            try:
                p = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                continue#Handle this better?
            if p.energy < lowest:
                lowest = p.energy
        return "{:.1f}".format((main_p.energy - lowest)*float(HARTREE_VAL))

    def weight(self, structure, params):
        data = []
        for s in self.structure_set.all():
            try:
                p = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                continue#Handle this better?
            data.append([decimal.Decimal(p.energy), structure.degeneracy])

        if len(data) == 1:
            return 1

        '''
        sumnum = decimal.Decimal(0)
        sumdenum = decimal.Decimal(0)
        for i in range(1, len(data)):
            exp_val = data[i][1]*E_VAL**(-(data[i][0]-data[0][0])/(gas_constant*temp))
            sumnum += decimal.Decimal(exp_val)*(data[i])
            sumdenum += exp_val
        weights = []
        for i, _ in enumerate(data):
            weights.append(data[i][1]*E_VAL**(-(data[i][0]-data[0][0])/(gas_constant*temp))/(decimal.Decimal(1)+sumdenum))

        sums[process_name(name, meso)] = [(gas_constant*temp), (decimal.Decimal(1)+sumdenum)]

        return minval, float((data[0]+sumnum)/(decimal.Decimal(1)+sumdenum)), weights
        '''
        return 'unimplemented'

class Property(models.Model):
    parameters = models.ForeignKey('Parameters', on_delete=models.CASCADE, blank=True, null=True)
    parent_structure = models.ForeignKey('Structure', on_delete=models.CASCADE, blank=True, null=True, related_name="properties")

    energy = models.FloatField(default=0)
    free_energy = models.FloatField(default=0)

    rel_energy = models.FloatField(default=0)
    boltzmann_weight = models.FloatField(default=1.)
    homo_lumo_gap = models.FloatField(default=0)

    uvvis = models.PositiveIntegerField(default=0)
    nmr = models.PositiveIntegerField(default=0)
    mo = models.PositiveIntegerField(default=0)
    freq = models.PositiveIntegerField(default=0)

    geom = models.BooleanField(default=False)



class Structure(models.Model):
    parent_ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True)

    mol_structure = models.CharField(default="", max_length=5000000)
    xyz_structure = models.CharField(default="", max_length=5000000)
    sdf_structure = models.CharField(default="", max_length=5000000)

    number = models.PositiveIntegerField(default=0)
    energy = models.FloatField(default=0)
    free_energy = models.FloatField(default=0)

    degeneracy = models.PositiveIntegerField(default=0)

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

    def __eq__(self, other):
        values = [(k,v) for k,v in self.__dict__.items() if k != '_state' and k != 'id']
        other_values = [(k,v) for k,v in other.__dict__.items() if k != '_state' and k != 'id']
        return values == other_values

class Molecule(models.Model):

    name = models.CharField(max_length=100)
    inchi = models.CharField(max_length=1000)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)

    @property
    def count_vis(self):
        return len(self.ensemble_set.filter(hidden=False))


class CalculationOrder(models.Model):
    name = models.CharField(max_length=100)

    ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True)
    result_ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True, related_name='result_of')
    step = models.ForeignKey(BasicStep, on_delete=models.CASCADE, blank=True, null=True)

    author = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    project = models.ForeignKey('Project', on_delete=models.CASCADE, blank=True, null=True)

    parameters = models.ForeignKey(Parameters, on_delete=models.CASCADE, blank=True, null=True)

    constraints = models.CharField(max_length=400, default="", blank=True, null=True)

    date = models.DateTimeField('date', null=True, blank=True)
    date_finished = models.DateTimeField('date', null=True, blank=True)

    @property
    def status(self):
        stat = 0
        for calc in self.calculation_set.all():
            if calc.status > stat:
                stat = calc.status
        return stat

    @property
    def get_queued(self):
        return len(self.calculation_set.filter(status=0))

    @property
    def get_running(self):
        return len(self.calculation_set.filter(status=1))

    @property
    def get_done(self):
        return len(self.calculation_set.filter(status=2))

    @property
    def get_error(self):
        return len(self.calculation_set.filter(status=3))

class Calculation(models.Model):

    CALC_STATUSES = {
            "Queued" : 0,
            "Running" : 1,
            "Done" : 2,
            "Error" : 3,
            }

    INV_CALC_STATUSES = {v: k for k, v in CALC_STATUSES.items()}


    error_message = models.CharField(max_length=400, default="")
    current_status = models.CharField(max_length=400, default="")

    date = models.DateTimeField('date', null=True, blank=True)
    date_finished = models.DateTimeField('date', null=True, blank=True)

    execution_time = models.PositiveIntegerField(default=0)

    status = models.PositiveIntegerField(default=0)

    structure = models.ForeignKey(Structure, on_delete=models.CASCADE)
    step = models.ForeignKey(BasicStep, on_delete=models.CASCADE)
    order = models.ForeignKey(CalculationOrder, on_delete=models.CASCADE)

    parameters = models.ForeignKey(Parameters, on_delete=models.CASCADE)
    result_ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True)
    unseen = models.BooleanField(default=True)

    constraints = models.CharField(max_length=400, default="", blank=True, null=True)

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


