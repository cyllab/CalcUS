# Generated by Django 3.2.19 on 2023-06-10 15:27

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("frontend", "0027_remove_basicstep_avail_nwchem"),
    ]

    operations = [
        migrations.AddField(
            model_name="basicstep",
            name="avail_NWChem",
            field=models.BooleanField(default=False),
        ),
    ]
