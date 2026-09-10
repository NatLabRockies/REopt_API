# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import json
import sys
import uuid
import numpy as np
import requests
import traceback
import os

from celery import shared_task
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.db import models as dbmodels
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.bundle import Bundle
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.resources import ModelResource
from tastypie.serializers import Serializer
from tastypie.validation import Validation
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from reo.exceptions import SaveToDatabase, UnexpectedError, REoptFailedToStartError

from reo.models import ScenarioModel, FinancialModel
from reoptjl.models import APIMeta
from resilience_stats.models import ResilienceModel, ERPMeta, ERPOutageInputs, ERPGeneratorInputs, ERPPrimeGeneratorInputs, ERPPVInputs, ERPWindInputs, ERPElectricStorageInputs, ERPOutputs, get_erp_input_dict_from_run_uuid
from resilience_stats.validators import validate_run_uuid
from resilience_stats.views import run_outage_sim


class ERPJob(ModelResource):

    class Meta:
        resource_name = 'erp'
        allowed_methods = ['post']
        detail_allowed_methods = []
        authorization = ReadOnlyAuthorization()
        serializer = Serializer(formats=['json'])
        always_return_data = True
        validation = Validation()
        object_class = None
        
    def detail_uri_kwargs(self, bundle_or_obj):
        kwargs = {}

        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.id
        else:
            kwargs['pk'] = bundle_or_obj['id']

        return kwargs

    def get_object_list(self, request):
        return [request]

    def obj_get_list(self, bundle, **kwargs):
        return self.get_object_list(bundle.request)

    def obj_create(self, bundle, **kwargs):
        erp_run_uuid = str(uuid.uuid4())

        meta_dict = {
            "run_uuid": erp_run_uuid,
            "status": "Validating..."
        }

        def add_validation_err_msg_and_raise_400_response(d:dict, err_msg:str):
            d["status"] = "Validation Error. See messages for details."
            d["messages"] = {}
            d["messages"]["error"] = err_msg
            raise ImmediateHttpResponse(HttpResponse(json.dumps(meta_dict),
                                    content_type='application/json',
                                    status=400))

        try:
            if bundle.request.META.get('HTTP_X_API_USER_ID', False):
                if bundle.request.META.get('HTTP_X_API_USER_ID', '') == '6f09c972-8414-469b-b3e8-a78398874103':
                    meta_dict["job_type"] = 'REopt Web Tool'
                else:
                    meta_dict["job_type"] = 'developer.nlr.gov'
            else:
                meta_dict["job_type"] = 'Internal NLR'
            test_case = bundle.request.META.get('HTTP_USER_AGENT','')
            if test_case.startswith('check_http/'):
                meta_dict["job_type"] = 'Monitoring'

            reopt_run_uuid = bundle.data.get("reopt_run_uuid", None)
            meta_dict["reopt_run_uuid"] = reopt_run_uuid

            meta = ERPMeta.create(**meta_dict)
            meta.clean_fields()
            meta.save()

            # TODO: validate time series (prod factors)
            if reopt_run_uuid is None:
                if bundle.data.get("CHP", None) or bundle.data.get("PrimeGenerator", None):
                    add_validation_err_msg_and_raise_400_response(
                        meta_dict, 
                        "Running ERP with CHP or PrimeGenerator but no reopt_run_uuid is not yet supported."
                    )
                if bundle.data.get("PV",{}).get("size_kw", 0) > 0 and \
                    len(bundle.data.get("PV",{}).get("production_factor_series", [])) != 8760: #TODO: handle subhourly
                    add_validation_err_msg_and_raise_400_response(
                        meta_dict, 
                        "To include PV, you must provide PV production_factor_series or the reopt_run_uuid of an optimization that considered PV."
                    )
                if bundle.data.get("Wind",{}).get("size_kw", 0) > 0 and \
                    len(bundle.data.get("Wind",{}).get("production_factor_series", [])) != 8760: #TODO: handle subhourly
                    add_validation_err_msg_and_raise_400_response(
                        meta_dict, 
                        "To include Wind, you must provide Wind production_factor_series or the reopt_run_uuid of an optimization that considered Wind."
                    )
                if bundle.data.get("Outage",{}).get("max_outage_duration", None) is None:
                    add_validation_err_msg_and_raise_400_response(
                        meta_dict, 
                        "You must provide Outage max_outage_duration or the reopt_run_uuid of an optimization that considered an outage(s)."
                    )
                if not bundle.data.get("Outage",{}).get("critical_loads_kw", []):
                    add_validation_err_msg_and_raise_400_response(
                        meta_dict, 
                        "You must provide Outage critical_loads_kw or the reopt_run_uuid of an optimization."
                    )
            else:
                #TODO: put in helper function for more readable code
                try:
                    validate_run_uuid(reopt_run_uuid)
                except ValidationError as err:
                    add_validation_err_msg_and_raise_400_response(meta_dict, str(err.message))

                ### Get values from REopt run for inputs that user has not provided ###
                # Note: have to try/except for CHP, ElectricStorage, and Generator models 
                # because may not exist (not PV because just get empty list)

                ## Get Meta model, validating reopt run_uuid ##
                try:
                    reopt_run_meta = APIMeta.objects.select_related(
                        "ElectricLoadOutputs",
                    ).get(run_uuid=reopt_run_uuid)
                except dbmodels.ObjectDoesNotExist as e:
                    # Handle non-existent REopt runs
                    add_validation_err_msg_and_raise_400_response(
                        meta_dict, 
                        "Invalid run_uuid {}, REopt run does not exist.".format(reopt_run_uuid)
                    )
                
                #TODO: put all of this stuff below in a helper function, or in clean or save django methods?
                
                def update_user_dict_with_values_from_reopt(user_dict_key:str, reopt_dict:dict):
                    reopt_dict.update(bundle.data.get(user_dict_key, {}))
                    bundle.data[user_dict_key] = reopt_dict

                ## Outage ##
                if not hasattr(reopt_run_meta, 'ElectricLoadOutputs'):
                    # Handle incomplete REopt runs
                    add_validation_err_msg_and_raise_400_response(
                        meta_dict, 
                        "REopt optimization with run_uuid {} has not yet completed. Please try again later.".format(reopt_run_uuid)
                    )
                critical_loads_kw = reopt_run_meta.ElectricLoadOutputs.dict["critical_load_series_kw"]
                update_user_dict_with_values_from_reopt("Outage", {"critical_loads_kw": critical_loads_kw})
                if len(reopt_run_meta.ElectricUtilityInputs.dict["outage_durations"]) > 0:
                    update_user_dict_with_values_from_reopt("Outage", {
                        "max_outage_duration": max(reopt_run_meta.ElectricUtilityInputs.dict["outage_durations"])
                    })
                if bundle.data.get("Outage", {}).get("max_outage_duration",None) is None:
                    add_validation_err_msg_and_raise_400_response(
                        meta_dict, 
                        "You must provide Outage max_outage_duration or the reopt_run_uuid of an optimization where ElectricUtility outage_durations was provided."
                    )

                ## Generator ##
                try:
                    gen_out = reopt_run_meta.GeneratorOutputs.dict
                    if gen_out.get("size_kw", 0) > 0:
                        update_user_dict_with_values_from_reopt(
                            "Generator", 
                            {"size_kw": gen_out.get("size_kw", 0) / bundle.data.get("Generator", {}).get("num_generators", 1)}
                        )
                except AttributeError as e: 
                    pass
                if "Generator" in bundle.data:
                    if (bundle.data["Generator"].get("electric_efficiency_half_load", None) is None and 
                        bundle.data["Generator"].get("electric_efficiency_full_load", None) is not None):
                        bundle.data["Generator"]["electric_efficiency_half_load"] = bundle.data["Generator"]["electric_efficiency_full_load"]

                    try:
                        gen_in = reopt_run_meta.GeneratorInputs.dict
                        update_user_dict_with_values_from_reopt(
                            "Generator",
                            {
                                "fuel_avail_gal": gen_in["fuel_avail_gal"],
                                "electric_efficiency_half_load": gen_in["electric_efficiency_half_load"],
                                "electric_efficiency_full_load": gen_in["electric_efficiency_full_load"]
                            }
                        )
                    except AttributeError as e: 
                        pass

                ## CHP/PrimeGenerator ##
                chp_or_prime_out = None
                chp_or_prime_in = None
                try:
                    chp_or_prime_out = reopt_run_meta.CHPOutputs.dict
                    if chp_or_prime_out.get("size_kw", 0) > 0:
                        update_user_dict_with_values_from_reopt(
                            "PrimeGenerator",
                            {"size_kw": chp_or_prime_out.get("size_kw", 0) / bundle.data.get("PrimeGenerator", {}).get("num_generators", 1)}
                        )
                except AttributeError as e: 
                    pass
                if "PrimeGenerator" in bundle.data:
                    if (bundle.data["PrimeGenerator"].get("electric_efficiency_half_load", None) is None and 
                        bundle.data["PrimeGenerator"].get("electric_efficiency_full_load", None) is not None):
                        bundle.data["PrimeGenerator"]["electric_efficiency_half_load"] = bundle.data["PrimeGenerator"]["electric_efficiency_full_load"]

                    bundle.data.get("PrimeGenerator")
                    try:
                        chp_or_prime_in = reopt_run_meta.CHPInputs.dict
                        update_user_dict_with_values_from_reopt(
                            "PrimeGenerator",
                            { 
                                "is_chp": chp_or_prime_in["thermal_efficiency_full_load"] > 0,
                                "electric_efficiency_half_load": chp_or_prime_in["electric_efficiency_half_load"],
                                "electric_efficiency_full_load": chp_or_prime_in["electric_efficiency_full_load"],
                                "prime_mover": chp_or_prime_in["prime_mover"]
                            }
                        )
                    except AttributeError as e:
                        add_validation_err_msg_and_raise_400_response(
                            meta_dict, 
                            "Running ERP with PrimeGenerator but a reopt_run_uuid of an optimization that did not consider it (using CHP) is not yet supported."
                        )

                ## PV ##
                pvs = reopt_run_meta.PVOutputs.all()
                if len(pvs) == 0 and \
                        bundle.data.get("PV",{}).get("size_kw", 0) > 0 and \
                        len(bundle.data.get("PV",{}).get("production_factor_series", [])) == 0:
                    add_validation_err_msg_and_raise_400_response(
                        meta_dict, 
                        "To include PV, you must provide PV size_kw and production_factor_series or the reopt_run_uuid of an optimization that considered PV."
                    )
                reopt_pv_size_kw = 0
                pv_prod_series = np.zeros(len(critical_loads_kw))
                for pv in pvs:
                    pvd = pv.dict
                    reopt_pv_size_kw += pvd.get("size_kw")
                    pv_prod_series += pvd.get("size_kw") * np.array(pvd.get("production_factor_series"))
                if reopt_pv_size_kw > 0 or "PV" in bundle.data:
                    update_user_dict_with_values_from_reopt(
                        "PV",
                        {"size_kw": reopt_pv_size_kw}
                    )
                    if bundle.data["PV"].get("production_factor_series", None) is None: 
                        # List pvs cannot be empty otherwise would have errored above
                        if reopt_pv_size_kw > 0: # Use weighted avg of PV prod factors
                            bundle.data["PV"]["production_factor_series"] = (pv_prod_series/reopt_pv_size_kw).tolist()
                        else: # PV considered in optimization but optimal sizes all 0. Use prod factor of first PV.
                            bundle.data["PV"]["production_factor_series"] = pvs[0].dict.get("production_factor_series")
                      
                ## Wind ##
                try:
                    wind_out = reopt_run_meta.WindOutputs.dict
                    if wind_out.get("size_kw") > 0 or "Wind" in bundle.data:
                        update_user_dict_with_values_from_reopt(
                            "Wind", 
                            {
                                "size_kw": wind_out.get("size_kw"),
                                "production_factor_series": wind_out.get("production_factor_series")
                            }
                        )                      
                except AttributeError as e: 
                    if bundle.data.get("Wind",{}).get("size_kw", 0) > 0 and \
                        len(bundle.data.get("Wind",{}).get("production_factor_series", [])) == 0:
                        add_validation_err_msg_and_raise_400_response(
                            meta_dict, 
                            "To include Wind, you must provide Wind size_kw and production_factor_series or the reopt_run_uuid of an optimization that considered Wind."
                        )
       
                ## ElectricStorage ##
                stor_out = None
                try:
                    stor_out = reopt_run_meta.ElectricStorageOutputs.dict
                except AttributeError as e: 
                    pass
                try:
                    stor_in = reopt_run_meta.ElectricStorageInputs.dict
                    #TODO: don't add ElectricStorage key if stor_out is None
                    update_user_dict_with_values_from_reopt(
                        "ElectricStorage",
                        {
                            "charge_efficiency": stor_in["rectifier_efficiency_fraction"] * stor_in["internal_efficiency_fraction"]**0.5,
                            "discharge_efficiency": stor_in["inverter_efficiency_fraction"] * stor_in["internal_efficiency_fraction"]**0.5,
                            "size_kw": 0 if stor_out is None else stor_out.get("size_kw", 0),
                            "size_kwh": 0 if stor_out is None else stor_out.get("size_kwh", 0),
                            "starting_soc_series_fraction": [] if stor_out is None else stor_out.get("soc_series_fraction", []),
                        }
                    )
                except AttributeError as e: 
                    pass

            for model in (
                ERPOutageInputs,    
                ERPGeneratorInputs,
                ERPPrimeGeneratorInputs,
                ERPPVInputs,
                ERPWindInputs,
                ERPElectricStorageInputs
            ):
                try:
                    obj = model.create(meta=meta, **bundle.data[model.key])
                    obj.clean()
                    obj.clean_fields()
                    obj.save()
                except KeyError:
                    pass

            meta.status = 'Simulating...'
            meta.save(update_fields=['status'])
            run_erp_task.delay(erp_run_uuid)
        except ImmediateHttpResponse as e:
            raise e
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            meta_dict["status"] = "Internal Server Error. See messages for details."
            meta_dict["messages"] = {}
            meta_dict["messages"]["error"] = str(exc_value)
            raise ImmediateHttpResponse(HttpResponse(json.dumps(meta_dict),
                                        content_type='application/json',
                                        status=500))  # internal server error

        raise ImmediateHttpResponse(HttpResponse(json.dumps({'run_uuid': erp_run_uuid}),
                                    content_type='application/json', status=201))


