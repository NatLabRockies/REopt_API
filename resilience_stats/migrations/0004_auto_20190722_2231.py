# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('resilience_stats', '0003_auto_20190715_1626'),
    ]

    operations = [
        migrations.AddField(
            model_name='resiliencemodel',
            name='survives_specified_outage',
            field=models.NullBooleanField(),
        ),
        migrations.AlterField(
            model_name='resiliencemodel',
            name='probs_of_surviving_by_hour_of_the_day',
            field=django.contrib.postgres.fields.ArrayField(null=True, base_field=django.contrib.postgres.fields.ArrayField(null=True, base_field=models.FloatField(null=True), size=None), size=None),
        ),
        migrations.AlterField(
            model_name='resiliencemodel',
            name='probs_of_surviving_by_month',
            field=django.contrib.postgres.fields.ArrayField(null=True, base_field=django.contrib.postgres.fields.ArrayField(null=True, base_field=models.FloatField(null=True), size=None), size=None),
        ),
    ]
