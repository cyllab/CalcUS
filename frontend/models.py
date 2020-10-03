from django.db import models
from django.db.models.signals import pre_save
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from django import template
import random, string
import numpy as np
import os
import hashlib

from .constants import *

register = template.Library()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    calculation_time_used = models.PositiveIntegerField(default=0)

    is_PI = models.BooleanField(default=False)

    member_of = models.ForeignKey('ResearchGroup', on_delete=models.SET_NULL, blank=True, null=True, related_name='members')

    default_gaussian = models.CharField(max_length=1000, default='')
    default_orca = models.CharField(max_length=1000, default='')

    code = models.CharField(max_length=16)

    pref_units = models.PositiveIntegerField(default=0)
    unseen_calculations = models.PositiveIntegerField(default=0)

    UNITS = {0: 'kJ/mol', 1: 'kcal/mol', 2: 'Ha'}

    INV_UNITS = {v: k for k, v in UNITS.items()}

    @property
    def pref_units_name(self):
        return self.UNITS[self.pref_units]

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

class Recipe(models.Model):
    title = models.CharField(max_length=100)
    page_path = models.CharField(max_length=100)

class Exercise(models.Model):
    title = models.CharField(max_length=100)
    page_path = models.CharField(max_length=100)

class Question(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.SET_NULL, blank=True, null=True)
    question = models.CharField(max_length=2000)
    answer = models.FloatField()
    tolerance = models.FloatField()

class CompletedExercise(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.SET_NULL, blank=True, null=True)
    completed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True)

class ClusterCommand(models.Model):
    issuer = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)

class ResearchGroup(Group):
    PI = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True, related_name="researchgroup_PI")

    def __repr__(self):
        return self.name

class PIRequest(models.Model):
    issuer = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    group_name = models.CharField(max_length=100)
    date_issued = models.DateTimeField('date')

class Project(models.Model):
    name = models.CharField(max_length=100)
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    private = models.PositiveIntegerField(default=0)

    preset = models.ForeignKey('Preset', on_delete=models.SET_NULL, blank=True, null=True)

    num_calc = models.PositiveIntegerField(default=0)
    num_calc_queued = models.PositiveIntegerField(default=0)
    num_calc_running = models.PositiveIntegerField(default=0)
    num_calc_completed = models.PositiveIntegerField(default=0)

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

    parameters = models.ForeignKey('Parameters', on_delete=models.CASCADE, blank=True, null=True)###

    same_dir = models.BooleanField(default=False)###

    def __repr__(self):
        return self.id

    @property
    def name(self):
        return self.step_model.name

