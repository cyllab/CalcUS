"""
This file of part of CalcUS.

Copyright (C) 2020-2022 Raphaël Robidas

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""


from django.db import models, transaction
from django.db.models.signals import pre_save
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save, post_init
from django.dispatch import receiver
from django import template
import random, string
import numpy as np
import os
import hashlib

from .constants import *

register = template.Library()

STATUS_COLORS = {0: "#AAAAAA", 1: "#FFE515", 2: "#1EE000", 3: "#FD1425"}


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    is_PI = models.BooleanField(default=False)

    member_of = models.ForeignKey(
        "ResearchGroup",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="members",
    )

    default_gaussian = models.CharField(max_length=1000, default="")
    default_orca = models.CharField(max_length=1000, default="")

    code = models.CharField(max_length=16)

    pref_units = models.PositiveIntegerField(default=0)
    unseen_calculations = models.PositiveIntegerField(default=0)

    UNITS = {0: "kJ/mol", 1: "kcal/mol", 2: "Eh"}
    UNITS_PRECISION = {0: 0, 1: 1, 2: 6}
    UNITS_FORMAT_STRING = {0: "{:.1f}", 1: "{:.1f}", 2: "{:.6f}"}

    INV_UNITS = {v: k for k, v in UNITS.items()}

    @property
    def pref_units_name(self):
        return self.UNITS[self.pref_units]

    @property
    def pref_units_precision(self):
        return self.UNITS_PRECISION[self.pref_units]

    @property
    def pref_units_format_string(self):
        return self.UNITS_FORMAT_STRING[self.pref_units]

    @property
    def unit_conversion_factor(self):
        if self.pref_units == 0:
            return HARTREE_FVAL
        elif self.pref_units == 1:
            return HARTREE_TO_KCAL_F
        elif self.pref_units == 2:
            return 1.0
        else:
            raise Exception("Unknown units")

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


class ResearchGroup(Group):
    PI = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="researchgroup_PI",
    )

    def __repr__(self):
        return self.name


class PIRequest(models.Model):
    issuer = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    group_name = models.CharField(max_length=100)
    date_issued = models.DateTimeField("date")


class Project(models.Model):
    name = models.CharField(max_length=100)
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    private = models.PositiveIntegerField(default=0)

    preset = models.ForeignKey(
        "Preset", on_delete=models.SET_NULL, blank=True, null=True
    )
    main_folder = models.ForeignKey(
        "Folder",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="defaultfolder_of",
    )

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


@receiver(post_save, sender=Project)
def create_main_folder(sender, instance, created, **kwargs):
    if created:
        instance.main_folder = Folder.objects.create(
            name="Main Folder", project=instance, depth=0
        )
        instance.main_folder.save()
        instance.save()


class Folder(models.Model):
    name = models.CharField(max_length=100)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, blank=True, null=True
    )
    parent_folder = models.ForeignKey(
        "Folder", on_delete=models.SET_NULL, blank=True, null=True
    )
    depth = models.PositiveIntegerField(default=0)


class ClusterAccess(models.Model):
    owner = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="clusteraccess_owner",
    )

    cluster_address = models.CharField(max_length=200, blank=True)
    cluster_username = models.CharField(max_length=50, blank=True)

    pal = models.PositiveIntegerField(default=8)
    memory = models.PositiveIntegerField(default=15000)

    status = models.CharField(max_length=500, default="")

    last_connected = models.DateTimeField(
        "date", default=timezone.datetime(year=2000, month=1, day=1, hour=1, minute=1)
    )

    @property
    def connected(self):
        dt = timezone.now() - self.last_connected
        if dt.total_seconds() < 600:
            return True
        else:
            return False


class BasicStep(models.Model):
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=100, default="")

    avail_xtb = models.BooleanField(default=False)
    avail_Gaussian = models.BooleanField(default=False)
    avail_ORCA = models.BooleanField(default=False)

    creates_ensemble = models.BooleanField(default=False)


class Preset(models.Model):
    name = models.CharField(max_length=100, default="My Preset")
    params = models.ForeignKey(
        "Parameters", on_delete=models.SET_NULL, blank=True, null=True
    )
    author = models.ForeignKey(
        "Profile", on_delete=models.CASCADE, blank=True, null=True
    )


class Ensemble(models.Model):
    name = models.CharField(max_length=100, default="Nameless ensemble")
    parent_molecule = models.ForeignKey(
        "Molecule", on_delete=models.CASCADE, blank=True, null=True
    )
    origin = models.ForeignKey(
        "Ensemble", on_delete=models.SET_NULL, blank=True, null=True
    )
    folder = models.ForeignKey(
        "Folder", on_delete=models.SET_NULL, blank=True, null=True
    )

    flagged = models.BooleanField(default=False)

    hidden = models.BooleanField(default=False)

    @property
    def get_node_color(self):
        orders = self.result_of.all()
        if len(orders) == 0:
            return STATUS_COLORS[2]
        statuses = [i.status for i in orders]
        orders2 = self.calculationorder_set.all()
        statuses += [i.status for i in orders2 if not i.step.creates_ensemble]

        if len(statuses) == 0:
            return STATUS_COLORS[0]

        if 1 in statuses:
            return STATUS_COLORS[1]

        if 0 not in statuses:
            if 3 in statuses and 2 not in statuses:
                return STATUS_COLORS[3]
            else:
                return STATUS_COLORS[2]

        return STATUS_COLORS[0]

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
                continue  # Handle this better?
            if p.simple_nmr != "":
                return True
        return False

    def boltzmann_weighting_full(self, values, degeneracies):
        if len(values) == 1:
            return [[0.0], [1.0], values[0]]

        en_0 = decimal.Decimal(min(values))
        data = zip([decimal.Decimal(i) - en_0 for i in values], degeneracies)
        relative_energies = [i - float(en_0) for i in values]

        weights = []

        s = decimal.Decimal(0)
        w_energy = decimal.Decimal(0)

        for e, n in data:
            e_exp = np.exp(-e / (R_CONSTANT_HARTREE * TEMP))
            s += n * e_exp
            w_energy += n * (e + decimal.Decimal(en_0)) * e_exp
            weights.append(n * e_exp)

        w_energy /= s
        weights = [i / s for i in weights]

        return [relative_energies, weights, float(w_energy)]

    def boltzmann_weighting_lite(self, values, degeneracies):
        if len(values) == 1:
            return values[0]

        en_0 = decimal.Decimal(min(values))
        data = zip([decimal.Decimal(i) - en_0 for i in values], degeneracies)

        s = decimal.Decimal(0)
        w_energy = decimal.Decimal(0)

        for e, n in data:
            e_exp = np.exp(-e / (R_CONSTANT_HARTREE * TEMP))
            s += n * e_exp
            w_energy += n * (e + decimal.Decimal(en_0)) * e_exp

        w_energy /= s

        return float(w_energy)

    def calc_array_properties(self, in_arr):
        data = []
        e_0 = 0
        f_e_0 = 0
        if 0 in in_arr[2]:
            w_e = "-"
        else:
            rel_e, weights, w_e = self.boltzmann_weighting_full(in_arr[2], in_arr[1])

        if 0 in in_arr[3]:
            w_f_e = "-"
        else:
            w_f_e = self.boltzmann_weighting_lite(in_arr[3], in_arr[1])

        return [rel_e, weights, w_e, w_f_e]

    @property
    def ensemble_summary(self):
        """
        Returns all the necessary information for the summary

        Data structure:
        {
            hash:
                [
                    [numbers],
                    [degeneracies],
                    [energies],
                    [free energies],
                    [structure id],
                    [relative energies],
                    [weights],
                    weighted_energy,
                    weighted_free_energy,
                ],
            ...
        }
        """

        ret = {}
        hashes = {}
        for s in (
            self.structure_set.prefetch_related("properties").order_by("number").all()
        ):
            for prop in s.properties.all():
                if prop.energy == 0:
                    continue

                p = prop.parameters
                p_name = p.md5

                if p_name not in hashes.keys():
                    hashes[p_name] = p.long_name

                if p_name not in ret.keys():
                    ret[p_name] = [[], [], [], [], []]
                ret[p_name][0].append(s.number)
                ret[p_name][1].append(s.degeneracy)
                ret[p_name][2].append(prop.energy)
                ret[p_name][3].append(prop.free_energy)
                ret[p_name][4].append(s.id)

        for p_name in ret.keys():
            ret[p_name] += self.calc_array_properties(ret[p_name])

        return ret, hashes

    @property
    def ensemble_short_summary(self):
        """
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
        """

        ret = {}
        hashes = {}

        arr_e = {}
        arr_f_e = {}
        for s in self.structure_set.prefetch_related("properties").all():
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
            ret[p_name] = [
                self.boltzmann_weighting_lite(*arr_e[p_name]),
                self.boltzmann_weighting_lite(*arr_f_e[p_name]),
            ]
        return ret, hashes

    def weighted_free_energy(self, params):
        energies = []
        degeneracies = []
        en_0 = 0
        for s in self.structure_set.all():
            try:
                p = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                continue  # Handle this better?
            energies.append(p.free_energy)
            degeneracies.append(s.degeneracy)

        return self.boltzmann_weighting_lite(energies, degeneracies)

    def weighted_energy(self, params):
        energies = []
        degeneracies = []
        en_0 = 0
        for s in self.structure_set.all():
            try:
                p = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                continue  # Handle this better?
            energies.append(p.energy)
            degeneracies.append(s.degeneracy)

        return self.boltzmann_weighting_lite(energies, degeneracies)

    def weighted_nmr_shifts(self, params):
        summary, hashes = self.ensemble_summary

        if params.md5 not in summary:
            return []

        weights = [decimal.Decimal(i) for i in summary[params.md5][6]]

        shifts = []
        for ind, s in enumerate(self.structure_set.all()):
            try:
                prop = s.properties.get(parameters=params)
            except Property.DoesNotExist:
                continue
            # Handle if simple_nmr is not set
            w = weights[ind]

            for ind2, shift in enumerate(prop.simple_nmr.split("\n")):
                if shift.strip() == "":
                    continue

                ss = shift.strip().split()
                if ind2 >= len(shifts):
                    shifts.append([ss[0], ss[1], w * decimal.Decimal(ss[2])])
                else:
                    shifts[ind2][2] += w * decimal.Decimal(ss[2])
                    assert shifts[ind2][0] == ss[0]
                    assert shifts[ind2][1] == ss[1]
        try:
            regressions = NMR_REGRESSIONS[params.software][params.method][
                params.basis_set
            ]
        except KeyError:
            return shifts

        for shift in shifts:
            try:
                m, b, R2 = regressions[shift[1]]
            except KeyError:
                shift.append("")
            else:
                shift.append((float(shift[2]) - b) / m)
        return shifts


@receiver(pre_save, sender=Ensemble)
def handle_folder(sender, instance, **kwargs):
    try:
        obj = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        pass
    else:
        if not obj.flagged == instance.flagged:
            if instance.flagged:
                instance.folder = instance.parent_molecule.project.main_folder
            else:
                instance.folder = None


class Property(models.Model):
    parameters = models.ForeignKey(
        "Parameters", on_delete=models.SET_NULL, blank=True, null=True
    )
    parent_structure = models.ForeignKey(
        "Structure",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="properties",
    )

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
    parent_ensemble = models.ForeignKey(
        Ensemble, on_delete=models.CASCADE, blank=True, null=True
    )

    mol_structure = models.CharField(default="", max_length=5000000)
    mol2_structure = models.CharField(default="", max_length=5000000)
    xyz_structure = models.CharField(default="", max_length=5000000)
    sdf_structure = models.CharField(default="", max_length=5000000)

    number = models.PositiveIntegerField(default=1)
    degeneracy = models.PositiveIntegerField(default=1)


class CalculationFrame(models.Model):
    parent_calculation = models.ForeignKey(
        "Calculation", on_delete=models.CASCADE, blank=True, null=True
    )

    xyz_structure = models.CharField(default="", max_length=5000000)
    RMSD = models.FloatField(default=0)
    converged = models.BooleanField(default=False)
    energy = models.FloatField(default=0)

    number = models.PositiveIntegerField(default=0)


class Parameters(models.Model):
    name = models.CharField(max_length=100, default="Nameless parameters")
    charge = models.IntegerField()
    multiplicity = models.IntegerField()
    solvent = models.CharField(max_length=100, default="vacuum")
    solvation_model = models.CharField(max_length=100, default="")
    solvation_radii = models.CharField(max_length=100, default="")
    software = models.CharField(max_length=100, default="xtb")
    basis_set = models.CharField(max_length=100, default="min")
    theory_level = models.CharField(max_length=100, default="")
    method = models.CharField(max_length=100, default="GFN2-xTB")
    specifications = models.CharField(max_length=1000, default="")
    density_fitting = models.CharField(max_length=1000, default="")
    custom_basis_sets = models.CharField(max_length=1000, default="")

    _md5 = models.CharField(max_length=32, default="")

    def __repr__(self):
        return f"{self.software} - {self.method} ({self.solvent})"

    @property
    def file_name(self):
        name = f"{self.software}_"
        if (
            self.theory_level == "DFT"
            or self.theory_level == "RI-MP2"
            or self.theory_level == "HF"
        ):
            name += f"{self.method}_{self.basis_set}"
        else:
            name += f"{self.method}"
        if self.solvent.lower() != "vacuum":
            name += f"_{self.solvation_model}_{self.solvent}"
        return name

    @property
    def long_name(self):
        name = f"{self.software} - "
        if (
            self.theory_level == "DFT"
            or self.theory_level == "RI-MP2"
            or self.theory_level == "HF"
        ):
            name += f"{self.method}/{self.basis_set} "
        else:
            name += f"{self.method} "
        if self.solvent.lower() != "vacuum":
            name += f"({self.solvation_model}; {self.solvent.replace(',', '_')})"
        return name

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        values = [
            (k, v) for k, v in self.__dict__.items() if k != "_state" and k != "id"
        ]
        other_values = [
            (k, v) for k, v in other.__dict__.items() if k != "_state" and k != "id"
        ]

        # Not sure
        # values = [(k,v) for k,v in self.__dict__.items() if k not in ['_state', 'id', 'specifications']]
        # other_values = [(k,v) for k,v in other.__dict__.items() if k not in ['_state', 'id', 'specifications']]

        return values == other_values

    @property
    def md5(self):
        if self._md5 != "":
            return self._md5

        self._md5 = gen_params_md5(self)
        self.save()

        return self._md5


def gen_params_md5(obj):
    values = [(k, v) for k, v in obj.__dict__.items() if k != "_state" and k != "id"]
    params_str = ""
    for k, v in values:
        if isinstance(v, int):
            params_str += f"{k}={v};"
        elif isinstance(v, str):
            params_str += f"{k}={v.lower()};"
        else:
            raise Exception("Unknown value type")
    return hashlib.md5(bytes(params_str, "UTF-8")).hexdigest()


class Molecule(models.Model):
    name = models.CharField(max_length=100)
    inchi = models.CharField(max_length=1000, default="", blank=True, null=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, blank=True, null=True
    )

    @property
    def count_vis(self):
        return len(self.ensemble_set.filter(hidden=False))


class CalculationOrder(models.Model):
    name = models.CharField(max_length=100)

    structure = models.ForeignKey(
        Structure, on_delete=models.SET_NULL, blank=True, null=True
    )
    aux_structure = models.ForeignKey(
        Structure,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="aux_of_order",
    )

    ensemble = models.ForeignKey(
        Ensemble, on_delete=models.SET_NULL, blank=True, null=True
    )
    start_calc = models.ForeignKey(
        "Calculation", on_delete=models.SET_NULL, blank=True, null=True
    )
    start_calc_frame = models.PositiveIntegerField(default=0)

    result_ensemble = models.ForeignKey(
        Ensemble,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="result_of",
    )
    step = models.ForeignKey(
        BasicStep, on_delete=models.SET_NULL, blank=True, null=True
    )

    author = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    project = models.ForeignKey(
        "Project", on_delete=models.CASCADE, blank=True, null=True
    )
    parameters = models.ForeignKey(
        Parameters, on_delete=models.SET_NULL, blank=True, null=True
    )

    constraints = models.CharField(max_length=400, default="", blank=True, null=True)

    filter = models.ForeignKey(
        "Filter", on_delete=models.SET_NULL, blank=True, null=True
    )

    date = models.DateTimeField("date", null=True, blank=True)
    last_seen_status = models.PositiveIntegerField(default=0)
    hidden = models.BooleanField(default=False)

    resource = models.ForeignKey(
        "ClusterAccess", on_delete=models.SET_NULL, blank=True, null=True
    )

    def see(self):
        if self.last_seen_status != self.status:
            self.last_seen_status = self.status
            self.save()

            with transaction.atomic():
                p = Profile.objects.select_for_update().get(id=self.author.id)
                p.unseen_calculations = max(
                    p.unseen_calculations - 1, 0
                )  # Glitches may screw up the count...
                p.save()
        else:
            if not self.hidden and self.status in [2, 3]:
                self.hidden = True
                self.save()

    @property
    def color(self):
        return STATUS_COLORS[self.status]

    @property
    def label(self):
        if not self.step:
            return "Unknown"

        if self.step.creates_ensemble:
            if self.result_ensemble:
                return self.result_ensemble.name
            else:
                return "Processing..."
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
        elif (
            self.structure != None
            and self.structure.parent_ensemble != None
            and self.structure.parent_ensemble.parent_molecule != None
        ):
            return self.structure.parent_ensemble.parent_molecule.name
        elif (
            self.start_calc != None
            and self.start_calc.result_ensemble != None
            and self.start_calc.result_ensemble.parent_molecule != None
        ):
            return self.start_calc.result_ensemble.parent_molecule.name
        else:
            return "Unknown"

    @property
    def source(self):
        if self.ensemble != None and self.ensemble.parent_molecule != None:
            return self.ensemble.name, f"/ensemble/{self.ensemble.id}"
        elif self.structure != None and self.structure.parent_ensemble != None:
            return (
                self.structure.parent_ensemble.name,
                f"/ensemble/{self.structure.parent_ensemble.id}",
            )
        elif self.start_calc != None and self.start_calc.result_ensemble != None:
            return (
                self.start_calc.result_ensemble.name,
                f"/ensemble/{self.start_calc.result_ensemble.id}",
            )
        else:
            return "Unknown"

    @property
    def status(self):
        return self._status(*self.get_all_calcs)

    def update_unseen(self, old_status, old_unseen):
        new_status = self.status
        new_unseen = self.new_status

        if old_unseen:
            if not new_unseen:
                with transaction.atomic():
                    p = Profile.objects.select_for_update().get(id=self.author.id)
                    p.unseen_calculations -= 1
                    p.save()
        else:
            if new_unseen:
                with transaction.atomic():
                    p = Profile.objects.select_for_update().get(id=self.author.id)
                    p.unseen_calculations += 1
                    p.save()

    def _status(self, num_queued, num_running, num_done, num_error):
        if num_queued + num_running + num_done + num_error == 0:
            return 0

        if num_running > 0:
            return 1

        if num_queued == 0:
            if num_error > 0 and num_done == 0:
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
        res = {i: 0 for i in range(4)}

        for calc in self.calculation_set.all().values("status"):
            res[calc["status"]] += 1
        return [res[i] for i in range(4)]

    @property
    def new_status(self):
        if self.last_seen_status != self.status:
            return True
        else:
            return False

    def delete(self, *args, **kwargs):
        if self.new_status:
            with transaction.atomic():
                p = Profile.objects.select_for_update().get(id=self.author.id)
                p.unseen_calculations = max(0, p.unseen_calculations - 1)
                p.save()
        super(CalculationOrder, self).delete(*args, **kwargs)


class Calculation(models.Model):

    CALC_STATUSES = {
        "Queued": 0,
        "Running": 1,
        "Done": 2,
        "Error": 3,
    }

    INV_CALC_STATUSES = {v: k for k, v in CALC_STATUSES.items()}

    error_message = models.CharField(max_length=400, default="")
    current_status = models.CharField(max_length=400, default="")

    date_submitted = models.DateTimeField("date", null=True, blank=True)
    date_started = models.DateTimeField("date", null=True, blank=True)
    date_finished = models.DateTimeField("date", null=True, blank=True)

    status = models.PositiveIntegerField(default=0)
    error_message = models.CharField(max_length=400, default="", blank=True, null=True)

    structure = models.ForeignKey(Structure, on_delete=models.SET_NULL, null=True)
    aux_structure = models.ForeignKey(
        Structure, on_delete=models.SET_NULL, null=True, related_name="aux_of_calc"
    )

    step = models.ForeignKey(BasicStep, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(CalculationOrder, on_delete=models.CASCADE)

    parameters = models.ForeignKey(Parameters, on_delete=models.SET_NULL, null=True)
    result_ensemble = models.ForeignKey(
        Ensemble, on_delete=models.CASCADE, blank=True, null=True
    )

    constraints = models.CharField(max_length=400, default="", blank=True, null=True)

    input_file = models.CharField(max_length=50000, default="", blank=True, null=True)

    command = models.CharField(max_length=500, default="", blank=True, null=True)

    local = models.BooleanField(default=True)

    task_id = models.CharField(max_length=100, default="")

    remote_id = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.step.name

    @property
    def color(self):
        return STATUS_COLORS[self.status]

    def get_mol(self):
        if self.result_ensemble is not None:
            return self.result_ensemble.parent_molecule
        elif self.structure is not None:
            return self.structure.parent_ensemble.parent_molecule
        else:
            print("Could not find molecule to update!")

    def save(self, *args, **kwargs):
        old_status = self.order.status
        old_unseen = self.order.new_status

        super(Calculation, self).save(*args, **kwargs)
        self.order.update_unseen(old_status, old_unseen)

    def delete(self, *args, **kwargs):
        old_status = self.order.status
        old_unseen = self.order.new_status

        super(Calculation, self).delete(*args, **kwargs)

        self.order.update_unseen(old_status, old_unseen)

        if self.order.calculation_set.count() == 0:
            self.order.delete()

    @property
    def execution_time(self):
        if self.order.resource is None:
            return "-"
        if self.date_started is not None and self.date_finished is not None:
            if self.local:
                pal = os.getenv("OMP_NUM_THREADS")[0]
            else:
                pal = self.order.resource.pal
            return int((self.date_finished - self.date_started).seconds * int(pal))

        else:
            return "-"

    def __repr__(self):
        return str(self.id)

    @property
    def text_status(self):
        return self.INV_CALC_STATUSES[self.status]

    @property
    def all_inputs(self):
        return f"{self.command}\n{self.input_file}"


class Filter(models.Model):
    type = models.CharField(max_length=500)
    parameters = models.ForeignKey(Parameters, on_delete=models.CASCADE, null=True)
    value = models.CharField(max_length=500)


@receiver(post_save, sender=Parameters)
def update_parameters_hash(sender, instance, **kwargs):
    if kwargs["created"]:
        hash = gen_params_md5(instance)
        instance._md5 = hash
    # Parameters are not really modified, but the case where they are updated could be handled
    # Changing just to _md5 field should not trigger anything


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        code = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(16)
        )
        Profile.objects.create(user=instance, code=code)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
