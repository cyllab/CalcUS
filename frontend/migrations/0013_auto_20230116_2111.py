# Generated by Django 3.2.16 on 2023-01-17 02:11

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("frontend", "0012_auto_20230116_2110"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ClassGroup2",
            new_name="ClassGroup",
        ),
        migrations.RenameModel(
            old_name="ResearchGroup2",
            new_name="ResearchGroup",
        ),
    ]
