# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('reo', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProForma',
            fields=[
                ('scenariomodel', models.OneToOneField(primary_key=True, default=0, serialize=False, to='reo.ScenarioModel', blank=True, on_delete=models.CASCADE)),
                ('uuid', models.UUIDField(default=uuid.uuid4)),
                ('spreadsheet_created', models.DateTimeField(null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
