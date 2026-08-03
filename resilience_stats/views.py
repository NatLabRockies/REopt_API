# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import sys
import uuid
from typing import Dict, Union
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpRequest
from django.db import models as dbmodels
from reo.exceptions import UnexpectedError
from reo.models import ModelManager
from reo.models import ScenarioModel, PVModel, StorageModel, LoadProfileModel, GeneratorModel, FinancialModel, \
    WindModel, CHPModel
from reo.utilities import annuity
from resilience_stats.models import ResilienceModel, ERPMeta, ERPOutageInputs, ERPGeneratorInputs, ERPPrimeGeneratorInputs, ERPPVInputs, ERPWindInputs, ERPElectricStorageInputs, ERPOutputs
from resilience_stats.outage_simulator_LF import simulate_outages
import numpy as np
from reo.utilities import empty_record
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def erp_results(request, run_uuid):
    try:
        uuid.UUID(run_uuid)  # raises ValueError if not valid uuid
    except ValueError as e:
        resp = {"messages": {}}
        resp['status'] = 'Error'
        if e.args[0] == "badly formed hexadecimal UUID string":
            resp['messages']['error'] = str(e.args[0])
            return JsonResponse(resp, status=400)
        else:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err = UnexpectedError(exc_type, exc_value.args[0], exc_traceback, task='resilience_stats',
                                  run_uuid=run_uuid)
            err.save_to_db()
            resp['messages']['error'] = str(err.message)
            return JsonResponse(resp, status=400)
    try:  # catch all unexpected exceptions
        # catch specific exceptions
        try:
            meta = ERPMeta.objects.select_related("ERPOutageInputs").get(run_uuid=run_uuid)
        except dbmodels.ObjectDoesNotExist as e:
            resp = {"messages": {}}
            resp['messages']['error'] = (
                "run_uuid {} not in database. "
                "If you have already submitted an ERP job, you may have "
                "hit the results endpoint too quickly after POST'ing, "
                "have a typo in your run_uuid, or the scenario was deleted. "
                "If you have not, please first submit an ERP job by sending a POST request to "
                "<version>/erp/. This will generate"
                " ERP results that you can access from a GET request to the "
                "<version>/erp/<run uuid>/results endpoint. ").format(run_uuid)
            resp['status'] = 'Error'
            return JsonResponse(resp, content_type='application/json', status=404)
        
        resp = meta.dict
        resp["inputs"] = dict()
        resp["inputs"][ERPOutageInputs.key] = meta.ERPOutageInputs.dict
        try:
            resp["inputs"][ERPGeneratorInputs.key] = meta.ERPGeneratorInputs.dict
        except AttributeError:
            pass
        try:
            resp["inputs"][ERPPrimeGeneratorInputs.key] = meta.ERPPrimeGeneratorInputs.dict
        except AttributeError:
            pass
        try:
            resp["inputs"][ERPPVInputs.key] = meta.ERPPVInputs.dict
        except AttributeError:
            pass
        try:
            resp["inputs"][ERPWindInputs.key] = meta.ERPWindInputs.dict
        except AttributeError:
            pass
        try:
            resp["inputs"][ERPElectricStorageInputs.key] = meta.ERPElectricStorageInputs.dict
        except AttributeError:
            pass
        resp["outputs"] = dict()
        resp["messages"] = dict()
        #TODO: save messages for ERP jobs and include here
        # try:
        #     msgs = meta.Message.all()
        #     for msg in msgs:
        #         r["messages"][msg.message_type] = msg.message
        # except: pass

        try:  
            erp_outputs = ERPOutputs.objects.get(meta__run_uuid=run_uuid)
        except dbmodels.ObjectDoesNotExist:
            resp['messages']['error'] = ('ERP results are not ready. Please try again later.')
            return JsonResponse(resp, content_type='application/json', status=404)

        else:  # ERPOutputs does exist
            resp["outputs"] = erp_outputs.dict

        response = JsonResponse(resp, content_type='application/json', status=200)
        return response

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err = UnexpectedError(exc_type, exc_value.args[0], exc_traceback, task='erp', run_uuid=run_uuid)
        err.save_to_db()
        resp = {"messages": {}}
        resp['messages']['error'] = err.message
        resp['status'] = 'Error'
        return JsonResponse(resp, status=500)

