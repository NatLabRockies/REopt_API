# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import json
import copy
from celery import shared_task
from reo.api import Job
from reo.views import results
from celery.utils.log import get_task_logger
from futurecosts.models import cost_forecasts, FutureCostsJob
from reo.models import ScenarioModel  # used in exec
from tastypie.exceptions import ImmediateHttpResponse
log = get_task_logger(__name__)


@shared_task(ignore_result=True)
def setup_jobs(run_uuid):
    """
    POST 10 jobs to main API and connect them to the FutureCostsJob model
    :param run_uuid: UUID of scenario from current year with "optimal" status. Used as base for all inputs except
        the future costs of Wind, PV, and Storage
    :return: None
    """

    fcjob = FutureCostsJob.objects.get(run_uuid=run_uuid)

    # 1. Get results for original scenario
    base_results = results(None, run_uuid)
    d = json.loads(base_results.content)
    d = scrub_urls_from_dict(d)

    # 2 Create future inputs and post them
    for i, year in enumerate(range(fcjob.base_year+2, fcjob.base_year+22, 2)):
        new_post = fill_in_future_costs(d["inputs"], year=year)
        # TODO make post_job a task and have it retry_on_failure?
        resp = post_job(new_post)
        exec("fcjob.future_scenario{} = ScenarioModel.objects.get(run_uuid=resp['run_uuid'])".format(i+1))
        exec("fcjob.future_year{} = year".format(i+1))

    fcjob.status = "Optimizing..."
    fcjob.save(force_update=True)


def post_job(data: dict) -> dict:
    job = Job()
    try:
        job.obj_create(bundle=copy.deepcopy(data))
    except ImmediateHttpResponse as resp:
        resp = json.loads(resp.response.content.decode('utf-8'))
        if "run_uuid" in resp.keys():
            return resp
        else:
            log.warning("could not create job:", resp["messages"]["error"])
            return resp["messages"]
    # TODO handle problems from posting jobs
    return {}


def scrub_urls_from_dict(d: dict) -> dict:
    for k, v in d.items():
        if isinstance(v, dict):
            scrub_urls_from_dict(v)
        if isinstance(v, str):
            if "http://" in v or "https://" in v:
                d[k] = "url removed"
    return d


def fill_in_future_costs(d: dict, year: int) -> dict:
    d["Scenario"]["Site"]["Wind"]["installed_cost_us_dollars_per_kw"] = \
        cost_forecasts.wind(
            year,
            type="capital_cost_dollars_per_kw",
            size_class=d["Scenario"]["Site"]["Wind"].get("size_class") or "commercial"
        )
    d["Scenario"]["Site"]["Wind"]["om_cost_us_dollars_per_kw"] = \
        cost_forecasts.wind(
            year,
            type="fixed_om_dollars_per_kw_per_yr",
            size_class=d["Scenario"]["Site"]["Wind"].get("size_class") or "commercial"
        )
    d["Scenario"]["Site"]["PV"]["installed_cost_us_dollars_per_kw"] = \
        cost_forecasts.pv(year, type="capital_cost_dollars_per_kw")

    d["Scenario"]["Site"]["PV"]["om_cost_us_dollars_per_kw"] = \
        cost_forecasts.pv(year, type="fixed_om_dollars_per_kw_per_yr")

    d["Scenario"]["Site"]["Storage"]["installed_cost_us_dollars_per_kw"] = \
        cost_forecasts.storage(year, type="installed_cost_us_dollars_per_kw")

    d["Scenario"]["Site"]["Storage"]["installed_cost_us_dollars_per_kwh"] = \
        cost_forecasts.storage(year, type="installed_cost_us_dollars_per_kwh")
    return d
