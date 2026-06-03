# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from . import views
from reo import views as reoviews
from django.urls import re_path

urlpatterns = [
    re_path(r'^job/(?P<run_uuid>[0-9a-f-]+)/results/?$', views.results),
    re_path(r'^help/?$', views.help),
    re_path(r'^job/inputs/?$', views.inputs),
    re_path(r'^job/outputs/?$', views.outputs),
    re_path(r'^chp_defaults/?$', views.chp_defaults),
    re_path(r'^absorption_chiller_defaults/?$', views.absorption_chiller_defaults),
    re_path(r'^avert_emissions_profile/?$', views.avert_emissions_profile),
    re_path(r'^cambium_profile/?$', views.cambium_profile),
    re_path(r'^easiur_costs/?$', views.easiur_costs),
    re_path(r'^sector_defaults/?$', views.sector_defaults),
    re_path(r'^simulated_load/?$', views.simulated_load),
    re_path(r'^user/(?P<user_uuid>[0-9a-f-]+)/summary/?$', views.summary),
    re_path(r'^user/(?P<user_uuid>[0-9a-f-]+)/summary_by_chunk/(?P<chunk>[0-9]+)/?$', views.summary_by_chunk),
    re_path(r'^user/(?P<user_uuid>[0-9a-f-]+)/unlink/(?P<run_uuid>[0-9a-f-]+)/?$', views.unlink),
    re_path(r'^user/(?P<user_uuid>[0-9a-f-]+)/unlink_from_portfolio/(?P<portfolio_uuid>[0-9a-f-]+)/(?P<run_uuid>[0-9a-f-]+)/?$', views.unlink_from_portfolio),
    re_path(r'^ghp_efficiency_thermal_factors/?$', views.ghp_efficiency_thermal_factors),
    re_path(r'^peak_load_outage_times/?$', views.peak_load_outage_times),
    re_path(r'^invalid_urdb/?$', reoviews.invalid_urdb),
    re_path(r'^schedule_stats/?$', reoviews.schedule_stats),
    re_path(r'^get_existing_chiller_default_cop/?$', views.get_existing_chiller_default_cop),
    re_path(r'^job/generate_results_table/?$', views.generate_results_table),
    re_path(r'^get_ashp_defaults/?$', views.get_ashp_defaults),
    re_path(r'^pv_cost_defaults/?$', views.pv_cost_defaults),
    re_path(r'^electric_storage_cost_defaults/?$', views.electric_storage_cost_defaults),
    re_path(r'^summary_by_runuuids/?$', views.summary_by_runuuids),
    re_path(r'^link_run_to_portfolios/?$', views.link_run_uuids_to_portfolio_uuid),
    re_path(r'^get_load_metrics/?$', views.get_load_metrics),
    re_path(r'^job/get_timeseries_table/?$', views.get_timeseries_table)
]
