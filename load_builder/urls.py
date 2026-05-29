# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^load_builder/?$', views.load_builder),
    re_path(r'^ensite/?$', views.ensite_view),
]