# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
# from django.contrib.auth.models import User
from django.db import models
from django.contrib.postgres.fields import *
from django.forms.models import model_to_dict
from picklefield.fields import PickledObjectField


class UserUnlinkedRuns(models.Model):
    run_uuid = models.UUIDField(unique=True)
    user_uuid = models.UUIDField(unique=False)

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        obj.save()
        return obj
