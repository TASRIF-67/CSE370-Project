# Generated by Django 4.2.20 on 2025-04-07 15:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0004_remove_transaction_commission_transaction_invoice_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interest',
            name='assigned_agent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leads', to=settings.AUTH_USER_MODEL),
        ),
    ]
