# Generated by Django 3.2.19 on 2023-05-17 19:43

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("frontend", "0021_user_opted_in_emails"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="subscription",
            name="duration",
        ),
        migrations.RemoveField(
            model_name="subscription",
            name="for_academia",
        ),
        migrations.AddField(
            model_name="user",
            name="stripe_cus_id",
            field=models.CharField(default="", max_length=256),
        ),
    ]
