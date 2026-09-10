# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from reoptjl.models import FinancialOutputs, APIMeta, PVOutputs, ElectricStorageInputs, ElectricStorageOutputs,\
                        ElectricTariffOutputs, SiteOutputs, ElectricUtilityOutputs,\
                        GeneratorOutputs, ElectricLoadOutputs, WindInputs, WindOutputs, FinancialInputs,\
                        ElectricUtilityInputs, ExistingBoilerOutputs, CHPOutputs, CHPInputs, \
                        ExistingChillerOutputs, CoolingLoadOutputs, HeatingLoadOutputs,\
                        HotThermalStorageInputs, HotThermalStorageOutputs, ColdThermalStorageInputs, ColdThermalStorageOutputs, OutageOutputs,\
                        REoptjlMessageOutputs, AbsorptionChillerOutputs, BoilerOutputs, SteamTurbineInputs, \
                        SteamTurbineOutputs, GHPInputs, GHPOutputs, ExistingChillerInputs, \
                        ElectricHeaterOutputs, ASHPSpaceHeaterOutputs, ASHPWaterHeaterOutputs, \
                        SiteInputs, ASHPSpaceHeaterInputs, ASHPWaterHeaterInputs, CSTInputs, CSTOutputs, PVInputs, \
                        HighTempThermalStorageInputs, HighTempThermalStorageOutputs, ElectricTariffInputs
import numpy as np
import sys
import traceback as tb
import logging
log = logging.getLogger(__name__)

