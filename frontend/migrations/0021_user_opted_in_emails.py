# Generated by Django 3.2.19 on 2023-05-15 16:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("frontend", "0020_subscription_stripe_sub_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="opted_in_emails",
            field=models.BooleanField(default=False),
        ),
    ]