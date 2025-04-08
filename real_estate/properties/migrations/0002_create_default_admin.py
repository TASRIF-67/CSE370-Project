from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_default_admin(apps, schema_editor):
    CustomUser = apps.get_model('properties', 'CustomUser')
    if not CustomUser.objects.filter(username='admin').exists():
        admin = CustomUser(
            username='admin',
            email='admin@example.com',
            password=make_password('admin'),
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        admin.save()

class Migration(migrations.Migration):
    dependencies = [('properties', '0001_initial')]
    operations = [migrations.RunPython(create_default_admin)]