class OutageSimJob(ModelResource):
    class Meta:
        resource_name = 'outagesimjob'
        allowed_methods = ['post']
        detail_allowed_methods = []
        authorization = ReadOnlyAuthorization()
        serializer = Serializer(formats=['json'])
        always_return_data = True
        validation = Validation()
        object_class = None

    def detail_uri_kwargs(self, bundle_or_obj):
        kwargs = {}

        if isinstance(bundle_or_obj, Bundle):
            # Primary key is set to be the run_uuid for 1 to1 matching
            # between scenario UUID and outage sim UUID
            kwargs['pk'] = bundle_or_obj.data["run_uuid"]  # bundle_or_obj.obj.id
        else:
            kwargs['pk'] = bundle_or_obj.get("id")

        return kwargs

    def get_object_list(self, request):
        return [request]

    def obj_get_list(self, bundle, **kwargs):
        return self.get_object_list(bundle.request)

    def obj_create(self, bundle, **kwargs):
        run_uuid = bundle.data.get("run_uuid")
        bau = bundle.data.get("bau", False)
        # Handle invalid uuids
        try:
            validate_run_uuid(run_uuid)
        except ValidationError as err:
            raise ImmediateHttpResponse(HttpResponse(json.dumps({"Error": str(err.message)}), status=400))

        # Handle non-existent scenario runs
        try:
            scenario = ScenarioModel.objects.get(run_uuid=run_uuid)
        except ScenarioModel.DoesNotExist:
            msg = "Scenario {} does not exist!.".format(run_uuid)
            raise ImmediateHttpResponse(HttpResponse(json.dumps({"Error": msg}), content_type='application/json', status=404))

        if scenario.status == "Optimizing...":
            raise ImmediateHttpResponse(HttpResponse(json.dumps({"Error": "The scenario is still optimizing. Please try again later."}),
                                content_type='application/json', status=500))
        elif "error" in scenario.status.lower():
            raise ImmediateHttpResponse(HttpResponse(json.dumps(
                {"Error": "An error occurred in the scenario. Please check the messages from your results."}),
                content_type='application/json', status=500))

        if ResilienceModel.objects.filter(scenariomodel=scenario).count() > 0:
            err_msg = ("An outage simulation job has already been created for this run_uuid."
                "Please retrieve the results with a GET request to v1/outagesimjob/<run_uuid>/results."
                " Note: Even if not specified when the job was created, business-as-usual (BAU) can be retrieved"
                " from the results endpoint by specifying bau=true in the URL parameters.")

            raise ImmediateHttpResponse(HttpResponse(
                json.dumps({"Warning": err_msg}),
                content_type='application/json',
                status=208))
        else:  # This is the first POST for this run_uuid, kick-off outage sim run
            try:
                rm = ResilienceModel.create(scenariomodel=scenario)
            except SaveToDatabase as e:
                raise ImmediateHttpResponse(
                HttpResponse(json.dumps({"Error": e.message}), content_type='application/json', status=500))
            run_outage_sim_task.delay(rm.scenariomodel_id, run_uuid, bau)
            bundle.data = {"run_uuid": run_uuid, "bau": bau, "Success": True, "Status": 201}

        return bundle

