# Generated by Django 4.2.20 on 2025-04-28 05:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0009_alter_property_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedback',
            name='status',
            field=models.CharField(choices=[('new', 'New'), ('read', 'Read')], default='new', max_length=10),
        ),
    ]