def get_erp_inputs_info():
    d = dict()
    d["reopt_run_uuid"] = ERPMeta.info_dict(ERPMeta)["reopt_run_uuid"]
    # do models need to be passed in as arg?
    d[ERPOutageInputs.key] = ERPOutageInputs.info_dict(ERPOutageInputs)
    d[ERPPVInputs.key] = ERPPVInputs.info_dict(ERPPVInputs)
    d[ERPWindInputs.key] = ERPWindInputs.info_dict(ERPWindInputs)
    d[ERPElectricStorageInputs.key] = ERPElectricStorageInputs.info_dict(ERPElectricStorageInputs)
    d[ERPGeneratorInputs.key] = ERPGeneratorInputs.info_dict(ERPGeneratorInputs)
    d[ERPPrimeGeneratorInputs.key] = ERPPrimeGeneratorInputs.info_dict(ERPPrimeGeneratorInputs)
    #TODO: add wind once implemented
    return JsonResponse(d)

def erp_help(request):
    """
    Served at host/erp/help
    :param request: 
    :return: JSON response with all erp inputs
    """
    try:
        resp = get_erp_inputs_info()
        return resp

    except Exception as e:
        return JsonResponse({"Error": "Unexpected error in ERP help endpoint: {}".format(e.args[0])}, status=500)

def erp_inputs(request):
    """
    Served at host/erp/inputs
    :param request: 
    :return: JSON response with all erp inputs
    """
    try:
        resp = get_erp_inputs_info()
        return resp

    except Exception as e:
        return JsonResponse({"Error": "Unexpected error in ERP inputs endpoint: {}".format(e.args[0])}, status=500)

def erp_outputs(request):
    """
    Served at host/erp/outputs
    :return: JSON response with all erp outputs
    """

    try:
        d = ERPOutputs.info_dict(ERPOutputs)
        return JsonResponse(d)

    except Exception as e:
        return JsonResponse({"Error": "Unexpected error in ERP outputs endpoint: {}".format(e.args[0])}, status=500)

def erp_chp_prime_gen_defaults(request):
    prime_mover = str(request.GET.get('prime_mover'))
    is_chp = bool(request.GET.get('is_chp'))
    size_kw = float(request.GET.get('size_kw'))
    try:
        d = ERPPrimeGeneratorInputs.info_dict_with_dependent_defaults(ERPPrimeGeneratorInputs, prime_mover, is_chp, size_kw)
        return JsonResponse(d)

    except TypeError as e:
        return JsonResponse({"Error": "Invalid or missing arguments: {}".format(e.args[0])}, status=400)

    except Exception as e:
        return JsonResponse({"Error": "Unexpected error in ERP chp_defaults endpoint: {}".format(e.args[0])}, status=500)

