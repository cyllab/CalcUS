# Generated by Django 3.2.16 on 2023-01-17 02:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("frontend", "0013_auto_20230116_2111"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="in_class2",
        ),
        migrations.RemoveField(
            model_name="user",
            name="member_of2",
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
        migrations.AlterField(
            model_name="classgroup",
            name="professor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="professor_of",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="researchgroup",
            name="PI",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="PI_of",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]