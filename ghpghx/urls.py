# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from django.urls import re_path
from django.conf.urls.static import static
from django.conf import settings
from . import views

# TODO: finish ghpghx/views.py with /help

urlpatterns = [
    re_path(r'^ghpghx/errors/?$', views.errors),
    #re_path(r'^ghpghx/help/?$', views.help),
    re_path(r'^ghpghx/(?P<ghp_uuid>[0-9a-f-]+)/results/?$', views.results),
    re_path(r'^ghpghx/ground_conductivity/?$', views.ground_conductivity),    
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

