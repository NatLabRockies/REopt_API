# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^erp/(?P<run_uuid>[0-9a-f-]+)/results/?$', views.erp_results),
    re_path(r'^erp/help/?$', views.erp_help),
    re_path(r'^erp/inputs/?$', views.erp_inputs),
    re_path(r'^erp/outputs/?$', views.erp_outputs),
    re_path(r'^erp/chp_defaults/?$', views.erp_chp_prime_gen_defaults),
]