class Preset(models.Model):
    name = models.CharField(max_length=100, default="My Preset")
    params = models.ForeignKey('Parameters', on_delete=models.SET_NULL, blank=True, null=True)
    author = models.ForeignKey('Profile', on_delete=models.CASCADE, blank=True, null=True)

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
    origin = models.ForeignKey('Ensemble', on_delete=models.SET_NULL, blank=True, null=True)

    flagged = models.BooleanField(default=False)

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
        statuses += [i.status for i in orders2 if not i.step.creates_ensemble]
        if 3 in statuses:
            return self.NODE_COLORS[3]
        else:
            return self.NODE_COLORS[min(statuses)]


    @property
    def unique_parameters(self):
        def _in(a, l):
            for i in l:
                if a == i:
                    return True
            return False

        unique = []
        structs = self.structure_set.all()
        for s in structs:
            for p in s.properties.all():
                if not _in(p.parameters, unique):
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

    def boltzmann_weighing_full(self, values, degeneracies):
        if len(values) == 1:
            return [[0.0], [1.0], values[0]]

        en_0 = decimal.Decimal(min(values))
        data = zip([decimal.Decimal(i) - en_0 for i in values], degeneracies)
        relative_energies = [i - float(en_0) for i in values]

        weights = []

        s = decimal.Decimal(0)
        w_energy = decimal.Decimal(0)

        for e, n in data:
            e_exp = np.exp(-e/(R_CONSTANT_HARTREE*TEMP))
            s += n*e_exp
            w_energy += n*(e+decimal.Decimal(en_0))*e_exp
            weights.append(n*e_exp)

        w_energy /= s
        weights = [i/s for i in weights]

        return [relative_energies, weights, float(w_energy)]

    def boltzmann_weighing_lite(self, values, degeneracies):
        if len(values) == 1:
            return values[0]

        en_0 = decimal.Decimal(min(values))
        data = zip([decimal.Decimal(i) - en_0 for i in values], degeneracies)

        s = decimal.Decimal(0)
        w_energy = decimal.Decimal(0)

        for e, n in data:
            e_exp = np.exp(-e/(R_CONSTANT_HARTREE*TEMP))
            s += n*e_exp
            w_energy += n*(e+decimal.Decimal(en_0))*e_exp

        w_energy /= s

        return float(w_energy)

    def calc_array_properties(self, in_arr):
        data = []
        e_0 = 0
        f_e_0 = 0
        if 0 in in_arr[2]:
            w_e = '-'
        else:
            rel_e, weights, w_e = self.boltzmann_weighing_full(in_arr[2], in_arr[1])

        if 0 in in_arr[3]:
            w_f_e = '-'
        else:
            w_f_e = self.boltzmann_weighing_lite(in_arr[3], in_arr[1])

        return [rel_e, weights, w_e, w_f_e]


    @property
    def ensemble_summary(self):
        '''
            Returns all the necessary information for the summary

            Data structure:
            {
                hash:
                    [
                        [numbers],
                        [degeneracies],
                        [energies],
                        [free energies],
                        [relative energies],
                        [weights],
                        weighted_energy,
                        weighted_free_energy,
                    ],
                ...
            }
        '''

        ret = {}
        hashes = {}
        for s in self.structure_set.all():
            for prop in s.properties.all():
                if prop.energy == 0:
                    continue

                p = prop.parameters
                p_name = p.md5

                if p_name not in hashes.keys():
                    hashes[p_name] = p.long_name

                if p_name not in ret.keys():
                    ret[p_name] = [[], [], [], []]
                ret[p_name][0].append(s.number)
                ret[p_name][1].append(s.degeneracy)
                ret[p_name][2].append(prop.energy)
                ret[p_name][3].append(prop.free_energy)

        for p_name in ret.keys():
            ret[p_name] += self.calc_array_properties(ret[p_name])

        return ret, hashes

    @property
    def ensemble_short_summary(self):
        '''
            Returns ensemble properties

            Data structure:
            {
                hash:
                    [
                        weighted_energy,
                        weighted_free_energy,
                    ],
                ...
            }
        '''

        ret = {}
        hashes = {}

        arr_e = {}
        arr_f_e = {}
        for s in self.structure_set.all():
            for prop in s.properties.all():
                if prop.energy == 0:
                    continue

                p = prop.parameters
                p_name = p.long_name

                if p_name not in hashes.keys():
                    hashes[p_name] = p.long_name

                if p_name not in arr_e.keys():
                    arr_e[p_name] = [[], []]
                    arr_f_e[p_name] = [[], []]

                arr_e[p_name][0].append(prop.energy)
                arr_e[p_name][1].append(s.degeneracy)

                arr_f_e[p_name][0].append(prop.free_energy)
                arr_f_e[p_name][1].append(s.degeneracy)

        for p_name in arr_e.keys():
            ret[p_name] = [self.boltzmann_weighing_lite(*arr_e[p_name]), self.boltzmann_weighing_lite(*arr_f_e[p_name])]
        return ret, hashes

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

        w_energy = decimal.Decimal(0)

        for e, degen in data:
            s += degen*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))
            w_energy += degen*(e+decimal.Decimal(en_0))*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))
        w_energy /= s

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
        w_energy = decimal.Decimal(0)

        for e, degen in data:
            s += degen*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))
            w_energy += degen*(e+en_0)*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))

        w_energy /= s

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
        return (main_p.energy - lowest)

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
        rel_energies = [(i-lowest) if i != '' else '' for i in energies]
        return rel_energies

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
                if degen == 0:
                    s += np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))
                else:
                    s += degen*np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))

        weights = []
        for e, degen in data:
            if e == '':
                weights.append('')
                continue
            if degen == 0:
                w = np.exp(-e*HARTREE_VAL*1000/(R_CONSTANT*TEMP))/s
            else:
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
    parameters = models.ForeignKey('Parameters', on_delete=models.SET_NULL, blank=True, null=True)
    parent_structure = models.ForeignKey('Structure', on_delete=models.CASCADE, blank=True, null=True, related_name="properties")

    energy = models.FloatField(default=0)
    free_energy = models.FloatField(default=0)

    homo_lumo_gap = models.FloatField(default=0)

    uvvis = models.PositiveIntegerField(default=0)
    nmr = models.PositiveIntegerField(default=0)
    mo = models.PositiveIntegerField(default=0)
    freq = models.PositiveIntegerField(default=0)

    simple_nmr = models.CharField(default="", max_length=100000)
    charges = models.CharField(default="", max_length=100000)

    geom = models.BooleanField(default=False)

