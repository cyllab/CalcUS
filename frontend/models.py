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
from django.db.models import Case, Count, F, When
from django.db.models.signals import pre_delete, pre_save
from django.utils import timezone
from django.contrib.auth.models import (
    GroupManager,
    Permission,
    AbstractUser,
    BaseUserManager,
)

from django.contrib.postgres.fields import ArrayField
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django import template

import numpy as np
import ast
import json
import os
import hashlib
import time

from hashid_field import HashidAutoField, BigHashidAutoField

from .constants import (
    HARTREE_FVAL,
    HARTREE_TO_KCAL_F,
    NMR_REGRESSIONS,
    R_CONSTANT_HARTREE,
    TEMP,
    decimal,
)
from .helpers import clean_xyz, get_random_readable_code, job_triage
from .libxyz import format_xyz
from .environment_variables import PAL

import ccinput

register = template.Library()

STATUS_COLORS = {0: "#202f26", 1: "#e2e100", 2: "#02b200", 3: "#b21b00"}


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("No email provided")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must be staff")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must be superuser")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    id = BigHashidAutoField(
        primary_key=True, salt="User_hashid_" + settings.HASHID_FIELD_SALT
    )

    username = None
    email = models.EmailField("email", unique=True)
    full_name = models.CharField(max_length=256, default="")

    # Randomly generated password for temporary accounts.
    # Can be displayed to the user in order to have "semi-temporary" accounts
    random_password = models.CharField(max_length=64, default="")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    is_temporary = models.BooleanField(default=False)
    is_trial = models.BooleanField(default=False)

    member_of = models.ForeignKey(
        "ResearchGroup",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="members",
    )

    in_class = models.ForeignKey(
        "ClassGroup",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="members",
    )

    default_gaussian = models.CharField(max_length=1000, default="")
    default_orca = models.CharField(max_length=1000, default="")

    tour_done = models.BooleanField(default=False)
    opted_in_emails = models.BooleanField(default=False)

    advanced_interface = models.BooleanField(default=False)
    calc_type_property = models.BooleanField(default=True)
    calc_method_suggestions = models.BooleanField(default=True)

    code = models.CharField(max_length=16)  ### ?

    pref_units = models.PositiveIntegerField(default=0)
    unseen_calculations = models.PositiveIntegerField(default=0)

    UNITS = {0: "kJ/mol", 1: "kcal/mol", 2: "Eh"}
    UNITS_PRECISION = {0: 0, 1: 1, 2: 6}
    UNITS_FORMAT_STRING = {0: "{:.1f}", 1: "{:.1f}", 2: "{:.6f}"}

    INV_UNITS = {v: k for k, v in UNITS.items()}

    stripe_cus_id = models.CharField(max_length=256, default="")
    stripe_will_renew = models.BooleanField(default=True)

    # Total/allocated computation time and time consumed by user or class/group
    # These numbers should be accurate, but are not the official references
    # Instead, allocated_seconds should be recalculated from ResourceAllocation objects
    # and billed_seconds from Calculation objects whose resource_provider is the current user
    allocated_seconds = models.PositiveIntegerField(default=0)
    # For temporary users, both their billed_seconds and the professor's will be incremented in order to enforce the usage limit
    billed_seconds = models.PositiveIntegerField(default=0)

    last_free_refill = models.DateTimeField(
        "date",
        default=timezone.make_aware(
            timezone.datetime(year=2000, month=1, day=1, hour=1, minute=1)
        ),
    )

    @property
    def user_type(self):
        if self.is_trial:
            return "trial"
        elif self.is_subscriber:
            return "subscriber"
        else:
            if self.member_of is not None and self.member_of.PI.is_subscriber:
                return "subscriber"
            return "free"

    @property
    def active_subscription(self):
        subs = self.subscription_set.all()
        now = timezone.now()
        for sub in subs:
            if now > sub.start_date and now < sub.end_date:
                return sub
        return None

    @property
    def is_subscriber(self):
        if not settings.IS_CLOUD:
            return True
        return self.active_subscription is not None

    @property
    def resource_provider(self):
        if self.is_PI:
            return self

        if self.is_temporary:
            if self.in_class:
                return self.in_class.professor
            if self.is_trial:
                return self
            else:
                raise Exception(
                    f"Unexpected case for the resource provider of user {self.id} (self.name)"
                )

        if self.member_of:
            return self.member_of.PI

        return self

    @property
    def remaining_time(self):
        if self.resource_provider != self:
            return self.resource_provider.remaining_time
        return self.allocated_seconds - self.billed_seconds

    def has_sufficient_resources(self, expected_time):
        t = self.remaining_time

        # Not fool-proof or entirely safe, but good enough for now
        if t > expected_time:
            return True
        return False

    def bill_time(self, time):
        """
        Directly bills the user for computation time
        """
        with transaction.atomic():
            user = User.objects.select_for_update().get(id=self.id)
            user.billed_seconds += time
            user.save()

        return user

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if "unseen_calculations" in field_names:
            instance._loaded_unseen_calculations = instance.unseen_calculations
        else:
            instance._loaded_unseen_calculations = None
        return instance

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        should_preserve_unseen = self.pk is not None and (
            (update_fields is not None and "unseen_calculations" not in update_fields)
            or (
                update_fields is None
                and hasattr(self, "_loaded_unseen_calculations")
                and self._loaded_unseen_calculations is not None
                and self.unseen_calculations == self._loaded_unseen_calculations
            )
        )
        if should_preserve_unseen:
            current_unseen = (
                User.objects.filter(id=self.pk)
                .values_list("unseen_calculations", flat=True)
                .first()
            )
            if current_unseen is not None:
                self.unseen_calculations = current_unseen

        super().save(*args, **kwargs)
        self._loaded_unseen_calculations = self.unseen_calculations

    @property
    def is_PI(self):
        return self.PI_of.first() is not None

    @property
    def name(self):
        if self.full_name:
            return self.full_name
        return f"User {self.id}"

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

    def __str__(self):
        return self.name

    @property
    def group(self):
        if self.is_PI:
            if self.PI_of.count() > 0:
                # TODO: handle multiple groups
                return self.PI_of.all()[0]
            else:
                return None
        else:
            return self.member_of

    @property
    def accesses(self):
        return self.clusteraccess_owner.all()


