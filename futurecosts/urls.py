# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from . import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^futurecosts/(?P<run_uuid>[0-9a-f-]+)/results/?$', views.results),
]
