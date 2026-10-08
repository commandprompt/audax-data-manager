from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0032_clear_old_erd_layouts'),
    ]

    operations = [
        migrations.AddField(
            model_name='connection',
            name='credentials_extra',
            field=models.JSONField(default=dict),
        ),
    ]