def process_results(results: dict, run_uuid: str) -> None:
    """
    Saves the results returned from the Julia API in the backend database.
    Called in reoptjl/run_jump_model (a celery task)
    """
    try:
        keys_to_skip = []
        pop_result_keys(results, keys_to_skip)

        meta = APIMeta.objects.get(run_uuid=run_uuid)
        meta.status = results.get("status")
        meta.save(update_fields=["status"])

        if "Messages" in results.keys():
            REoptjlMessageOutputs.create(meta=meta, **results["Messages"]).save()
        if results.get("status") != "error":
            FinancialOutputs.create(meta=meta, **results["Financial"]).save()
            ElectricTariffOutputs.create(meta=meta, **results["ElectricTariff"]).save()
            ElectricUtilityOutputs.create(meta=meta, **results["ElectricUtility"]).save()
            ElectricLoadOutputs.create(meta=meta, **results["ElectricLoad"]).save()
            SiteOutputs.create(meta=meta, **results["Site"]).save()
            if "PV" in results.keys():
                if isinstance(results["PV"], dict):
                    PVOutputs.create(meta=meta, **results["PV"]).save()
                elif isinstance(results["PV"], list):
                    for pvdict in results["PV"]:
                        PVOutputs.create(meta=meta, **pvdict).save()
            if "ElectricStorage" in results.keys():
                ElectricStorageOutputs.create(meta=meta, **results["ElectricStorage"]).save()
            if "Generator" in results.keys():
                GeneratorOutputs.create(meta=meta, **results["Generator"]).save()
            if "Wind" in results.keys():
                WindOutputs.create(meta=meta, **results["Wind"]).save()
            if "Boiler" in results.keys():
                BoilerOutputs.create(meta=meta, **results["Boiler"]).save()
            if "ExistingBoiler" in results.keys():
                ExistingBoilerOutputs.create(meta=meta, **results["ExistingBoiler"]).save()
            if "ExistingChiller" in results.keys():
                ExistingChillerOutputs.create(meta=meta, **results["ExistingChiller"]).save()
            if "HotThermalStorage" in results.keys():
                HotThermalStorageOutputs.create(meta=meta, **results["HotThermalStorage"]).save()
            if "ColdThermalStorage" in results.keys():
                ColdThermalStorageOutputs.create(meta=meta, **results["ColdThermalStorage"]).save()
            if "HeatingLoad" in results.keys():
                HeatingLoadOutputs.create(meta=meta, **results["HeatingLoad"]).save()
            if "CoolingLoad" in results.keys():
                CoolingLoadOutputs.create(meta=meta, **results["CoolingLoad"]).save()
            if "CHP" in results.keys():
                CHPOutputs.create(meta=meta, **results["CHP"]).save()
            if "AbsorptionChiller" in results.keys():
                AbsorptionChillerOutputs.create(meta=meta, **results["AbsorptionChiller"]).save()
            if "Outages" in results.keys():
                for multi_dim_array_name in ["unserved_load_series_kw", "unserved_load_per_outage_kwh", 
                                            "storage_discharge_series_kw", "pv_to_storage_series_kw", 
                                            "pv_curtailed_series_kw", "pv_to_load_series_kw", 
                                            "wind_to_storage_series_kw", 
                                            "wind_curtailed_series_kw", "wind_to_load_series_kw", 
                                            "generator_to_storage_series_kw", "generator_curtailed_series_kw", 
                                            "generator_to_load_series_kw", "generator_fuel_used_per_outage_gal",
                                            "chp_to_storage_series_kw", "chp_curtailed_series_kw", 
                                            "chp_to_load_series_kw", "chp_fuel_used_per_outage_mmbtu",
                                            "critical_loads_per_outage_series_kw", "soc_series_fraction"]:
                    if multi_dim_array_name in results["Outages"]:
                        results["Outages"][multi_dim_array_name] = np.transpose(results["Outages"][multi_dim_array_name]).tolist()
                OutageOutputs.create(meta=meta, **results["Outages"]).save()
            if "SteamTurbine" in results.keys():
                SteamTurbineOutputs.create(meta=meta, **results["SteamTurbine"]).save()
            if "GHP" in results.keys():
                for pop_key in ["solve_time_min", "number_of_boreholes_nonhybrid", 
                                "number_of_boreholes_auto_guess", "number_of_boreholes_flipped_guess",
                                "iterations_nonhybrid", "iterations_auto_guess", "iterations_flipped_guess"]:
                    results["GHP"].pop(pop_key, None)
                GHPOutputs.create(meta=meta, **results["GHP"]).save() 
            if "ElectricHeater" in results.keys():
                ElectricHeaterOutputs.create(meta=meta, **results["ElectricHeater"]).save()
            if "ASHPSpaceHeater" in results.keys():
                ASHPSpaceHeaterOutputs.create(meta=meta, **results["ASHPSpaceHeater"]).save()
            if "ASHPWaterHeater" in results.keys():
                ASHPWaterHeaterOutputs.create(meta=meta, **results["ASHPWaterHeater"]).save()
            if "CST" in results.keys():
                CSTOutputs.create(meta=meta, **results["CST"]).save()
            if "HighTempThermalStorage" in results.keys():
                HighTempThermalStorageOutputs.create(meta=meta, **results["HighTempThermalStorage"]).save()               
            # TODO process rest of results
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        debug_msg = "exc_type: {}; exc_value: {}; exc_traceback: {}".format(
                                                                        exc_type, 
                                                                        exc_value.args[0] if exc_value.args else str(exc_value),
                                                                        tb.format_tb(exc_traceback)
                                                                    )
        log.error(debug_msg)
        raise e

def pop_result_keys(r:dict, keys_to_skip:list):
    for k in r.keys():
        if (type(r[k])) == dict:
            for s in keys_to_skip:
                r[k].pop(s, None)
        else:
            pass

