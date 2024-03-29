# Generated by Django 3.2.15 on 2022-10-02 20:39

import datetime
from django.conf import settings
import django.contrib.auth.models
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import frontend.models
import hashid_field.field


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="first name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="last name"
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        max_length=254, unique=True, verbose_name="email"
                    ),
                ),
                ("full_name", models.CharField(default="", max_length=256)),
                ("is_temporary", models.BooleanField(default=False)),
                ("default_gaussian", models.CharField(default="", max_length=1000)),
                ("default_orca", models.CharField(default="", max_length=1000)),
                ("code", models.CharField(max_length=16)),
                ("pref_units", models.PositiveIntegerField(default=0)),
                ("unseen_calculations", models.PositiveIntegerField(default=0)),
                ("allocated_seconds", models.PositiveIntegerField(default=0)),
                ("billed_seconds", models.PositiveIntegerField(default=0)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Group",
                        verbose_name="groups",
                    ),
                ),
            ],
            options={
                "verbose_name": "user",
                "verbose_name_plural": "users",
                "abstract": False,
            },
            managers=[
                ("objects", frontend.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="BasicStep",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        auto_created=True,
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("short_name", models.CharField(default="", max_length=100)),
                ("avail_xtb", models.BooleanField(default=False)),
                ("avail_Gaussian", models.BooleanField(default=False)),
                ("avail_ORCA", models.BooleanField(default=False)),
                ("creates_ensemble", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="Calculation",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("current_status", models.CharField(default="", max_length=400)),
                (
                    "date_submitted",
                    models.DateTimeField(blank=True, null=True, verbose_name="date"),
                ),
                (
                    "date_started",
                    models.DateTimeField(blank=True, null=True, verbose_name="date"),
                ),
                (
                    "date_finished",
                    models.DateTimeField(blank=True, null=True, verbose_name="date"),
                ),
                ("billed_seconds", models.PositiveIntegerField(default=0)),
                ("status", models.PositiveIntegerField(default=0)),
                (
                    "error_message",
                    models.CharField(blank=True, default="", max_length=400, null=True),
                ),
                (
                    "constraints",
                    models.CharField(blank=True, default="", max_length=400, null=True),
                ),
                (
                    "input_file",
                    models.CharField(
                        blank=True, default="", max_length=50000, null=True
                    ),
                ),
                (
                    "command",
                    models.CharField(blank=True, default="", max_length=500, null=True),
                ),
                ("local", models.BooleanField(default=True)),
                ("task_id", models.CharField(default="", max_length=100)),
                ("remote_id", models.PositiveIntegerField(default=0)),
                ("output_files", models.TextField(default="")),
            ],
        ),
        migrations.CreateModel(
            name="Ensemble",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(default="Nameless ensemble", max_length=100)),
                ("flagged", models.BooleanField(default=False)),
                ("hidden", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="Example",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        auto_created=True,
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=100)),
                ("page_path", models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name="Folder",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("depth", models.PositiveIntegerField(default=0)),
                (
                    "parent_folder",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="frontend.folder",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Parameters",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(default="Nameless parameters", max_length=100),
                ),
                ("charge", models.IntegerField()),
                ("multiplicity", models.IntegerField()),
                ("solvent", models.CharField(default="vacuum", max_length=100)),
                ("solvation_model", models.CharField(default="", max_length=100)),
                ("solvation_radii", models.CharField(default="", max_length=100)),
                ("software", models.CharField(default="xtb", max_length=100)),
                ("basis_set", models.CharField(default="min", max_length=100)),
                ("theory_level", models.CharField(default="", max_length=100)),
                ("method", models.CharField(default="GFN2-xTB", max_length=100)),
                ("specifications", models.CharField(default="", max_length=1000)),
                ("density_fitting", models.CharField(default="", max_length=1000)),
                ("custom_basis_sets", models.CharField(default="", max_length=1000)),
                ("_md5", models.CharField(default="", max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name="Preset",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(default="My Preset", max_length=100)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "params",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="frontend.parameters",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Recipe",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        auto_created=True,
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=100)),
                ("page_path", models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name="Structure",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("xyz_structure", models.CharField(default="", max_length=5000000)),
                ("number", models.PositiveIntegerField(default=1)),
                ("degeneracy", models.PositiveIntegerField(default=1)),
                (
                    "parent_ensemble",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="frontend.ensemble",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ResourceAllocation",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("code", models.CharField(max_length=256)),
                ("allocation_seconds", models.PositiveIntegerField()),
                (
                    "redeemer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ResearchGroup",
            fields=[
                (
                    "group_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="auth.group",
                    ),
                ),
                (
                    "PI",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="PI_of",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            bases=("auth.group",),
            managers=[
                ("objects", django.contrib.auth.models.GroupManager()),
            ],
        ),
        migrations.CreateModel(
            name="Property",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("energy", models.FloatField(default=0)),
                ("free_energy", models.FloatField(default=0)),
                ("uvvis", models.TextField(default="")),
                ("nmr", models.TextField(default="")),
                ("mo", models.TextField(default="")),
                (
                    "freq_list",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.FloatField(), default=list, size=None
                    ),
                ),
                (
                    "freq_animations",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.TextField(), default=list, size=None
                    ),
                ),
                ("ir_spectrum", models.TextField(default="")),
                ("simple_nmr", models.CharField(default="", max_length=100000)),
                ("charges", models.CharField(default="", max_length=100000)),
                ("geom", models.BooleanField(default=False)),
                (
                    "parameters",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="frontend.parameters",
                    ),
                ),
                (
                    "parent_structure",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="properties",
                        to="frontend.structure",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("private", models.PositiveIntegerField(default=0)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "main_folder",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="defaultfolder_of",
                        to="frontend.folder",
                    ),
                ),
                (
                    "preset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="frontend.preset",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Molecule",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                (
                    "inchi",
                    models.CharField(
                        blank=True, default="", max_length=1000, null=True
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="frontend.project",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="folder",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="frontend.project",
            ),
        ),
        migrations.CreateModel(
            name="Filter",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("type", models.CharField(max_length=500)),
                ("value", models.CharField(max_length=500)),
                (
                    "parameters",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="frontend.parameters",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="ensemble",
            name="folder",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="frontend.folder",
            ),
        ),
        migrations.AddField(
            model_name="ensemble",
            name="origin",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="frontend.ensemble",
            ),
        ),
        migrations.AddField(
            model_name="ensemble",
            name="parent_molecule",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="frontend.molecule",
            ),
        ),
        migrations.CreateModel(
            name="ClusterAccess",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("cluster_address", models.CharField(blank=True, max_length=200)),
                ("cluster_username", models.CharField(blank=True, max_length=50)),
                ("pal", models.PositiveIntegerField(default=8)),
                ("memory", models.PositiveIntegerField(default=15000)),
                ("status", models.CharField(default="", max_length=500)),
                (
                    "last_connected",
                    models.DateTimeField(
                        default=datetime.datetime(2000, 1, 1, 1, 1), verbose_name="date"
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="clusteraccess_owner",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ClassGroup",
            fields=[
                (
                    "group_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="auth.group",
                    ),
                ),
                ("user_resource_threshold", models.PositiveIntegerField(default=300)),
                ("group_resource_threshold", models.PositiveIntegerField(default=0)),
                ("access_code", models.CharField(max_length=256)),
                (
                    "professor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="professor_of",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            bases=("auth.group",),
            managers=[
                ("objects", django.contrib.auth.models.GroupManager()),
            ],
        ),
        migrations.CreateModel(
            name="CalculationOrder",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("start_calc_frame", models.PositiveIntegerField(default=0)),
                (
                    "constraints",
                    models.CharField(blank=True, default="", max_length=400, null=True),
                ),
                (
                    "date",
                    models.DateTimeField(blank=True, null=True, verbose_name="date"),
                ),
                ("last_seen_status", models.PositiveIntegerField(default=0)),
                ("hidden", models.BooleanField(default=False)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "aux_structure",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="aux_of_order",
                        to="frontend.structure",
                    ),
                ),
                (
                    "ensemble",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="frontend.ensemble",
                    ),
                ),
                (
                    "filter",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="frontend.filter",
                    ),
                ),
                (
                    "parameters",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="frontend.parameters",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="frontend.project",
                    ),
                ),
                (
                    "resource",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="frontend.clusteraccess",
                    ),
                ),
                (
                    "resource_provider",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provider_of",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "result_ensemble",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="result_of",
                        to="frontend.ensemble",
                    ),
                ),
                (
                    "start_calc",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="frontend.calculation",
                    ),
                ),
                (
                    "step",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="frontend.basicstep",
                    ),
                ),
                (
                    "structure",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="frontend.structure",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CalculationFrame",
            fields=[
                (
                    "id",
                    hashid_field.field.BigHashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=13,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("xyz_structure", models.CharField(default="", max_length=5000000)),
                ("RMSD", models.FloatField(default=0)),
                ("converged", models.BooleanField(default=False)),
                ("energy", models.FloatField(default=0)),
                ("number", models.PositiveIntegerField(default=0)),
                (
                    "parent_calculation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="frontend.calculation",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="calculation",
            name="aux_structure",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="aux_of_calc",
                to="frontend.structure",
            ),
        ),
        migrations.AddField(
            model_name="calculation",
            name="order",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="frontend.calculationorder",
            ),
        ),
        migrations.AddField(
            model_name="calculation",
            name="parameters",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="frontend.parameters",
            ),
        ),
        migrations.AddField(
            model_name="calculation",
            name="result_ensemble",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="frontend.ensemble",
            ),
        ),
        migrations.AddField(
            model_name="calculation",
            name="step",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="frontend.basicstep",
            ),
        ),
        migrations.AddField(
            model_name="calculation",
            name="structure",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="frontend.structure",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="in_class",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="members",
                to="frontend.classgroup",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="member_of",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="members",
                to="frontend.researchgroup",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Specific permissions for this user.",
                related_name="user_set",
                related_query_name="user",
                to="auth.Permission",
                verbose_name="user permissions",
            ),
        ),
    ]
