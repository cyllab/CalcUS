from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from django import template
import random, string
import numpy as np

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
            return self.researchgroup_PI.all()[0]
        else:
            return self.member_of

    @property
    def accesses(self):
        return self.clusteraccess_owner.all()

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

    cluster_address = models.CharField(max_length=200, blank=True)
    cluster_username = models.CharField(max_length=50, blank=True)

    pal = models.PositiveIntegerField(default=8)
    memory = models.PositiveIntegerField(default=15000)

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
    origin = models.ForeignKey('Ensemble', on_delete=models.CASCADE, blank=True, null=True)

    NODE_COLORS = {0: '#000000', 1: '#ffdd57', 2: '#23d160', 3: '#ff3860'}
    hidden = models.BooleanField(default=False)
    def __repr__(self):
        return self.id

    @property
    def get_node_color(self):
        orders = self.result_of.all()
        if len(orders) == 0:
            return self.NODE_COLORS[2]
        statuses = [i.status for i in orders]
        orders2 = self.calculationorder_set.all()
        statuses += [i.status for i in orders2]
        if 3 in statuses:
            return self.NODE_COLORS[3]
        else:
            return self.NODE_COLORS[min(statuses)]


    @property
    def unique_parameters(self):
        unique = []
        structs = self.structure_set.all()
        for s in structs:
            for p in s.properties.all():
                if p.parameters not in unique:
                    unique.append(p.parameters)
        return unique

    @property
    def unique_calculations(self):
        unique = []
        structs = self.structure_set.all()
        for s in structs:
            for c in s.calculation_set.all():
                if c.step.name not in unique:
                    unique.append(c.step.name)
        return unique

    def has_nmr(self, params):
        for s in self.structure_set.all():
            try:
                p = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                continue#Handle this better?
            if p.simple_nmr != '':
                return True
        return False


    def weighted_free_energy(self, params):
        data = []
        en_0 = 0
        for s in self.structure_set.all():
            try:
                p = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                continue#Handle this better?
            if p.free_energy == 0.:
                return '-'
            if en_0 == 0:
                en_0 = p.free_energy
            data.append([decimal.Decimal(p.free_energy-en_0), s.degeneracy])

        if len(data) == 1:
            return float(en_0)

        s = decimal.Decimal(0)

        for e, degen in data:
            s += degen*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))

        w_energy = decimal.Decimal(0)

        for e, degen in data:
            w_energy += degen*(e+decimal.Decimal(en_0))*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))/s

        return float(w_energy)

    def weighted_energy(self, params):
        data = []
        en_0 = 0
        for s in self.structure_set.all():
            try:
                p = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                continue#Handle this better?
            en = decimal.Decimal(p.energy)
            if en == 0:
                return ''
            if en_0 == 0:
                en_0 = en
            data.append([en-en_0, s.degeneracy])

        if len(data) == 1:
            return float(en_0)

        s = decimal.Decimal(0)

        for e, degen in data:
            s += degen*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))

        w_energy = decimal.Decimal(0)

        for e, degen in data:
            w_energy += degen*(e+en_0)*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))/s

        return float(w_energy)

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
        return (main_p.energy - lowest)*float(HARTREE_VAL)

    def relative_energies(self, params):
        lowest = 0
        energies = []
        for s in self.structure_set.all():
            try:
                p = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                energies.append('')
                continue
            if p.energy < lowest:
                lowest = decimal.Decimal(p.energy)
            energies.append(decimal.Decimal(p.energy))
        energies_kj = [(i-lowest)*HARTREE_VAL if i != '' else '' for i in energies]
        return energies_kj

    def weights(self, params):
        data = []
        en_0 = 0
        for s in self.structure_set.all():
            try:
                p = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                data.append(['', ''])
                continue
            en = p.energy
            if en_0 == 0:
                en_0 = en
            data.append([decimal.Decimal(en-en_0), s.degeneracy])

        en_0 = decimal.Decimal(en_0)
        if len(data) == 1:
            return [1]

        s = decimal.Decimal(0)

        for e, degen in data:
            if e != '':
                s += degen*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))

        weights = []
        for e, degen in data:
            if e == '':
                weights.append('')
                continue
            assert degen != 0
            w = degen*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))/s
            weights.append(w)
        return weights

    def weighted_nmr_shifts(self, params):
        weights = self.weights(params)
        shifts = []
        for ind, s in enumerate(self.structure_set.all()):
            try:
                prop = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                continue
            #Handle if simple_nmr is not set
            w = weights[ind]

            for ind2, shift in enumerate(prop.simple_nmr.split('\n')):
                if shift.strip() == '':
                    continue

                ss = shift.strip().split()
                if ind2 >= len(shifts):
                    shifts.append([ss[0], ss[1], w*decimal.Decimal(ss[2])])
                else:
                    shifts[ind2][2] += w*decimal.Decimal(ss[2])
                    assert shifts[ind2][0] == ss[0]
                    assert shifts[ind2][1] == ss[1]
        try:
            regressions = NMR_REGRESSIONS[params.software][params.method][params.basis_set]
        except KeyError:
            return shifts

        for shift in shifts:
            try:
                m, b, R2 = regressions[shift[1]]
            except KeyError:
                shift.append('')
            else:
                shift.append((float(shift[2])-b)/m)
        return shifts

    def weight(self, structure, params):
        data = []
        en_0 = 0
        for s in self.structure_set.all():
            try:
                p = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                continue#Handle this better?
            en = p.energy
            if en == 0:
                return ''
            if en_0 == 0:
                en_0 = en
            data.append([decimal.Decimal(en-en_0), s.degeneracy])

        if len(data) == 1:
            return 1

        s = decimal.Decimal(0)

        for e, degen in data:
            s += degen*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))

        try:
            main_p = structure.properties.get(parameters=params)
        except Property.DoesNotExist:
            return '-'

        main_weight = structure.degeneracy*np.exp(-decimal.Decimal(main_p.energy-en_0)*HARTREE_VAL*1000/(R_CONSTANT*TEMP))/s
        return float(main_weight)

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

    simple_nmr = models.CharField(default="", max_length=100000)

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
    software = models.CharField(max_length=100, default='xtb')
    basis_set = models.CharField(max_length=100, default='min')
    method = models.CharField(max_length=100, default='GFN2-xTB')
    misc = models.CharField(max_length=1000, default='')

    def __repr__(self):
        return "{} - {} ({})".format(self.software, self.method, self.solvent)

    def __str__(self):
        return self.__repr__()

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

    structure = models.ForeignKey(Structure, on_delete=models.CASCADE, blank=True, null=True)
    ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True)
    result_ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True, related_name='result_of')
    step = models.ForeignKey(BasicStep, on_delete=models.CASCADE, blank=True, null=True)

    author = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    project = models.ForeignKey('Project', on_delete=models.CASCADE, blank=True, null=True)
    parameters = models.ForeignKey(Parameters, on_delete=models.CASCADE, blank=True, null=True)

    constraints = models.CharField(max_length=400, default="", blank=True, null=True)

    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, blank=True, null=True)

    date = models.DateTimeField('date', null=True, blank=True)
    date_finished = models.DateTimeField('date', null=True, blank=True)
    unseen = models.BooleanField(default=True)

    resource = models.ForeignKey('ClusterAccess', on_delete=models.CASCADE, blank=True, null=True)

    @property
    def status(self):
        stat = 0
        num_queued = 0
        num_running = 0
        num_done = 0
        num_error = 0
        for calc in self.calculation_set.all():
            if calc.status == 0:
                num_queued += 1
            elif calc.status == 1:
                num_running += 1
            elif calc.status == 2:
                num_done += 1
            elif calc.status == 3:
                num_error += 1

        if num_queued + num_running + num_done + num_error == 0:
            return 0

        if num_running > 0:
            return 1

        if num_queued == 0:
            if num_error > 0:
                return 3
            else:
                return 2

        return 0
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
    software = models.CharField(max_length=100, default="")

    parameters = models.ForeignKey(Parameters, on_delete=models.CASCADE)
    result_ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True)

    constraints = models.CharField(max_length=400, default="", blank=True, null=True)

    has_scan = models.BooleanField(default=False)
    local = models.BooleanField(default=True)

    pal = models.PositiveIntegerField(default=8)
    memory = models.PositiveIntegerField(default=15000)

    def __str__(self):
        return self.step.name

    @property
    def runtime(self):
        if self.status == 2 or self.status == 3:
            try:
                return (self.date_finished - self.date)
            except TypeError:
                return ''
        else:
            return ''

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

class Filter(models.Model):
    type = models.CharField(max_length=500)
    parameters = models.ForeignKey(Parameters, on_delete=models.CASCADE)
    value = models.FloatField()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(16))
    if created:
        Profile.objects.create(user=instance, code=code)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