def resilience_stats(request: Union[Dict, HttpRequest], run_uuid=None):
    """
    Run outage simulator for given run_uuid
    :param request: optional parameter for 'bau', boolean
    :param run_uuid:
    :return: {"resilience_by_timestep",
              "resilience_hours_min",
              "resilience_hours_max",
              "resilience_hours_avg",
              "outage_durations",
              "probs_of_surviving",
             }
         Also can GET the same values as above with '_bau' appended if 'bau=true' for the site's existing capacities.
    """
    try:
        uuid.UUID(run_uuid)  # raises ValueError if not valid uuid
    except ValueError as e:
        if e.args[0] == "badly formed hexadecimal UUID string":
            return JsonResponse({"Error": str(e.args[0])}, status=400)
        else:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err = UnexpectedError(exc_type, exc_value.args[0], exc_traceback, task='resilience_stats',
                                  run_uuid=run_uuid)
            err.save_to_db()
            return JsonResponse({"Error": str(err.message)}, status=400)

    bau = False  # whether or not user wants outage simulator run with existing sizes
    if isinstance(request, HttpRequest):
        if request.GET.get('bau') in ["True", "true", "1"]:
            bau = True
    elif isinstance(request, dict):
        bau = request.get("bau")
    # Safety check; No exception is expected if called after POST-ing to /outagesimjob end point
    try:
        scenario = ScenarioModel.objects.get(run_uuid=run_uuid)
    except ScenarioModel.DoesNotExist:
        msg = "Scenario {} does not exist.".format(run_uuid)
        return JsonResponse({"Error": msg}, content_type='application/json', status=404)

    if scenario.status == "Optimizing...":
        return JsonResponse({"Error": "The scenario is still optimizing. Please try again later."},
                            content_type='application/json', status=404)
    elif "error" in scenario.status.lower():
        return JsonResponse(
            {"Error": "An error occurred in the scenario. Please check the messages from your results."},
            content_type='application/json', status=500)
    try:  # catch all exceptions
        try:  # catch specific exception
            not_ready_msg = ('Outage sim results are not ready. '
                'If you have already submitted an outagesimjob, please try again later. '
                'If not, please first submit an outagesimjob by sending a POST request to '
                '<version>/outagesimjob/ with run_uuid and bau parameters. This will generate'
                ' outage simulation results that you can access from a GET request to the '
                '<version>/job/<run uuid>/resilience_stats endpoint. ')
            not_ready_msg += 'Sample body data for POST-ing to /outagesimjob/: {"run_uuid\": \"6ea30f0f-3723-4fd1-8a3f-bebf8a3e4dbf\", \"bau\": false}' 
            rm = ResilienceModel.objects.get(scenariomodel=scenario)
            if rm.resilience_by_timestep is None:
                return JsonResponse({"Error": not_ready_msg}, content_type='application/json', status=404)
        except ResilienceModel.DoesNotExist:  # case for no resilience_stats generated yet
            return JsonResponse({"Error": not_ready_msg}, content_type='application/json', status=404)

        else:  # ResilienceModel does exist
            results = model_to_dict(rm)
            # remove items that user does not need
            del results['scenariomodel']
            del results['id']

            if bau and results[
                "probs_of_surviving_bau"] is None:  # then need to run outage_sim with existing sizes (BAU)
                bau_results = run_outage_sim(run_uuid, with_tech=False, bau=bau)
                ResilienceModel.objects.filter(id=rm.id).update(**bau_results)
                results.update(bau_results)

            if not bau:  # remove BAU results from results dict (if they're there)
                filtered_dict = {k: v for k, v in results.items() if "_bau" not in k}
                results = filtered_dict

        results.update({
            "help_text": ("The present_worth_factor and avg_critical_load are provided such"
                " that one can calculate an avoided outage cost in dollars by multiplying a value "
                "of load load ($/kWh) by the avg_critical_load, resilience_hours_avg, and present_worth_factor."
                " Note that if the outage event is 'major' (i.e. only occurs once), then the present_worth_factor is 1.")
        })
        response = JsonResponse({"outage_sim_results": results}, content_type='application/json', status=200)
        return response

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err = UnexpectedError(exc_type, exc_value.args[0], exc_traceback, task='resilience_stats', run_uuid=run_uuid)
        err.save_to_db()
        return JsonResponse({"Error": err.message}, status=500)


