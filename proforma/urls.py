# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from django.urls import re_path
from . import views

urlpatterns = [
	re_path(r'^job/(?P<run_uuid>[0-9a-f-]+)/proforma/?$', views.proforma)
]

