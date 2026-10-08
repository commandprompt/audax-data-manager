from django.db import migrations


def populate_technologies(apps, schema_editor):
    Technology = apps.get_model('app', 'Technology')
    Technology.objects.get_or_create(name='rdspostgresql')


def remove_technologies(apps, schema_editor):
    Technology = apps.get_model('app', 'Technology')
    Technology.objects.filter(name='rdspostgresql').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0033_connection_credentials_extra'),
    ]

    operations = [
        migrations.RunPython(populate_technologies, remove_technologies)
    ]