class Structure(models.Model):
    parent_ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True)

    mol_structure = models.CharField(default="", max_length=5000000)
    mol2_structure = models.CharField(default="", max_length=5000000)
    xyz_structure = models.CharField(default="", max_length=5000000)
    sdf_structure = models.CharField(default="", max_length=5000000)

    number = models.PositiveIntegerField(default=1)
    degeneracy = models.PositiveIntegerField(default=1)

    def __repr__(self):
        return self.id

class CalculationFrame(models.Model):
    parent_calculation = models.ForeignKey('Calculation', on_delete=models.CASCADE, blank=True, null=True)

    xyz_structure = models.CharField(default="", max_length=5000000)
    RMSD = models.FloatField(default=0)

    number = models.PositiveIntegerField(default=0)

    def __repr__(self):
        return self.id

class Parameters(models.Model):
    name = models.CharField(max_length=100, default="Nameless parameters")
    charge = models.IntegerField()
    multiplicity = models.IntegerField()
    solvent = models.CharField(max_length=100, default='vacuum')
    solvation_model = models.CharField(max_length=100, default='')
    solvation_radii = models.CharField(max_length=100, default='')
    software = models.CharField(max_length=100, default='xtb')
    basis_set = models.CharField(max_length=100, default='min')
    theory_level = models.CharField(max_length=100, default='')
    method = models.CharField(max_length=100, default='GFN2-xTB')
    specifications = models.CharField(max_length=1000, default='')
    additional_command = models.CharField(max_length=1000, default='')
    density_fitting = models.CharField(max_length=1000, default='')
    custom_basis_sets = models.CharField(max_length=1000, default='')

    def __repr__(self):
        return "{} - {} ({})".format(self.software, self.method, self.solvent)

    @property
    def file_name(self):
        name = "{}_".format(self.software)
        if self.theory_level == "DFT" or self.theory_level == "RI-MP2" or self.theory_level == "HF":
            name += "{}_{}".format(self.method, self.basis_set)
        else:
            name += "{}".format(self.method)
        if self.solvent.lower() != 'vacuum':
            name += "_{}_{}".format(self.solvation_model, self.solvent)
        return name

    @property
    def long_name(self):
        name = "{} - ".format(self.software)
        if self.theory_level == "DFT" or self.theory_level == "RI-MP2" or self.theory_level == "HF":
            name += "{}/{} ".format(self.method, self.basis_set)
        else:
            name += "{} ".format(self.method)
        if self.solvent.lower() != 'vacuum':
            name += "({}; {})".format(self.solvation_model, self.solvent)
        return name

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        values = [(k,v) for k,v in self.__dict__.items() if k != '_state' and k != 'id']
        other_values = [(k,v) for k,v in other.__dict__.items() if k != '_state' and k != 'id']
        return values == other_values

    @property
    def md5(self):
        values = [(k,v) for k,v in self.__dict__.items() if k != '_state' and k != 'id']
        params_str = ""
        for k, v in values:
            if isinstance(v, int):
                params_str += "{}={};".format(k, v)
            elif isinstance(v, str):
                params_str += "{}={};".format(k, v.lower())
            else:
                raise Exception("Unknown value type")
        hash = hashlib.md5(bytes(params_str, 'UTF-8'))
        return hash.digest()


class Molecule(models.Model):
    name = models.CharField(max_length=100)
    inchi = models.CharField(max_length=1000)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)

    num_calc = models.PositiveIntegerField(default=0)
    num_calc_queued = models.PositiveIntegerField(default=0)
    num_calc_running = models.PositiveIntegerField(default=0)
    num_calc_completed = models.PositiveIntegerField(default=0)

    @property
    def count_vis(self):
        return len(self.ensemble_set.filter(hidden=False))


