# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from django.urls import include, re_path, path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import HttpResponse
from reo.api import Job
from resilience_stats.api import OutageSimJob
from resilience_stats.api import ERPJob
from tastypie.api import Api
from reo import views
from reoptjl.api import Job as REoptJLJob
from futurecosts.api import FutureCostsAPI
from ghpghx.resources import GHPGHXJob
from reo.api import Job2

v1_api = Api(api_name='v1')
v1_api.register(Job())
v1_api.register(OutageSimJob())
v1_api.register(GHPGHXJob())

v2_api = Api(api_name='v2')
v2_api.register(Job2())
v2_api.register(OutageSimJob())
v2_api.register(GHPGHXJob())

v3_api = Api(api_name='v3')
v3_api.register(REoptJLJob())
v3_api.register(ERPJob())
v3_api.register(GHPGHXJob())

stable_api = Api(api_name='stable')
stable_api.register(REoptJLJob())
stable_api.register(ERPJob())
stable_api.register(GHPGHXJob())

dev_api = Api(api_name='dev')
dev_api.register(FutureCostsAPI())


def page_not_found(request, url):
    """
    If we could run with DEBUG = False, this custom 404 would not be necessary (see production_settings.py for more).
    This custom 404 is to avoid showing users too much information (i.e. traceback information) when they mistype a url.
    :param request:
    :param url:
    :return:
    """
    return HttpResponse("Invalid URL: {}".format(url), status=404)

# Note the order of the URLs matters for avoiding invalid GET method for v1_api endpoints
urlpatterns = [
    re_path(r'^_health/?$', views.health, name='health'),
    
    path('v1/', include('reo.urls')),
    path('v1/', include('resilience_stats.urls_v1_v2')),
    path('v1/', include('proforma.urls')),
    path('v1/', include('load_builder.urls')),
    path('v1/', include('summary.urls')),
    path('v1/', include('ghpghx.urls')),
    re_path(r'', include(v1_api.urls)),

    path('v2/', include('resilience_stats.urls_v1_v2')),
    path('v2/', include('reo.urls_v2')),
    path('v2/', include('proforma.urls')),
    path('v2/', include('load_builder.urls')),
    path('v2/', include('summary.urls')),
    path('v2/', include('ghpghx.urls')),
    re_path(r'', include(v2_api.urls)),

    path('v3/', include('reoptjl.urls')),
    path('v3/', include('resilience_stats.urls_v3plus')),
    path('v3/', include('ghpghx.urls')),
    path('v3/', include('load_builder.urls')),
    # TODO proforma for v3
    # (summary is within reoptjl.urls)
    re_path(r'', include(v3_api.urls)),

    path('stable/', include('reoptjl.urls')),
    path('stable/', include('resilience_stats.urls_v3plus')),
    path('stable/', include('ghpghx.urls')),
    path('stable/', include('load_builder.urls')),
    # TODO proforma for v3
    # (summary is within reoptjl.urls)
    re_path(r'', include(stable_api.urls)),

    path('dev/', include('futurecosts.urls')),
    re_path(r'', include(dev_api.urls)),

    re_path(r'(.*)', page_not_found, name='404'),
    ]

urlpatterns += staticfiles_urlpatterns()