def financial_check(request, run_uuid=None):
    """ Check to see if resilience scenario system sizes are the same as financial scenario sizes """
    resilience_uuid = request.GET.get('resilience_uuid')
    if resilience_uuid is None:  # preserving old behavior
        resilience_uuid = run_uuid
    financial_uuid = request.GET.get('financial_uuid')

    def parse_system_sizes(site):
        size_dict = dict()
        if "Generator" in site:
            size_dict["Generator"] = site["Generator"]["size_kw"]
        if "Storage" in site:
            size_dict["Storage_kw"] = site["Storage"]["size_kw"]
            size_dict["Storage_kwh"] = site["Storage"]["size_kwh"]
        if "Wind" in site:
            size_dict["Wind"] = site["Wind"]["size_kw"]
        if "PV" in site:
            size_dict["PV"] = site["PV"]["size_kw"]
        return size_dict

    # validate uuid's
    try:
        uuid.UUID(str(resilience_uuid))  # raises ValueError if not valid uuid
        uuid.UUID(str(financial_uuid))  # raises ValueError if not valid uuid
    except ValueError as e:
        if e.args[0] == "badly formed hexadecimal UUID string":
            return JsonResponse({"Error": str(e.args[0])}, status=400)
        else:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err = UnexpectedError(exc_type, exc_value.args[0], exc_traceback, task='resilience_stats',
                                  run_uuid=resilience_uuid)
            err.save_to_db()
            return JsonResponse({"Error": str(err.message)}, status=400)

    try:
        resil_scenario = ScenarioModel.objects.get(run_uuid=resilience_uuid)
    except ScenarioModel.DoesNotExist:
        msg = "Scenario {} does not exist.".format(resilience_uuid)
        return JsonResponse({"Error": msg}, content_type='application/json', status=404)
    if resil_scenario.status == "Optimizing...":
        return JsonResponse({"Error": "The resilience scenario is still optimizing. Please try again later."},
                            content_type='application/json', status=500)
    elif "error" in resil_scenario.status.lower():
        return JsonResponse(
            {"Error": "An error occurred in the resilience scenario. Please check the messages from your results."},
            content_type='application/json', status=500)

    try:
        financial_scenario = ScenarioModel.objects.get(run_uuid=financial_uuid)
    except ScenarioModel.DoesNotExist:
        msg = "Scenario {} does not exist.".format(financial_uuid)
        return JsonResponse({"Error": msg}, content_type='application/json', status=404)
    if financial_scenario.status == "Optimizing...":
        return JsonResponse({"Error": "The financial scenario is still optimizing. Please try again later."},
                            content_type='application/json', status=500)
    elif "error" in financial_scenario.status.lower():
        return JsonResponse(
            {"Error": "An error occurred in the financial scenario. Please check the messages from your results."},
            content_type='application/json', status=500)
    try:
        # retrieve sizes from db
        resilience_result = ModelManager.make_response(resilience_uuid)
        financial_result = ModelManager.make_response(financial_uuid)
        resilience_sizes = parse_system_sizes(resilience_result["outputs"]["Scenario"]["Site"])
        financial_sizes = parse_system_sizes(financial_result["outputs"]["Scenario"]["Site"])

        survives = True
        if resilience_sizes.keys() == financial_sizes.keys():
            for tech, resil_size in resilience_sizes.items():
                if float(resil_size - financial_sizes[tech]) / float(max(resil_size, 1)) > 1.0e-3:
                    survives = False
                    break
        else:
            survives = False
        response = JsonResponse({"survives_specified_outage": survives})

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err = UnexpectedError(exc_type, exc_value.args[0], exc_traceback, task='resilience_stats',
                              run_uuid=resilience_uuid)
        err.save_to_db()
        return JsonResponse({"Error": err.message}, status=500)

    else:
        return response