def update_inputs_in_database(inputs_to_update: dict, run_uuid: str) -> None:
    """
    Updates inputs in the backend database with values returned from Julia.
    This is needed for inputs that have defaults calculated in the REopt Julia package, 
    which currently is those that use EASIUR or AVERT data.
    Called in reoptjl/run_jump_model (a celery task)
    """

    try:
        # get input models that need updating
        FinancialInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["Financial"])
        ElectricUtilityInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["ElectricUtility"])
        
        if inputs_to_update["Site"]:
            SiteInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["Site"])

        if inputs_to_update["CHP"]:  # Will be an empty dictionary if CHP is not considered
            if inputs_to_update["CHP"].get("installed_cost_per_kw") and type(inputs_to_update["CHP"].get("installed_cost_per_kw")) == float:
                inputs_to_update["CHP"]["installed_cost_per_kw"] = [inputs_to_update["CHP"]["installed_cost_per_kw"]]
            CHPInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["CHP"])
        if inputs_to_update["SteamTurbine"]:  # Will be an empty dictionary if SteamTurbine is not considered
            SteamTurbineInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["SteamTurbine"])
        if inputs_to_update["GHP"]:
            GHPInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["GHP"])
        if inputs_to_update["ExistingChiller"]:
            if not ExistingChillerInputs.objects.filter(meta__run_uuid=run_uuid):
                meta = APIMeta.objects.get(run_uuid=run_uuid)
                ExistingChillerInputs.create(meta=meta, **inputs_to_update["ExistingChiller"]).save()
            else:
                ExistingChillerInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["ExistingChiller"])
        if inputs_to_update["ASHPSpaceHeater"]:
            prune_update_fields(ASHPSpaceHeaterInputs, inputs_to_update["ASHPSpaceHeater"])
            ASHPSpaceHeaterInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["ASHPSpaceHeater"])
        if inputs_to_update["ASHPWaterHeater"]:
            prune_update_fields(ASHPWaterHeaterInputs, inputs_to_update["ASHPWaterHeater"])
            ASHPWaterHeaterInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["ASHPWaterHeater"])
        if inputs_to_update["PV"]:
            prune_update_fields(PVInputs, inputs_to_update["PV"])
            PVInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["PV"])  
        if inputs_to_update["Wind"]:
            prune_update_fields(WindInputs, inputs_to_update["Wind"])
            WindInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["Wind"])  
        if inputs_to_update["ElectricStorage"]:
            prune_update_fields(ElectricStorageInputs, inputs_to_update["ElectricStorage"])
            ElectricStorageInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["ElectricStorage"])  
        if inputs_to_update["ColdThermalStorage"]:
            prune_update_fields(ColdThermalStorageInputs, inputs_to_update["ColdThermalStorage"])
            ColdThermalStorageInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["ColdThermalStorage"])  
        if inputs_to_update["HotThermalStorage"]:
            prune_update_fields(HotThermalStorageInputs, inputs_to_update["HotThermalStorage"])
            HotThermalStorageInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["HotThermalStorage"])  
        if inputs_to_update["HighTempThermalStorage"]:
            prune_update_fields(HighTempThermalStorageInputs, inputs_to_update["HighTempThermalStorage"])
            HighTempThermalStorageInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["HighTempThermalStorage"])  
        # TODO CST is not added to this inputs_with_defaults_set_in_julia dictionary in http.jl, IF we need to update any CST inputs
        if inputs_to_update.get("CST") is not None:
            prune_update_fields(CSTInputs, inputs_to_update["CST"])
            CSTInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["CST"])
        if inputs_to_update.get("HighTempThermalStorage") is not None:
            prune_update_fields(HighTempThermalStorageInputs, inputs_to_update["HighTempThermalStorage"])
            HighTempThermalStorageInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["HighTempThermalStorage"])
        if inputs_to_update.get("ElectricTariff"):
            prune_update_fields(ElectricTariffInputs, inputs_to_update["ElectricTariff"])
            ElectricTariffInputs.objects.filter(meta__run_uuid=run_uuid).update(**inputs_to_update["ElectricTariff"])            
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        debug_msg = "exc_type: {}; exc_value: {}; exc_traceback: {}".format(
                                                                        exc_type, 
                                                                        exc_value.args[0] if exc_value.args else str(exc_value),
                                                                        tb.format_tb(exc_traceback)
                                                                    )
        log.error(debug_msg)
        return

def prune_update_fields(model_obj, dict_to_update):
    """
    REopt.jl may return more fields than the API has to update, so prune those extra ones before updating the model/db object
    """
    field_names = [field.name for field in model_obj._meta.get_fields()]
    dict_to_update_keys = list(dict_to_update.keys())
    for key in dict_to_update_keys:
        if key not in field_names:
            del dict_to_update[key]