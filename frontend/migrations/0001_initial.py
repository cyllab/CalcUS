# Generated by Django 3.0.3 on 2020-04-10 16:59

from django.conf import settings
import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0011_update_proxy_permissions'),
    ]

    operations = [
        migrations.CreateModel(
            name='BasicStep',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('desc', models.CharField(default='', max_length=500)),
                ('error_message', models.CharField(default='', max_length=500)),
                ('avail_xtb', models.BooleanField(default=False)),
                ('avail_Gaussian', models.BooleanField(default=False)),
                ('avail_orca', models.BooleanField(default=False)),
                ('creates_ensemble', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Ensemble',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Nameless ensemble', max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Example',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('page_path', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Parameters',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Nameless parameters', max_length=100)),
                ('charge', models.IntegerField()),
                ('multiplicity', models.IntegerField()),
                ('solvent', models.CharField(default='vacuum', max_length=100)),
                ('solvation_model', models.CharField(default='gbsa', max_length=100)),
                ('program', models.CharField(default='xtb', max_length=100)),
                ('basis_set', models.CharField(default='min', max_length=100)),
                ('method', models.CharField(default='GFN2-xTB', max_length=100)),
                ('misc', models.CharField(default='', max_length=1000)),
            ],
        ),
        migrations.CreateModel(
            name='Procedure',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('has_nmr', models.BooleanField(default=False)),
                ('has_freq', models.BooleanField(default=False)),
                ('has_uvvis', models.BooleanField(default=False)),
                ('has_mo', models.BooleanField(default=False)),
                ('avail_xtb', models.BooleanField(default=False)),
                ('avail_Gaussian', models.BooleanField(default=False)),
                ('avail_orca', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('calculation_time_used', models.PositiveIntegerField(default=0)),
                ('is_PI', models.BooleanField(default=False)),
                ('code', models.CharField(max_length=16)),
            ],
        ),
        migrations.CreateModel(
            name='Structure',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mol_structure', models.CharField(default='', max_length=5000000)),
                ('xyz_structure', models.CharField(default='', max_length=5000000)),
                ('sdf_structure', models.CharField(default='', max_length=5000000)),
                ('number', models.PositiveIntegerField(default=0)),
                ('energy', models.FloatField(default=0)),
                ('free_energy', models.FloatField(default=0)),
                ('degeneracy', models.PositiveIntegerField(default=0)),
                ('parent_ensemble', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Ensemble')),
            ],
        ),
        migrations.CreateModel(
            name='Step',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('same_dir', models.BooleanField(default=False)),
                ('from_procedure', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='frontend.Procedure')),
                ('parameters', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Parameters')),
                ('parent_procedure', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='initial_steps', to='frontend.Procedure')),
                ('parent_step', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Step')),
                ('step_model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='frontend.BasicStep')),
            ],
        ),
        migrations.CreateModel(
            name='ResearchGroup',
            fields=[
                ('group_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='auth.Group')),
                ('PI', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='researchgroup_PI', to='frontend.Profile')),
            ],
            bases=('auth.group',),
            managers=[
                ('objects', django.contrib.auth.models.GroupManager()),
            ],
        ),
        migrations.CreateModel(
            name='Property',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('energy', models.FloatField(default=0)),
                ('free_energy', models.FloatField(default=0)),
                ('rel_energy', models.FloatField(default=0)),
                ('boltzmann_weight', models.FloatField(default=1.0)),
                ('homo_lumo_gap', models.FloatField(default=0)),
                ('uvvis', models.PositiveIntegerField(default=0)),
                ('nmr', models.PositiveIntegerField(default=0)),
                ('mo', models.PositiveIntegerField(default=0)),
                ('freq', models.PositiveIntegerField(default=0)),
                ('parameters', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Parameters')),
                ('parent_structure', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='properties', to='frontend.Structure')),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Profile')),
            ],
        ),
        migrations.AddField(
            model_name='profile',
            name='member_of',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='members', to='frontend.ResearchGroup'),
        ),
        migrations.AddField(
            model_name='profile',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='PIRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group_name', models.CharField(max_length=100)),
                ('date_issued', models.DateTimeField(verbose_name='date')),
                ('issuer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Profile')),
            ],
        ),
        migrations.CreateModel(
            name='Molecule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('inchi', models.CharField(max_length=1000)),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Project')),
            ],
        ),
        migrations.AddField(
            model_name='ensemble',
            name='parent_molecule',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Molecule'),
        ),
        migrations.CreateModel(
            name='ClusterCommand',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('issuer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Profile')),
            ],
        ),
        migrations.CreateModel(
            name='ClusterAccess',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('private_key_path', models.CharField(max_length=100)),
                ('public_key_path', models.CharField(max_length=100)),
                ('cluster_address', models.CharField(blank=True, max_length=200)),
                ('cluster_username', models.CharField(blank=True, max_length=50)),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.ResearchGroup')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='clusteraccess_owner', to='frontend.Profile')),
            ],
        ),
        migrations.CreateModel(
            name='CalculationOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('constraints', models.CharField(blank=True, default='', max_length=400, null=True)),
                ('date', models.DateTimeField(blank=True, null=True, verbose_name='date')),
                ('date_finished', models.DateTimeField(blank=True, null=True, verbose_name='date')),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Profile')),
                ('ensemble', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Ensemble')),
                ('parameters', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Parameters')),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Project')),
                ('result_ensemble', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='result_of', to='frontend.Ensemble')),
                ('step', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.BasicStep')),
            ],
        ),
        migrations.CreateModel(
            name='Calculation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('error_message', models.CharField(default='', max_length=400)),
                ('current_status', models.CharField(default='', max_length=400)),
                ('date', models.DateTimeField(blank=True, null=True, verbose_name='date')),
                ('date_finished', models.DateTimeField(blank=True, null=True, verbose_name='date')),
                ('execution_time', models.PositiveIntegerField(default=0)),
                ('status', models.PositiveIntegerField(default=0)),
                ('unseen', models.BooleanField(default=True)),
                ('constraints', models.CharField(blank=True, default='', max_length=400, null=True)),
                ('has_scan', models.BooleanField(default=False)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='frontend.CalculationOrder')),
                ('parameters', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='frontend.Parameters')),
                ('result_ensemble', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Ensemble')),
                ('step', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='frontend.BasicStep')),
                ('structure', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='frontend.Structure')),
            ],
        ),
    ]
