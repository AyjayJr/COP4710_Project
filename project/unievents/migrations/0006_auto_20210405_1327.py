# Generated by Django 3.1.7 on 2021-04-05 13:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('unievents', '0005_delete_member_of'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='rrule',
        ),
        migrations.AddField(
            model_name='event',
            name='byday',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('MO', 'Monday'), ('TU', 'Tuesday'), ('WE', 'Wednesday'), ('TH', 'Thursday'), ('FR', 'Friday'), ('SA', 'Saturday'), ('SU', 'Sunday')], db_column='byday', max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='freq',
            field=models.TextField(choices=[('DAILY', 'Daily'), ('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly'), ('YEARLY', 'Yearly')], db_column='freq', null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='privacy_level',
            field=models.IntegerField(blank=True, choices=[(1, 'Public'), (2, 'Universityprivate'), (3, 'Rsoprivate')], db_column='privacy_level'),
        ),
        migrations.AlterField(
            model_name='rso',
            name='admin',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admin_at', to=settings.AUTH_USER_MODEL),
        ),
    ]
