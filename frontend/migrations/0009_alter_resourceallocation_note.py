# Generated by Django 3.2.16 on 2022-12-05 00:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("frontend", "0008_resourceallocation_note"),
    ]

    operations = [
        migrations.AlterField(
            model_name="resourceallocation",
            name="note",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "Trial"),
                    (2, "New account"),
                    (3, "Tester"),
                    (4, "Purchase"),
                    (5, "Subscription"),
                    (99, "Manually issued allocation"),
                ],
                default=99,
            ),
        ),
    ]
