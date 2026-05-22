# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^job/(?P<run_uuid>[0-9a-f-]+)/resilience_stats/?$', views.resilience_stats),
    re_path(r'^outagesimjob/(?P<run_uuid>[0-9a-f-]+)/results/?$', views.resilience_stats),
    re_path(r'^outagesimjob/(?P<run_uuid>[0-9a-f-]+)/resilience_stats/?$', views.resilience_stats),
    re_path(r'^financial_check/?$', views.financial_check),
    re_path(r'^job/(?P<run_uuid>[0-9a-f-]+)/resilience_stats/financial_check/?$', views.financial_check),  # preserving old behavior
]