@shared_task
def run_erp_task(run_uuid):
    name = 'run_erp_task'
    data = get_erp_input_dict_from_run_uuid(run_uuid)

    user_uuid = data.get('user_uuid')
    data.pop('user_uuid',None) # Remove user uuid from inputs dict to avoid downstream errors

    logger.info("Running ERP tool ...")
    try:
        julia_host = os.environ.get('JULIA_HOST', "julia")
        response = requests.post("http://" + julia_host + ":8081/erp/", json=data)
        response_json = response.json()
        if response.status_code == 500:
            raise REoptFailedToStartError(task=name, message=response_json["error"], run_uuid=run_uuid, user_uuid=user_uuid)
        logger.info("ERP run successful.")
        process_erp_results(response_json, run_uuid)
        logger.info("ERP results processing successful.")
        
    except Exception as e:
        if isinstance(e, REoptFailedToStartError):
            raise e

        if isinstance(e, requests.exceptions.ConnectionError):  # Julia server down
            raise REoptFailedToStartError(task=name, message="Julia server is down.", run_uuid=run_uuid, user_uuid=user_uuid)

        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error("ERP raised an unexpected error: UUID: " + str(run_uuid))
        raise UnexpectedError(exc_type, exc_value, traceback.format_tb(exc_traceback), task=name, run_uuid=run_uuid,
                              user_uuid=user_uuid)
    
    return True

def process_erp_results(results: dict, run_uuid: str) -> None:
    """
    Saves ERP results returned from the Julia API in the backend database.
    Called in resilience_stats/run_erp_task (a celery task)
    """
    #TODO: get success or error status from julia
    meta = ERPMeta.objects.get(run_uuid=run_uuid)
    meta.status = 'Completed' #results.get("status")
    meta.reopt_version = results.pop("reopt_version")
    meta.save(update_fields=['status','reopt_version'])
    ERPOutputs.create(meta=meta, **results).save()
    

@shared_task
def run_outage_sim_task(scenariomodel_id, run_uuid, bau):

    results = run_outage_sim(run_uuid, with_tech=True, bau=bau)

    try:
        ResilienceModel.objects.filter(scenariomodel_id=scenariomodel_id).update(**results)
        results = {'avoided_outage_costs_us_dollars': results['avoided_outage_costs_us_dollars']}
        FinancialModel.objects.filter(run_uuid=run_uuid).update(**results)        
    except SaveToDatabase as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err = SaveToDatabase(exc_type, exc_value.args[0], exc_traceback, task='resilience_model', run_uuid=run_uuid)
        err.save_to_db()
