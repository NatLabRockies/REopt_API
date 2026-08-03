# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('reo', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResilienceModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('resilience_by_timestep', django.contrib.postgres.fields.ArrayField(null=True, base_field=models.FloatField(null=True), size=None)),
                ('resilience_hours_min', models.FloatField(null=True)),
                ('resilience_hours_max', models.FloatField(null=True)),
                ('resilience_hours_avg', models.FloatField(null=True)),
                ('outage_durations', django.contrib.postgres.fields.ArrayField(null=True, base_field=models.FloatField(null=True), size=None)),
                ('probs_of_surviving', django.contrib.postgres.fields.ArrayField(null=True, base_field=models.FloatField(null=True), size=None)),
                ('scenariomodel', models.OneToOneField(null=True, default=None, blank=True, to='reo.ScenarioModel', on_delete=models.CASCADE)),
            ],
        ),
    ]