class CalculationOrder(models.Model):
    name = models.CharField(max_length=100)

    structure = models.ForeignKey(Structure, on_delete=models.SET_NULL, blank=True, null=True)
    aux_structure = models.ForeignKey(Structure, on_delete=models.SET_NULL, blank=True, null=True, related_name='aux_of_order')
    ensemble = models.ForeignKey(Ensemble, on_delete=models.SET_NULL, blank=True, null=True)
    start_calc = models.ForeignKey('Calculation', on_delete=models.SET_NULL, blank=True, null=True)
    start_calc_frame = models.PositiveIntegerField(default=0)

    result_ensemble = models.ForeignKey(Ensemble, on_delete=models.SET_NULL, blank=True, null=True, related_name='result_of')
    step = models.ForeignKey(BasicStep, on_delete=models.SET_NULL, blank=True, null=True)

    author = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    project = models.ForeignKey('Project', on_delete=models.CASCADE, blank=True, null=True)
    parameters = models.ForeignKey(Parameters, on_delete=models.SET_NULL, blank=True, null=True)

    constraints = models.CharField(max_length=400, default="", blank=True, null=True)

    filter = models.ForeignKey('Filter', on_delete=models.SET_NULL, blank=True, null=True)

    date = models.DateTimeField('date', null=True, blank=True)
    last_seen_status = models.PositiveIntegerField(default=0)

    resource = models.ForeignKey('ClusterAccess', on_delete=models.SET_NULL, blank=True, null=True)

    def see(self):
        self.last_seen_status = self.status
        self.author.unseen_calculations -= 1
        self.author.save()
        self.save()

    @property
    def label(self):
        if self.result_ensemble:
            return self.result_ensemble.name
        else:
            if self.ensemble:
                return self.ensemble.name
            elif self.structure:
                return self.structure.parent_ensemble.name
            else:
                return "Unknown"

    @property
    def molecule_name(self):
        if self.ensemble != None and self.ensemble.parent_molecule != None:
            return self.ensemble.parent_molecule.name
        elif self.structure != None and self.structure.parent_ensemble != None and self.structure.parent_ensemble.parent_molecule != None:
            return self.structure.parent_ensemble.parent_molecule.name
        else:
            return "Unknown"

    @property
    def status(self):
        return self._status(*self.get_all_calcs)

    def _status(self, num_queued, num_running, num_done, num_error):
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

    @property
    def get_all_calcs(self):
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
        return num_queued, num_running, num_done, num_error

    @property
    def new_status(self):
        if self.last_seen_status != self.status:
            return True
        else:
            return False

    def delete(self, *args, **kwargs):
        if self.new_status:
            self.author.unseen_calculations -= 1
            self.author.save()
        super(CalculationOrder, self).delete(*args, **kwargs)

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

    date_submitted = models.DateTimeField('date', null=True, blank=True)
    date_started = models.DateTimeField('date', null=True, blank=True)
    date_finished = models.DateTimeField('date', null=True, blank=True)

    status = models.PositiveIntegerField(default=0)
    error_message = models.CharField(max_length=400, default="", blank=True, null=True)

    structure = models.ForeignKey(Structure, on_delete=models.SET_NULL, null=True)
    aux_structure = models.ForeignKey(Structure, on_delete=models.SET_NULL, null=True, related_name='aux_of_calc')

    step = models.ForeignKey(BasicStep, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(CalculationOrder, on_delete=models.CASCADE)

    parameters = models.ForeignKey(Parameters, on_delete=models.SET_NULL, null=True)
    result_ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE, blank=True, null=True)

    constraints = models.CharField(max_length=400, default="", blank=True, null=True)

    input_file = models.CharField(max_length=50000, default="", blank=True, null=True)

    local = models.BooleanField(default=True)

    task_id = models.CharField(max_length=100, default="")

    remote_id = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.step.name

    def get_mol(self):
        if self.result_ensemble is not None:
            return self.result_ensemble.parent_molecule
        elif self.structure is not None:
            return self.structure.parent_ensemble.parent_molecule
        else:
            print("Could not find molecule to update!")

    def save(self, *args, **kwargs):
        if not self.pk:
            mol = self.get_mol()
            self.order.project.num_calc += 1
            self.order.project.num_calc_queued += 1
            self.order.project.save()
            mol.num_calc += 1
            mol.num_calc_queued += 1
            mol.save()
        else:
            old = Calculation.objects.filter(pk=self.pk).first()
            if old:
                if self.status != old.status:
                    mol = self.get_mol()
                    num_calc_queued = 0
                    num_calc_running = 0
                    num_calc_done = 0
                    num_calc_error = 0

                    if old.status == 0:
                        self.order.project.num_calc_queued -= 1
                        mol.num_calc_queued -= 1
                        num_calc_queued -= 1
                    elif old.status == 1:
                        self.order.project.num_calc_running -= 1
                        mol.num_calc_running -= 1
                        num_calc_running -= 1
                    elif old.status == 2:
                        self.order.project.num_calc_completed -= 1
                        mol.num_calc_completed -= 1
                        num_calc_done -= 1
                    if old.status == 3:
                        self.order.project.num_calc_completed -= 1
                        mol.num_calc_completed -= 1
                        num_calc_error -= 1

                    if self.status == 0:
                        self.order.project.num_calc_queued += 1
                        mol.num_calc_queued += 1
                        num_calc_queued += 1
                    elif self.status == 1:
                        self.order.project.num_calc_running += 1
                        mol.num_calc_running += 1
                        num_calc_running += 1
                    elif self.status == 2:
                        self.order.project.num_calc_completed += 1
                        mol.num_calc_completed += 1
                        num_calc_done += 1
                    if self.status == 3:
                        self.order.project.num_calc_completed += 1
                        mol.num_calc_completed += 1
                        num_calc_error += 1

                    self.order.project.save()
                    mol.save()

                    if not self.order.new_status:#Predict if this status change will change the status of the order
                        old_status = self.order.status
                        nums = self.order.get_all_calcs

                        num_calc_queued += nums[0]
                        num_calc_running += nums[1]
                        num_calc_done += nums[2]
                        num_calc_error += nums[3]

                        new_status = self.order._status(num_calc_queued, num_calc_running, num_calc_done, num_calc_error)
                        if new_status != old_status:
                            self.order.author.unseen_calculations += 1
                            self.order.author.save()

        super(Calculation, self).save(*args, **kwargs)


    def delete(self, *args, **kwargs):
        mol = self.get_mol()
        self.order.project.num_calc -= 1
        mol.num_calc -= 1

        num_calc_queued = 0
        num_calc_running = 0
        num_calc_done = 0
        num_calc_error = 0

        if self.status == 0:
            self.order.project.num_calc_queued -= 1
            mol.num_calc_queued -= 1
            num_calc_queued -= 1
        elif self.status == 1:
            self.order.project.num_calc_running -= 1
            mol.num_calc_running -= 1
            num_calc_running -= 1
        elif self.status == 2:
            self.order.project.num_calc_completed -= 1
            mol.num_calc_completed -= 1
            num_calc_done -= 1
        elif self.status == 3:
            self.order.project.num_calc_completed -= 1
            mol.num_calc_completed -= 1
            num_calc_error -= 1
        else:
            raise Exception("Unknown calculation status")

        self.order.project.save()

        old_status = self.order.status
        nums = self.order.get_all_calcs

        num_calc_queued += nums[0]
        num_calc_running += nums[1]
        num_calc_done += nums[2]
        num_calc_error += nums[3]

        new_status = self.order._status(num_calc_queued, num_calc_running, num_calc_done, num_calc_error)

        if self.order.calculation_set.count() == 1:
            self.order.delete()
        else:
            if new_status != old_status:
                if not self.order.new_status:
                    self.order.author.unseen_calculations += 1
                    self.order.author.save()

            self.order.author.save()

        mol.save()

        super(Calculation, self).delete(*args, **kwargs)

    @property
    def execution_time(self):
        if self.date_started is not None and self.date_finished is not None:
            if self.local:
                pal = os.getenv("OMP_NUM_THREADS")[0]
            else:
                pal = self.order.resource.pal
            return int((self.date_finished-self.date_started).seconds*int(pal))

        else:
            return '-'

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