class Subscription(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="Subscription_hashid_" + settings.HASHID_FIELD_SALT
    )

    subscriber = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    associated_allocation = models.ForeignKey(
        "ResourceAllocation", on_delete=models.SET_NULL, null=True
    )

    start_date = models.DateTimeField("date")
    end_date = models.DateTimeField("date")

    stripe_sub_id = models.CharField(max_length=256, default="")


class ResourceAllocation(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="ResourceAllocation_hashid_" + settings.HASHID_FIELD_SALT
    )

    # Code to redeem the allocation manually
    code = models.CharField(max_length=256)
    redeemer = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    allocation_seconds = models.PositiveIntegerField()

    TRIAL = 1
    NEW_ACCOUNT = 2
    TESTER = 3
    PURCHASE = 4
    SUBSCRIPTION = 5
    TRIAL_CONVERSION = 6
    MONTHLY_FREE_REFILL = 7

    MANUAL = 99

    NOTES = [
        (TRIAL, "Trial"),
        (NEW_ACCOUNT, "New account"),
        (TRIAL_CONVERSION, "Trial conversion"),
        (TESTER, "Tester"),
        (PURCHASE, "Purchase"),
        (SUBSCRIPTION, "Subscription"),
        (MANUAL, "Manually issued allocation"),
        (MONTHLY_FREE_REFILL, "Monthly free refill"),
    ]
    note = models.PositiveSmallIntegerField(choices=NOTES, default=99)

    def redeem(self, user, stall=0):
        with transaction.atomic():
            alloc = ResourceAllocation.objects.select_for_update().get(id=self.id)

            # For testing purposes
            if stall != 0:
                time.sleep(stall)

            if alloc.redeemer:
                return False
            alloc.redeemer = user
            alloc.save()

        with transaction.atomic():
            u = User.objects.select_for_update().get(id=user.id)
            u.allocated_seconds += alloc.allocation_seconds
            u.save()

        return True


class Example(models.Model):
    title = models.CharField(max_length=100)
    page_path = models.CharField(max_length=100)


class Recipe(models.Model):
    title = models.CharField(max_length=100)
    page_path = models.CharField(max_length=100)


class ResearchGroup(models.Model):
    name = models.CharField("name", max_length=150, unique=True)
    permissions = models.ManyToManyField(
        Permission,
        verbose_name="permissions",
        blank=True,
    )

    objects = GroupManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    id = HashidAutoField(
        primary_key=True, salt="ResearchGroup_hashid_" + settings.HASHID_FIELD_SALT
    )

    PI = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="PI_of",
    )

    def __repr__(self):
        return self.name


class ClassGroup(models.Model):
    name = models.CharField("name", max_length=150, unique=True)
    permissions = models.ManyToManyField(
        Permission,
        verbose_name="permissions",
        blank=True,
    )

    objects = GroupManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    id = HashidAutoField(
        primary_key=True, salt="ClassGroup_hashid_" + settings.HASHID_FIELD_SALT
    )

    professor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="professor_of",
    )

    # Maximal computation time per user or per group, in seconds
    # 0 means no limit
    user_resource_threshold = models.PositiveIntegerField(default=5 * 60)
    group_resource_threshold = models.PositiveIntegerField(default=0)

    # Randomly generated code upon group creation
    # Allows student to join the group
    access_code = models.CharField(max_length=256)

    def __repr__(self):
        return self.name

    def generate_code(self):
        self.access_code = get_random_readable_code()
        self.save()


