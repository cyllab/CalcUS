# Generated by Django 3.2.19 on 2023-07-09 18:13

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("frontend", "0033_basicstep_prop_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="calc_method_suggestions",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="user",
            name="calc_type_property",
            field=models.BooleanField(default=True),
        ),
    ]
