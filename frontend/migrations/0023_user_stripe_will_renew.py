# Generated by Django 3.2.19 on 2023-05-19 14:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("frontend", "0022_auto_20230517_1443"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="stripe_will_renew",
            field=models.BooleanField(default=True),
        ),
    ]
