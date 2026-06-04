# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^user/(?P<user_uuid>[0-9a-f-]+)/summary_by_chunk/(?P<chunk>[0-9]+)/?$', views.summary_by_chunk),
    re_path(r'^user/(?P<user_uuid>[0-9a-f-]+)/summary/?$', views.summary),
    re_path(r'^user/(?P<user_uuid>[0-9a-f-]+)/unlink/(?P<run_uuid>[0-9a-f-]+)/?$', views.unlink),
    re_path(r'^user/(?P<user_uuid>[0-9a-f-]+)/addtorun/(?P<run_uuid>[0-9a-f-]+)/?$', views.add_user_uuid),
]