def run_outage_sim(run_uuid, with_tech=True, bau=False):
    load_profile = LoadProfileModel.objects.filter(run_uuid=run_uuid).first() or empty_record()
    gen = GeneratorModel.objects.filter(run_uuid=run_uuid).first() or empty_record()
    batt = StorageModel.objects.filter(run_uuid=run_uuid).first() or empty_record()
    pvs = PVModel.objects.filter(run_uuid=run_uuid)
    financial = FinancialModel.objects.filter(run_uuid=run_uuid).first() or empty_record()
    wind = WindModel.objects.filter(run_uuid=run_uuid).first() or empty_record()
    chp = CHPModel.objects.filter(run_uuid=run_uuid).first() or empty_record()

    batt_roundtrip_efficiency = batt.internal_efficiency_pct \
                                * batt.inverter_efficiency_pct \
                                * batt.rectifier_efficiency_pct
    results = dict()

    if with_tech:  # NOTE: with_tech case is run after each optimization in reo/results.py
        celery_eager = True
        """ nlaws 200229
        Set celery_eager = False to run each inner outage simulator loop in parallel. Timing tests with generator only
        indicate that celery task management does not improve speed due to the overhead required to manage the 8760 tasks.
        However, if the outage simulator does get more complicated (say with CHP) we should revisit using celery to run
        the inner loops in parallel.
        try:
            if load_profile['outage_end_time_step'] - load_profile['outage_start_time_step'] > 1000:
                celery_eager = False
        except KeyError:
            pass  # in case no outage has been defined
        """
        pv_kw_ac_hourly = np.zeros(len(pvs[0].year_one_power_production_series_kw))
        for pv in pvs:
            pv_kw_ac_hourly += np.array(pv.year_one_power_production_series_kw) 
        pv_kw_ac_hourly = list(pv_kw_ac_hourly) 
        
        tech_results = simulate_outages(
            batt_kwh=batt.size_kwh or 0,
            batt_kw=batt.size_kw or 0,
            pv_kw_ac_hourly=pv_kw_ac_hourly,
            wind_kw_ac_hourly=wind.year_one_power_production_series_kw,
            init_soc=batt.year_one_soc_series_pct,
            critical_loads_kw=load_profile.critical_load_series_kw,
            batt_roundtrip_efficiency=batt_roundtrip_efficiency,
            diesel_kw=gen.size_kw or 0,
            fuel_available=gen.fuel_avail_gal,
            b=gen.fuel_intercept_gal_per_hr,
            m=gen.fuel_slope_gal_per_kwh,
            celery_eager=celery_eager,
            chp_kw=chp.size_kw or 0,
        )
        results.update(tech_results)

    if bau:
        # only PV and diesel generator may have existing size
        pv_kw_ac_hourly = np.zeros(len(load_profile.critical_load_series_kw))
        for pv in pvs:
            if pv.existing_kw > 0:
                pv_kw_ac_hourly += np.array(pv.year_one_power_production_series_kw) * pv.existing_kw / pv.size_kw
        pv_kw_ac_hourly = list(pv_kw_ac_hourly) 
        
        bau_results = simulate_outages(
            batt_kwh=0,
            batt_kw=0,
            pv_kw_ac_hourly=pv_kw_ac_hourly,
            critical_loads_kw=load_profile.critical_load_series_kw,
            diesel_kw=gen.existing_kw or 0,
            fuel_available=gen.fuel_avail_gal,
            b=gen.fuel_intercept_gal_per_hr,
            m=gen.fuel_slope_gal_per_kwh,
            chp_kw=chp.size_kw or 0,
        )
        results.update({key + '_bau': val for key, val in bau_results.items()})

    avg_critical_load = round(sum(load_profile.critical_load_series_kw) /
                              len(load_profile.critical_load_series_kw), 5)

    if load_profile.outage_is_major_event:
        # assume that outage occurs only once in analysis period
        present_worth_factor = 1
    else:
        present_worth_factor = annuity(financial.analysis_years, financial.escalation_pct,
                                       financial.offtaker_discount_pct)
    
    if 'resilience_hours_avg' in results.keys():
        avoided_outage_costs_us_dollars = round( results['resilience_hours_avg'] * \
                                            financial.value_of_lost_load_us_dollars_per_kwh * \
                                            avg_critical_load * \
                                            present_worth_factor, 2)
        results.update({"avoided_outage_costs_us_dollars": avoided_outage_costs_us_dollars})
    results.update({"present_worth_factor": present_worth_factor,
                    "avg_critical_load": avg_critical_load,
                    })
    return results
