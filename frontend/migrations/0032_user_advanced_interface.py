# Generated by Django 3.2.19 on 2023-07-03 18:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("frontend", "0031_auto_20230626_1410"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="advanced_interface",
            field=models.BooleanField(default=False),
        ),
    ]