class Flowchart(models.Model):
    name = models.CharField(max_length=100)
    author = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    flowchart = models.JSONField(null=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Project(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="Project_hashid_" + settings.HASHID_FIELD_SALT
    )
    name = models.CharField(max_length=100)
    author = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
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

    def save(self, *args, **kwargs):
        rename = kwargs.pop("rename", False)
        if rename:
            self._is_renaming = True
        super().save(*args, **kwargs)


@receiver(post_save, sender=Project)
def create_main_folder(sender, instance, created, **kwargs):
    if created:
        instance.main_folder = Folder.objects.create(
            name="Main Folder", project=instance, depth=0
        )
        instance.main_folder.save()
        instance.save()


class Folder(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="Folder_hashid_" + settings.HASHID_FIELD_SALT
    )
    name = models.CharField(max_length=100)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, blank=True, null=True
    )
    parent_folder = models.ForeignKey(
        "Folder", on_delete=models.SET_NULL, blank=True, null=True
    )
    depth = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        rename = kwargs.pop("rename", False)
        if rename:
            self._is_renaming = True
        super().save(*args, **kwargs)


class ClusterAccess(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="ClusterAccess_hashid_" + settings.HASHID_FIELD_SALT
    )
    owner = models.ForeignKey(
        User,
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
    prop_name = models.CharField(max_length=100, default="")

    avail_xtb = models.BooleanField(default=False)
    avail_Gaussian = models.BooleanField(default=False)
    avail_ORCA = models.BooleanField(default=False)
    avail_NWChem = models.BooleanField(default=False)

    creates_ensemble = models.BooleanField(default=False)


class Preset(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="Preset_hashid_" + settings.HASHID_FIELD_SALT
    )
    name = models.CharField(max_length=100, default="My Preset")
    params = models.ForeignKey(
        "Parameters", on_delete=models.SET_NULL, blank=True, null=True
    )
    author = models.ForeignKey("User", on_delete=models.CASCADE, blank=True, null=True)


class Ensemble(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="Ensemble_hashid_" + settings.HASHID_FIELD_SALT
    )
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

    def save(self, *args, **kwargs):
        rename = kwargs.pop("rename", False)
        if rename:
            self._is_renaming = True
        super().save(*args, **kwargs)

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
        for s in self.structure_set.all():
            for p in s.properties.all():
                if not _in(p.parameters, unique):
                    unique.append(p.parameters)

        return unique

    @property
    def unique_calculations(self):
        unique = []
        for s in self.structure_set.all():
            for c in s.calculation_set.values("step__name"):
                if c["step__name"] not in unique:
                    unique.append(c["step__name"])
        return unique

    def has_nmr(self, params):
        for s in self.structure_set.all():
            try:
                props = s.properties.filter(parameters=params).all()
            except Property.DoesNotExist:
                continue  # Handle this better?
            for p in props:
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
    id = BigHashidAutoField(
        primary_key=True,
        salt="Property_hashid_" + settings.HASHID_FIELD_SALT,
        db_index=True,
    )
    parameters = models.ForeignKey(
        "Parameters", on_delete=models.SET_NULL, blank=True, null=True, db_index=True
    )
    parent_structure = models.ForeignKey(
        "Structure",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="properties",
        db_index=True,
    )

    energy = models.FloatField(default=0)
    free_energy = models.FloatField(default=0)

    uvvis = models.TextField(default="")
    nmr = models.TextField(default="")
    mo_diagram = models.TextField(default="")
    molden = models.TextField(default="")
    esp = models.TextField(default="")
    freq_list = ArrayField(models.FloatField(), default=list)
    freq_animations = ArrayField(models.TextField(), default=list)
    ir_spectrum = models.TextField(default="")
    property_file_manifest = models.JSONField(default=dict, blank=True)

    simple_nmr = models.CharField(default="", max_length=100000)  # TODO: to array
    charges = models.CharField(default="", max_length=100000)  # TODO: to array

    geom = models.BooleanField(default=False)

    @property
    def has_freq(self):
        return len(self.freq_list) > 0

    @property
    def has_negative_freq(self):
        return any(freq < 0 for freq in self.freq_list)

    @property
    def negative_freq_count(self):
        return sum(1 for freq in self.freq_list if freq < 0)

    def get_negative_freq_index(self, negative_freq_num=1):
        try:
            negative_freq_num = int(negative_freq_num)
        except (TypeError, ValueError):
            return None

        if negative_freq_num < 1:
            return None

        negative_freq_indices = [
            ind
            for ind, freq in sorted(enumerate(self.freq_list), key=lambda item: item[1])
            if freq < 0
        ]
        if negative_freq_num > len(negative_freq_indices):
            return None
        return negative_freq_indices[negative_freq_num - 1]

    @property
    def most_negative_freq_index(self):
        return self.get_negative_freq_index(1)

    def get_heavy_property(self, field):
        from .storage_backends.property_storage import read_property_file

        return read_property_file(self, field)

    def save(self, *args, **kwargs):
        from .storage_backends.property_storage import (
            HEAVY_PROPERTY_FIELDS,
            empty_value,
            is_empty_value,
            save_property_files,
        )

        backend_name = settings.CALCULATION_OUTPUT_STORAGE_BACKEND.lower()
        if backend_name == "database":
            return super().save(*args, **kwargs)

        update_fields = kwargs.get("update_fields")
        if update_fields is None:
            fields_to_check = HEAVY_PROPERTY_FIELDS
        else:
            update_fields_set = set(update_fields)
            fields_to_check = [
                field for field in HEAVY_PROPERTY_FIELDS if field in update_fields_set
            ]

        heavy_values = {}
        for field in fields_to_check:
            value = self.__dict__.get(field, empty_value(field))
            if update_fields is not None or not is_empty_value(field, value):
                heavy_values[field] = value

        if not heavy_values:
            return super().save(*args, **kwargs)

        originals = {field: self.__dict__.get(field) for field in heavy_values}
        for field in heavy_values:
            self.__dict__[field] = empty_value(field)

        if update_fields is not None:
            kwargs["update_fields"] = list(set(update_fields) | set(heavy_values))

        super().save(*args, **kwargs)
        save_property_files(self, heavy_values, backend_name=backend_name)

        for field, value in originals.items():
            self.__dict__[field] = value

    def get_distorted_structure(self, scale=0.87, negative_freq_num=1):
        freq_animations = self.get_heavy_property("freq_animations")
        mode_ind = self.get_negative_freq_index(negative_freq_num)
        if mode_ind is None or mode_ind >= len(freq_animations):
            return ""

        distorted_xyz = []
        for line in freq_animations[mode_ind].replace("\xa0", " ").splitlines()[2:]:
            if line.strip() == "":
                continue

            parts = line.split()
            if len(parts) < 7:
                return ""

            atom = parts[0]
            coords = np.array([float(i) for i in parts[1:4]])
            displacement = np.array([float(i) for i in parts[4:7]])
            distorted_xyz.append([atom, coords + displacement * scale])

        if len(distorted_xyz) == 0:
            return ""

        return clean_xyz(format_xyz(distorted_xyz, header_text="CalcUS"))

    @property
    def has_uvvis(self):
        return len(self.get_heavy_property("uvvis")) > 0

    @property
    def has_nmr(self):
        return len(self.nmr) > 0

    @property
    def has_mo(self):
        return len(self.get_heavy_property("mo_diagram")) > 0

    @property
    def has_esp(self):
        return len(self.get_heavy_property("esp")) > 0


@receiver(pre_delete, sender=Property)
def property_deleted(sender, instance, **kwargs):
    from .storage_backends.property_storage import delete_property_files

    transaction.on_commit(lambda: delete_property_files(instance, save=False))


class ShowcaseProperty(Property):
    name = models.TextField()


class Structure(models.Model):
    id = BigHashidAutoField(
        primary_key=True,
        salt="Structure_hashid_" + settings.HASHID_FIELD_SALT,
        db_index=True,
    )
    parent_ensemble = models.ForeignKey(
        Ensemble, on_delete=models.CASCADE, blank=True, null=True, db_index=True
    )

    xyz_structure = models.CharField(default="", max_length=5000000)

    number = models.PositiveIntegerField(default=1)
    degeneracy = models.PositiveIntegerField(default=1)


class ShowcaseEnsemble(Ensemble):
    label = models.TextField()


class CalculationFrame(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="CalculationFrame_hashid_" + settings.HASHID_FIELD_SALT
    )
    parent_calculation = models.ForeignKey(
        "Calculation", on_delete=models.CASCADE, blank=True, null=True
    )

    xyz_structure = models.CharField(default="", max_length=5000000)
    RMSD = models.FloatField(default=0)
    converged = models.BooleanField(default=False)
    energy = models.FloatField(default=0)

    number = models.PositiveIntegerField(default=0)


class Parameters(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="Parameters_hashid_" + settings.HASHID_FIELD_SALT
    )
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

    driver = models.CharField(max_length=100, default="")

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
        for field in ["method", "basis_set", "solvent"]:
            try:
                m1 = getattr(ccinput.utilities, f"get_abs_{field}")(
                    getattr(self, field)
                )
            except ccinput.exceptions.InvalidParameter:
                m1 = getattr(self, field)
            try:
                m2 = getattr(ccinput.utilities, f"get_abs_{field}")(
                    getattr(self, field)
                )
            except ccinput.exceptions.InvalidParameter:
                m2 = getattr(self, field)

            if m1 != m2:
                return False

        excluded_fields = [
            "_state",
            "id",
            "charge",
            "multiplicity",
            "specifications",
            # Previously compared fields
            "method",
            "basis_set",
            "solvent",
        ]

        values = [(k, v) for k, v in self.__dict__.items() if k not in excluded_fields]
        other_values = [
            (k, v) for k, v in other.__dict__.items() if k not in excluded_fields
        ]

        return values == other_values

    @property
    def md5(self):
        if self._md5 != "":
            return self._md5

        self._md5 = gen_params_md5(self)
        self.save()

        return self._md5


class Step(models.Model):
    name = models.CharField(max_length=50)
    flowchart = models.ForeignKey(Flowchart, on_delete=models.CASCADE, default=None)
    step = models.ForeignKey(
        BasicStep, on_delete=models.SET_NULL, blank=True, null=True
    )
    parameters = models.ForeignKey(
        Parameters, on_delete=models.SET_NULL, blank=True, null=True
    )
    parentId = models.ForeignKey(
        "Step", related_name="+", on_delete=models.CASCADE, blank=True, null=True
    )

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


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
    id = BigHashidAutoField(
        primary_key=True, salt="Molecule_hashid_" + settings.HASHID_FIELD_SALT
    )
    name = models.CharField(max_length=100)
    inchi = models.CharField(max_length=10000, default="", blank=True, null=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, blank=True, null=True
    )

    @property
    def count_vis(self):
        return len(self.ensemble_set.filter(hidden=False))

    def save(self, *args, **kwargs):
        rename = kwargs.pop("rename", False)
        if rename:
            self._is_renaming = True
        super().save(*args, **kwargs)


class FlowchartOrder(models.Model):
    name = models.CharField(max_length=100)
    structure = models.ForeignKey(
        Structure, on_delete=models.SET_NULL, blank=True, null=True
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    project = models.ForeignKey(
        "Project", on_delete=models.CASCADE, blank=True, null=True
    )
    flowchart = models.ForeignKey(
        Flowchart, on_delete=models.CASCADE, default=None, null=True
    )
    ensemble = models.ForeignKey(
        Ensemble, on_delete=models.SET_NULL, blank=True, null=True
    )
    filter = models.ForeignKey(
        "Filter", on_delete=models.SET_NULL, blank=True, null=True
    )
    last_seen_status = models.PositiveIntegerField(default=0)
    date = models.DateTimeField("date", null=True, blank=True)

    @property
    def status(self):
        return self._status(*self.get_all_calcs)

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


class CalculationOrder(models.Model):
    id = BigHashidAutoField(
        primary_key=True,
        salt="CalculationOrder_hashid_" + settings.HASHID_FIELD_SALT,
        db_index=True,
    )
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

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True, db_index=True
    )

    # Account billed for the resource usage
    # Set when creating the order, then never modified
    resource_provider = models.ForeignKey(
        User,
        related_name="provider_of",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    project = models.ForeignKey(
        "Project", on_delete=models.CASCADE, blank=True, null=True
    )
    parameters = models.ForeignKey(
        Parameters, on_delete=models.SET_NULL, blank=True, null=True
    )

    constraints = models.CharField(max_length=1000, default="", blank=True, null=True)

    filter = models.ForeignKey(
        "Filter", on_delete=models.SET_NULL, blank=True, null=True
    )

    hidden = models.BooleanField(default=False)

    resource = models.ForeignKey(
        "ClusterAccess", on_delete=models.SET_NULL, blank=True, null=True
    )

    date = models.DateTimeField("date", null=True, blank=True)
    last_seen_status = models.PositiveIntegerField(default=0)
    cached_status = models.PositiveIntegerField(default=0)
    total_cpu_time = models.PositiveBigIntegerField(default=0)
    _calc_statuses = models.CharField(max_length=50, default="")

    _label = models.CharField(max_length=200, default="")
    _molecule_name = models.CharField(max_length=200, default="")
    _source = models.CharField(max_length=200, default="")

    _project_name = models.CharField(max_length=200, default="")
    _step_name = models.CharField(max_length=200, default="")

    @classmethod
    def _update_unseen_counter(cls, user_id, delta):
        if user_id is None:
            return

        unseen = (
            cls.objects.filter(author_id=user_id, hidden=False)
            .exclude(last_seen_status=F("cached_status"))
            .count()
        )
        User.objects.filter(id=user_id).update(unseen_calculations=unseen)

    def see(self):
        with transaction.atomic():
            order = (
                CalculationOrder.objects.select_for_update()
                .only("id", "author_id", "last_seen_status", "cached_status", "hidden")
                .get(id=self.id)
            )

            update_fields = []
            delta = 0
            was_new = order.last_seen_status != order.cached_status

            if was_new:
                order.last_seen_status = order.cached_status
                update_fields.append("last_seen_status")
                delta = -1

            if not was_new and not order.hidden and order.cached_status in [2, 3]:
                order.hidden = True
                update_fields.append("hidden")

            if update_fields:
                order.save(update_fields=update_fields)

            CalculationOrder._update_unseen_counter(order.author_id, delta)

    @property
    def color(self):
        return STATUS_COLORS[self.status]

    @property
    def label(self):
        if self._label == "":
            self._label = self._get_label()
            self.save(update_fields=["_label"])
        return self._label

    def _get_label(self):
        if settings.IS_TEST and self.step is None:
            if self.result_ensemble is not None:
                return self.result_ensemble.name
            if self.ensemble is not None:
                return self.ensemble.name
            if (
                self.structure is not None
                and self.structure.parent_ensemble is not None
            ):
                return self.structure.parent_ensemble.name
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
        if self._molecule_name == "":
            self._molecule_name = self._get_molecule_name()
            self.save(update_fields=["_molecule_name"])
        return self._molecule_name

    @property
    def step_name(self):
        if self._step_name == "":
            if settings.IS_TEST and self.step is None:
                self._step_name = "Unknown"
            else:
                self._step_name = self.step.name
            self.save(update_fields=["_step_name"])
        return self._step_name

    @property
    def project_name(self):
        if self._project_name == "":
            if settings.IS_TEST and self.project is None:
                self._project_name = "Unknown"
            else:
                self._project_name = self.project.name
            self.save(update_fields=["_project_name"])
        return self._project_name

    def _get_molecule_name(self):
        if self.ensemble is not None and self.ensemble.parent_molecule is not None:
            return self.ensemble.parent_molecule.name
        elif (
            self.structure is not None
            and self.structure.parent_ensemble is not None
            and self.structure.parent_ensemble.parent_molecule is not None
        ):
            return self.structure.parent_ensemble.parent_molecule.name
        elif (
            self.start_calc is not None
            and self.start_calc.result_ensemble is not None
            and self.start_calc.result_ensemble.parent_molecule is not None
        ):
            return self.start_calc.result_ensemble.parent_molecule.name
        else:
            return "Unknown"

    @property
    def source(self):
        source = self._deserialize_source(self._source)
        if source is not None:
            return source

        source = self._get_source()
        self._source = self._serialize_source(source)
        self.save(update_fields=["_source"])
        return source

    @staticmethod
    def _serialize_source(source):
        return json.dumps(list(source))

    @staticmethod
    def _deserialize_source(source):
        if source == "":
            return None

        if source == "Unknown":
            return ("Unknown", "")

        try:
            parsed = json.loads(source)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(source)
            except (ValueError, SyntaxError):
                return ("Unknown", "")

        if isinstance(parsed, (list, tuple)) and len(parsed) == 2:
            return (parsed[0], parsed[1])

        return ("Unknown", "")

    def _get_source(self):
        if self.ensemble is not None and self.ensemble.parent_molecule is not None:
            return self.ensemble.name, f"/ensemble/{self.ensemble.id}"
        elif self.structure is not None and self.structure.parent_ensemble is not None:
            return (
                self.structure.parent_ensemble.name,
                f"/ensemble/{self.structure.parent_ensemble.id}",
            )
        elif (
            self.start_calc is not None and self.start_calc.result_ensemble is not None
        ):
            return (
                self.start_calc.result_ensemble.name,
                f"/ensemble/{self.start_calc.result_ensemble.id}",
            )
        else:
            return ("Unknown", "")

    @property
    def calc_statuses(self):
        if self._calc_statuses == "":
            return ""
        return [int(i) for i in self._calc_statuses.split(",")]

    @calc_statuses.setter
    def calc_statuses(self, val):
        self._calc_statuses = ",".join([str(i) for i in val])
        # Derive cached status from the same counter snapshot being stored.
        # Calling ensure_status() here may read stale DB rows during calc pre-save.
        self.cached_status = self._status(*val)

    def set_calc_statuses(self):
        statuses = self.get_all_calcs
        self.calc_statuses = statuses
        return statuses

    def _sync_cached_status(self, statuses, persist_statuses=False):
        stat = self._status(*statuses)
        should_save = persist_statuses or stat != self.cached_status

        if should_save:
            self.cached_status = stat
            update_fields = ["cached_status"]
            if persist_statuses:
                update_fields.append("_calc_statuses")
            self.save(update_fields=update_fields)

        return stat

    @property
    def status(self):
        if self.calc_statuses == "":
            statuses = self.set_calc_statuses()
            persist_statuses = True
        else:
            statuses = self.calc_statuses
            persist_statuses = False

        return self._sync_cached_status(statuses, persist_statuses=persist_statuses)

    def ensure_status(self):
        """Triggers a manual update of the status"""
        return self._status(*self.get_all_calcs)

    @staticmethod
    def _serialize_calc_statuses(statuses):
        return ",".join(str(i) for i in statuses)

    @classmethod
    def _count_calc_statuses(cls, order_id):
        counts = [0, 0, 0, 0]
        rows = (
            Calculation.objects.filter(order_id=order_id)
            .values("status")
            .annotate(total=Count("id"))
        )
        for row in rows:
            counts[row["status"]] = row["total"]
        return counts

    @classmethod
    def _get_total_cpu_time(cls, order_id):
        total_cpu_time = 0

        for calc in Calculation.objects.filter(order_id=order_id).select_related(
            "order__resource"
        ):
            if (
                settings.IS_CLOUD
                and calc.status != Calculation.CALC_STATUSES["Running"]
            ):
                total_cpu_time += calc.billed_seconds
            else:
                total_cpu_time += calc.execution_time

        return max(0, total_cpu_time)

    @classmethod
    def sync_cache(cls, order_id):
        if order_id is None:
            return

        with transaction.atomic():
            order = (
                cls.objects.select_for_update()
                .only("id", "author_id", "last_seen_status", "cached_status")
                .filter(id=order_id)
                .first()
            )
            if order is None:
                return

            old_status = order.cached_status
            old_unseen = order.last_seen_status != old_status
            statuses = cls._count_calc_statuses(order_id)

            if sum(statuses) == 0:
                if old_unseen:
                    cls._update_unseen_counter(order.author_id, -1)
                cls.objects.filter(id=order_id).delete()
                return

            new_status = order._status(*statuses)
            total_cpu_time = cls._get_total_cpu_time(order_id)
            cls.objects.filter(id=order_id).update(
                _calc_statuses=cls._serialize_calc_statuses(statuses),
                cached_status=new_status,
                total_cpu_time=total_cpu_time,
            )

            new_unseen = order.last_seen_status != new_status
            if old_unseen == new_unseen:
                return

            if new_unseen:
                cls._update_unseen_counter(order.author_id, 1)
            else:
                cls._update_unseen_counter(order.author_id, -1)

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
    def get_data(self):
        """Returns a list of [queued, running, done, error, net_status, total_time, new_status]"""
        calc_statuses = self.calc_statuses
        persist_statuses = False
        if calc_statuses == "":
            calc_statuses = self.set_calc_statuses()
            persist_statuses = True

        nums = calc_statuses + [0, 0, 0]
        nums[5] = self.total_cpu_time
        nums[4] = self._sync_cached_status(
            calc_statuses, persist_statuses=persist_statuses
        )

        if self.last_seen_status != nums[4]:
            nums[6] = 1

        return nums

    @property
    def get_all_calcs(self):
        res = {i: 0 for i in range(4)}

        for calc in self.calculation_set.values("status"):
            res[calc["status"]] += 1
        return [res[i] for i in range(4)]

    @property
    def new_status(self):
        if self.last_seen_status != self.status:
            return True
        else:
            return False

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if self.pk is not None and update_fields is not None:
            current_cache = (
                CalculationOrder.objects.filter(id=self.pk)
                .values(
                    "hidden",
                    "last_seen_status",
                    "cached_status",
                    "_calc_statuses",
                    "total_cpu_time",
                )
                .first()
            )
            if current_cache is not None:
                for field, value in current_cache.items():
                    if update_fields is None or field not in update_fields:
                        setattr(self, field, value)

        if self.step_id is not None or (settings.IS_TEST and self.step is None):
            new_label = self._get_label()
            if self._label != new_label:
                self._label = new_label
                if update_fields is not None and "_label" not in update_fields:
                    kwargs["update_fields"] = list(update_fields) + ["_label"]
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            order = (
                CalculationOrder.objects.select_for_update()
                .only("id", "author_id", "last_seen_status", "cached_status")
                .filter(id=self.id)
                .first()
            )

            if order is None:
                return super(CalculationOrder, self).delete(*args, **kwargs)

            delta = -1 if order.last_seen_status != order.cached_status else 0
            ret = super(CalculationOrder, self).delete(*args, **kwargs)
            CalculationOrder._update_unseen_counter(order.author_id, delta)
            return ret


class Calculation(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="Calculation_hashid_" + settings.HASHID_FIELD_SALT
    )
    CALC_STATUSES = {
        "Queued": 0,
        "Running": 1,
        "Done": 2,
        "Error": 3,
    }

    INV_CALC_STATUSES = {v: k for k, v in CALC_STATUSES.items()}

    error_message = models.CharField(max_length=1000, default="")
    current_status = models.CharField(max_length=1000, default="")

    date_submitted = models.DateTimeField("date", null=True, blank=True)
    date_started = models.DateTimeField("date", null=True, blank=True)
    date_finished = models.DateTimeField("date", null=True, blank=True)
    billed_seconds = models.PositiveIntegerField(default=0)

    status = models.PositiveIntegerField(default=0, db_index=True)
    error_message = models.CharField(max_length=1000, default="", blank=True, null=True)

    structure = models.ForeignKey(Structure, on_delete=models.SET_NULL, null=True)
    aux_structure = models.ForeignKey(
        Structure, on_delete=models.SET_NULL, null=True, related_name="aux_of_calc"
    )

    step = models.ForeignKey(BasicStep, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(
        CalculationOrder, on_delete=models.CASCADE, blank=True, null=True, db_index=True
    )
    flowchart_order = models.ForeignKey(
        FlowchartOrder, on_delete=models.CASCADE, blank=True, null=True
    )
    flowchart_step = models.ForeignKey(
        Step, on_delete=models.CASCADE, blank=True, null=True
    )

    parameters = models.ForeignKey(Parameters, on_delete=models.SET_NULL, null=True)
    result_ensemble = models.ForeignKey(
        Ensemble, on_delete=models.CASCADE, blank=True, null=True
    )

    constraints = models.CharField(max_length=1000, default="", blank=True, null=True)

    input_file = models.CharField(max_length=50000, default="", blank=True, null=True)

    command = models.CharField(max_length=500, default="", blank=True, null=True)

    local = models.BooleanField(default=True)

    task_id = models.CharField(max_length=100, default="")

    remote_id = models.PositiveIntegerField(default=0)

    output_files = models.TextField(default="")
    output_file_manifest = models.JSONField(default=dict, blank=True)
    frame_file_manifest = models.JSONField(default=dict, blank=True)

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

    @property
    def corresponding_ensemble(self):
        if self.result_ensemble is not None:
            return self.result_ensemble
        elif self.structure is not None:
            return self.structure.parent_ensemble
        else:
            print("Could not find the corresponding ensemble")

    def save(self, *args, **kwargs):
        if self.order is None:
            raise Exception("No calculation order")

        previous_state = None
        if self.pk is not None:
            previous_state = (
                Calculation.objects.filter(id=self.pk)
                .values(
                    "status",
                    "order_id",
                    "date_started",
                    "date_finished",
                    "billed_seconds",
                )
                .first()
            )

        super().save(*args, **kwargs)
        if previous_state is None or any(
            [
                previous_state["status"] != self.status,
                previous_state["order_id"] != self.order_id,
                previous_state["date_started"] != self.date_started,
                previous_state["date_finished"] != self.date_finished,
                previous_state["billed_seconds"] != self.billed_seconds,
            ]
        ):
            CalculationOrder.sync_cache(self.order_id)

    def delete(self, *args, **kwargs):
        if self.order is None:
            return super().delete(*args, **kwargs)

        order_id = self.order_id
        super().delete(*args, **kwargs)
        CalculationOrder.sync_cache(order_id)

    @property
    def execution_time(self):
        if self.date_started is None:
            return 0
        if self.date_finished is None:
            end_date = timezone.now()
        else:
            end_date = self.date_finished

        elapsed_seconds = max(0, (end_date - self.date_started).total_seconds())

        if settings.IS_CLOUD:
            nproc, limit = job_triage(self)
            return round(elapsed_seconds * nproc)
        if self.local:
            return round(elapsed_seconds * PAL)

        if self.order.resource is None:
            # Shouldn't happen
            return 0

        if self.local:
            pal = os.getenv("OMP_NUM_THREADS")[0]
        else:
            pal = self.order.resource.pal
        return int(elapsed_seconds * int(pal))

    def __repr__(self):
        return str(self.id)

    @property
    def text_status(self):
        return self.INV_CALC_STATUSES[self.status]

    @property
    def all_inputs(self):
        return f"{self.command}\n{self.input_file}"

    def set_as_cancelled(self):
        with transaction.atomic():
            calc = Calculation.objects.select_for_update().get(id=self.id)
            calc.status = 3
            calc.save()


@receiver(pre_delete, sender=Calculation)
def calculation_deleted(sender, instance, **kwargs):
    from .storage_backends.calculation_outputs import delete_output_files
    from .storage_backends.calculation_frames import delete_frame_files

    transaction.on_commit(lambda: delete_output_files(instance, save=False))
    transaction.on_commit(lambda: delete_frame_files(instance, save=False))


class BatchCalcOrder(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="BatchCalc_hashid_" + settings.HASHID_FIELD_SALT
    )
    step = models.ForeignKey(
        BasicStep, on_delete=models.SET_NULL, blank=True, null=True
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    project = models.ForeignKey(
        "Project", on_delete=models.CASCADE, blank=True, null=True
    )
    date = models.DateTimeField("date", null=True, blank=True)


class BatchCalculation(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="BatchCalc_hashid_" + settings.HASHID_FIELD_SALT
    )
    batch_name = models.CharField(max_length=100)
    parametersets = models.JSONField(default=list)
    parameters = models.ForeignKey(
        Parameters, on_delete=models.SET_NULL, blank=True, null=True
    )
    structure = models.ForeignKey(
        Structure, on_delete=models.SET_NULL, blank=True, null=True
    )
    calculationorder = models.ForeignKey(
        BatchCalcOrder, on_delete=models.SET_NULL, blank=True, null=True
    )


class Filter(models.Model):
    id = BigHashidAutoField(
        primary_key=True, salt="Calculation_hashid_" + settings.HASHID_FIELD_SALT
    )
    type = models.CharField(max_length=500)
    parameters = models.ForeignKey(Parameters, on_delete=models.CASCADE, null=True)
    value = models.CharField(max_length=500)


@receiver(post_save, sender=Ensemble)
def ensemble_renamed(sender, instance, **kwargs):
    if getattr(instance, "_is_renaming", False):
        for o in instance.calculationorder_set.all():
            o._source = o._serialize_source(o._get_source())
            o._label = o._get_label()
            o.save(update_fields=["_source", "_label"])
        for o in instance.result_of.all():
            o._label = o._get_label()
            o.save(update_fields=["_label"])
        for s in instance.structure_set.all():
            for o in s.calculationorder_set.all():
                o._label = o._get_label()
                o._source = o._serialize_source(o._get_source())
                o.save(update_fields=["_label", "_source"])


@receiver(post_save, sender=Molecule)
def molecule_renamed(sender, instance, **kwargs):
    if getattr(instance, "_is_renaming", False):
        for e in instance.ensemble_set.all():
            for o in e.calculationorder_set.all():
                o._molecule_name = o._get_molecule_name()
                o.save(update_fields=["_molecule_name"])


@receiver(post_save, sender=Project)
def project_renamed(sender, instance, **kwargs):
    if getattr(instance, "_is_renaming", False):
        pass


@receiver(post_save, sender=Folder)
def folder_renamed(sender, instance, **kwargs):
    if getattr(instance, "_is_renaming", False):
        pass


@receiver(post_save, sender=Parameters)
def update_parameters_hash(sender, instance, **kwargs):
    if kwargs["created"]:
        hash = gen_params_md5(instance)
        instance._md5 = hash
    # Parameters are not really modified, but the case where they are updated could be handled
    # Changing just to _md5 field should not trigger anything
