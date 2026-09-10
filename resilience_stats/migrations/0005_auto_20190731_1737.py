# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('resilience_stats', '0004_auto_20190722_2231'),
    ]

    operations = [
        migrations.AddField(
            model_name='resiliencemodel',
            name='outage_durations_bau',
            field=django.contrib.postgres.fields.ArrayField(null=True, base_field=models.FloatField(null=True), size=None),
        ),
        migrations.AddField(
            model_name='resiliencemodel',
            name='probs_of_surviving_bau',
            field=django.contrib.postgres.fields.ArrayField(null=True, base_field=models.FloatField(null=True), size=None),
        ),
        migrations.AddField(
            model_name='resiliencemodel',
            name='probs_of_surviving_by_hour_of_the_day_bau',
            field=django.contrib.postgres.fields.ArrayField(null=True, base_field=django.contrib.postgres.fields.ArrayField(null=True, base_field=models.FloatField(null=True), size=None), size=None),
        ),
        migrations.AddField(
            model_name='resiliencemodel',
            name='probs_of_surviving_by_month_bau',
            field=django.contrib.postgres.fields.ArrayField(null=True, base_field=django.contrib.postgres.fields.ArrayField(null=True, base_field=models.FloatField(null=True), size=None), size=None),
        ),
        migrations.AddField(
            model_name='resiliencemodel',
            name='resilience_by_timestep_bau',
            field=django.contrib.postgres.fields.ArrayField(null=True, base_field=models.FloatField(null=True), size=None),
        ),
        migrations.AddField(
            model_name='resiliencemodel',
            name='resilience_hours_avg_bau',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='resiliencemodel',
            name='resilience_hours_max_bau',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='resiliencemodel',
            name='resilience_hours_min_bau',
            field=models.FloatField(null=True),
        ),
    ]
