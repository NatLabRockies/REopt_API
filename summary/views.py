# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import sys
from django.http import JsonResponse
from reo.models import ScenarioModel, SiteModel, LoadProfileModel, PVModel, StorageModel, \
    WindModel, GeneratorModel, FinancialModel, ElectricTariffModel, \
    MessageModel, AbsorptionChillerModel, ColdTESModel, HotTESModel, CHPModel, GHPModel, \
    SteamTurbineModel
from reo.exceptions import UnexpectedError
from reo.models import ModelManager
from resilience_stats.models import ResilienceModel
import uuid
from summary.models import UserUnlinkedRuns


def add_user_uuid(request, user_uuid, run_uuid):
    """
    update the user_uuid associated with a Scenario run_uuid
    """
    content = {'user_uuid': user_uuid, 'run_uuid': run_uuid}
    for name, check_id in content.items():
        try:
            uuid.UUID(check_id)  # raises ValueError if not valid uuid
        except ValueError as e:
            if e.args[0] == "badly formed hexadecimal UUID string":
                return JsonResponse({"Error": "{} {}".format(name, e.args[0]) }, status=400)
            else:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if name == 'user_uuid':
                    err = UnexpectedError(exc_type, exc_value, exc_traceback, task='unlink', user_uuid=check_id)
                if name == 'run_uuid':
                    err = UnexpectedError(exc_type, exc_value, exc_traceback, task='unlink', run_uuid=check_id)
                err.save_to_db()
                return JsonResponse({"Error": str(err.message)}, status=400)
    try:
        try:
            scenario = ScenarioModel.objects.filter(run_uuid=run_uuid).first()
            if scenario.user_uuid is None:
                ModelManager.add_user_uuid(user_uuid, run_uuid)
                response = JsonResponse(
                    {"Success": "user_uuid for run_uuid {} has been set to {}".format(run_uuid, user_uuid)})
                return response
            else:
                return JsonResponse({"Error": "a user_uuid already exists for run_uuid {}".format(run_uuid)})
        except:
            return JsonResponse({"Error": "run_uuid does not exist"})

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err = UnexpectedError(exc_type, exc_value, exc_traceback, task='add_user_uuid')
        err.save_to_db()
        return JsonResponse({"Error": err.message}, status=500)


def unlink(request, user_uuid, run_uuid):
    """
    add an entry to the UserUnlinkedRuns for the given user_uuid and run_uuid
    """
    content = {'user_uuid': user_uuid, 'run_uuid': run_uuid}
    for name, check_id in content.items():
        try:
            uuid.UUID(check_id)  # raises ValueError if not valid uuid
        except ValueError as e:
            if e.args[0] == "badly formed hexadecimal UUID string":
                return JsonResponse({"Error": "{} {}".format(name, e.args[0]) }, status=400)
            else:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if name == 'user_uuid':
                    err = UnexpectedError(exc_type, exc_value, exc_traceback, task='unlink', user_uuid=check_id)
                if name == 'run_uuid':
                    err = UnexpectedError(exc_type, exc_value, exc_traceback, task='unlink', run_uuid=check_id)
                err.save_to_db()
                return JsonResponse({"Error": str(err.message)}, status=400)

    try:
        if not ScenarioModel.objects.filter(user_uuid=user_uuid).exists():
            return JsonResponse({"Error": "User {} does not exist".format(user_uuid)}, status=400)

        if not ScenarioModel.objects.filter(run_uuid=run_uuid).exists():
            return JsonResponse({"Error": "Run {} does not exist".format(run_uuid)}, status=400)

        runs = ScenarioModel.objects.filter(run_uuid=run_uuid)
        if runs.exists():
            if runs[0].user_uuid != user_uuid:
                return JsonResponse({"Error": "Run {} is not associated with user {}".format(run_uuid, user_uuid)}, status=400)

        if not UserUnlinkedRuns.objects.filter(run_uuid=run_uuid).exists():
            UserUnlinkedRuns.create(**content)
            return JsonResponse({"Success": "user_uuid {} unlinked from run_uuid {}".format(user_uuid, run_uuid)},
                                status=201)
        else:
            return JsonResponse({"Nothing changed": "user_uuid {} is already unlinked from run_uuid {}".format(user_uuid, run_uuid)},
                                status=208)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err = UnexpectedError(exc_type, exc_value, exc_traceback, task='unlink', user_uuid=user_uuid)
        err.save_to_db()
        return JsonResponse({"Error": err.message}, status=404)




def get_user_summary_for_scenarios(scenarios, user_uuid, total_chunks=None, chunk=None):
    json_response = {"user_uuid": user_uuid, "scenarios": []}
    if total_chunks not in [None, 0]:
        json_response["total_chunks"] = total_chunks
    if chunk not in [None]:
        json_response["chunk"] = chunk

    scenario_run_uuids = [s.run_uuid for s in scenarios]
    scenario_run_ids = [s.id for s in scenarios]

    #saving time by only calling each table once
    messages = MessageModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','message_type','message')
    sites = SiteModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','address')
    loads = LoadProfileModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','outage_start_time_step',
                                                                                    'loads_kw','doe_reference_name')
    batts = StorageModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','max_kw','size_kw','size_kwh')
    pvs = PVModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','max_kw','size_kw')
    winds = WindModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','max_kw','size_kw')
    gens = GeneratorModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid', 'max_kw', 'size_kw')
    financials = FinancialModel.objects.filter(run_uuid__in=scenario_run_uuids).values(
                                                                        'run_uuid',
                                                                        'npv_us_dollars',
                                                                        'net_capital_costs',
                                                                        'lcc_us_dollars',
                                                                        'lcc_bau_us_dollars',
                                                                        'net_capital_costs_plus_om_us_dollars',
                                                                        'net_capital_costs',
                                                                        'net_om_us_dollars_bau')
    tariffs = ElectricTariffModel.objects.filter(run_uuid__in=scenario_run_uuids).values(
                                                                        'run_uuid',
                                                                        'urdb_rate_name',
                                                                        'year_one_energy_cost_us_dollars',
                                                                        'year_one_demand_cost_us_dollars',
                                                                        'year_one_fixed_cost_us_dollars',
                                                                        'year_one_min_charge_adder_us_dollars',
                                                                        'year_one_coincident_peak_cost_us_dollars',
                                                                        'year_one_bill_us_dollars',
                                                                        'year_one_energy_cost_bau_us_dollars',
                                                                        'year_one_demand_cost_bau_us_dollars',
                                                                        'year_one_fixed_cost_bau_us_dollars',
                                                                        'year_one_min_charge_adder_bau_us_dollars',
                                                                        'year_one_coincident_peak_cost_bau_us_dollars',
                                                                        'year_one_bill_bau_us_dollars')
    resiliences = ResilienceModel.objects.filter(scenariomodel_id__in=scenario_run_ids).values(
                                                                        'scenariomodel_id',
                                                                        'resilience_hours_avg',
                                                                        'resilience_hours_max',
                                                                        'resilience_hours_min')
    chps = CHPModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','max_kw','size_kw')
    hottess = HotTESModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','max_gal','size_gal')
    coldtess = ColdTESModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','max_gal','size_gal')
    absorpchls = AbsorptionChillerModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','max_ton','size_ton')
    ghps = GHPModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','building_sqft','size_heat_pump_ton', 'ghpghx_chosen_outputs')
    steamturbines = SteamTurbineModel.objects.filter(run_uuid__in=scenario_run_uuids).values('run_uuid','max_kw','size_kw')

    def get_scenario_data(data, run_uuid):
        if type(data)==dict:
            if str(data.get('run_uuid')) == str(run_uuid):
                return data
            if str(data.get('scenariomodel_id')) == str(run_uuid):
                return data
        result = [s for s in data if str(s.get('run_uuid')) == str(run_uuid)]
        if len(result) > 0:
            return result
        result = [s for s in data if str(s.get('scenariomodel_id')) == str(run_uuid)]
        if len(result) > 0:
            return result
        return [{}]

    for scenario in scenarios:
        results = dict({
            'focus': None,
            'address': None,
            'urdb_rate_name': None,
            'doe_reference_name': None,
            'npv_us_dollars': None,
            'net_capital_costs': None,
            'net_capital_costs_plus_om_us_dollars': None,
            'net_om_us_dollars_bau': None,
            'resilience_hours_min': None,
            'resilience_hours_max': None,
            'resilience_hours_avg': None,
            'year_one_savings_us_dollars': None,
            'pv_kw': 'not evaluated',
            'wind_kw': 'not evaluated',
            'gen_kw': 'not evaluated',
            'batt_kw': 'not evaluated',
            'batt_kwh': 'not evaluated',
            'chp_kw': 'not evaluated',
            'hottes_gal': 'not evaluated',
            'coldtes_gal': 'not evaluated',
            'absorpchl_ton': 'not evaluated',
            'ghp_ton': 'not evaluated',
            'ghp_n_bores': 'not evaluated',
            'steamturbine_kw': 'not evaluated'
        })
        results['status'] = scenario.status
        results['run_uuid'] = str(scenario.run_uuid)
        results['created'] = scenario.created
        results['description'] = scenario.description

        # Messages
        message_set = get_scenario_data(messages, scenario.run_uuid)
        if not type(message_set) == list:
            message_set = [message_set]
        results['messages'] = {}
        for message in message_set:
            if len(message.keys()) > 0:
                results['messages'][message.get('message_type') or "type"] = message.get('message') or ""

        try:
            site = get_scenario_data(sites, scenario.run_uuid)[0]
            load = get_scenario_data(loads, scenario.run_uuid)[0]
            batt = get_scenario_data(batts, scenario.run_uuid)[0]
            pv = get_scenario_data(pvs, scenario.run_uuid)[0]
            wind = get_scenario_data(winds, scenario.run_uuid)[0]
            gen = get_scenario_data(gens, scenario.run_uuid)[0]
            financial = get_scenario_data(financials, scenario.run_uuid)[0]
            tariff = get_scenario_data(tariffs, scenario.run_uuid)[0]
            resilience = get_scenario_data(resiliences, scenario.id)[0]
            chp = get_scenario_data(chps, scenario.run_uuid)[0]
            hottes = get_scenario_data(hottess, scenario.run_uuid)[0]
            coldtes = get_scenario_data(coldtess, scenario.run_uuid)[0]
            absorpchl = get_scenario_data(absorpchls, scenario.run_uuid)[0]
            ghp = get_scenario_data(ghps, scenario.run_uuid)[0]
            steamturbine = get_scenario_data(steamturbines, scenario.run_uuid)[0]

            if site:

                # Focus
                if load: 
                    if load.get('outage_start_time_step') is not None:
                        results['focus'] = "Resilience"
                    else:
                        results['focus'] = "Financial"
                    
                    if load.get('loads_kw') is not None:
                        results['doe_reference_name'] = "Custom"
                    else:
                        results['doe_reference_name'] = load.get('doe_reference_name')

                # Address
                results['address'] = site.get('address')

                # Description
                results['description'] = scenario.description

                # Address
                results['address'] = site.get('address')

                # Utility Tariff
                if tariff.get('urdb_rate_name') is not None:
                    results['urdb_rate_name'] = tariff.get('urdb_rate_name')
                else:
                    results['urdb_rate_name'] = "Custom"

                # NPV
                results['npv_us_dollars'] = financial.get('npv_us_dollars')

                # DG System Cost
                results['net_capital_costs'] = financial.get('net_capital_costs')

                # Lifecycle Costs
                results['lcc_us_dollars'] = financial.get('lcc_us_dollars')

                 # Lifecycle Costs BAU
                results['lcc_bau_us_dollars'] = financial.get('lcc_bau_us_dollars')

                #Other Financials
                results['net_capital_costs_plus_om_us_dollars'] = financial.get('net_capital_costs_plus_om_us_dollars')
                results['net_om_us_dollars_bau'] = financial.get('net_om_us_dollars_bau')
                results['net_capital_costs'] = financial.get('net_capital_costs')

                # Year 1 Savings
                year_one_costs = sum(filter(None, [
                    tariff.get('year_one_energy_cost_us_dollars') or 0,
                    tariff.get('year_one_demand_cost_us_dollars') or 0,
                    tariff.get('year_one_fixed_cost_us_dollars') or 0,
                    tariff.get('year_one_min_charge_adder_us_dollars') or 0,
                    tariff.get('year_one_coincident_peak_cost_us_dollars') or 0,
                    tariff.get('year_one_bill_us_dollars') or 0
                    ]))
                
                year_one_costs_bau = sum(filter(None, [
                    tariff.get('year_one_energy_cost_bau_us_dollars') or 0,
                    tariff.get('year_one_demand_cost_bau_us_dollars') or 0,
                    tariff.get('year_one_fixed_cost_bau_us_dollars') or 0,
                    tariff.get('year_one_min_charge_adder_bau_us_dollars') or 0,
                    tariff.get('year_one_coincident_peak_cost_bau_us_dollars') or 0,
                    tariff.get('year_one_bill_bau_us_dollars') or 0
                    ]))

                #Resilience Stats
                results['resilience_hours_min'] = resilience.get('resilience_hours_min', 'not evaluated')
                results['resilience_hours_max'] = resilience.get('resilience_hours_max', 'not evaluated')
                results['resilience_hours_avg'] = resilience.get('resilience_hours_avg', 'not evaluated')
                
                results['year_one_savings_us_dollars'] = year_one_costs_bau - year_one_costs

                # PV Size
                if pv is not None:
                    if pv['max_kw'] > 0:
                        results['pv_kw'] = pv.get('size_kw')

                # Wind Size
                if wind is not None:
                    if wind.get('max_kw') or -1 > 0:
                        results['wind_kw'] = wind.get('size_kw')

                # Generator Size
                if gen is not None:
                    if gen.get('max_kw') or -1 > 0:
                        results['gen_kw'] = gen.get('size_kw')

                # Battery Size
                if batt is not None:
                    if batt.get('max_kw') or -1 > 0:
                        results['batt_kw'] = batt.get('size_kw')
                        results['batt_kwh'] = batt.get('size_kwh')

                if chp is not None:
                    if (chp.get('max_kw') or -1) > 0:
                        results['chp_kw'] = chp.get('size_kw')

                # HotTES Size
                if hottes is not None:
                    if (hottes.get('max_gal') or -1) > 0:
                        results['hottes_gal'] = hottes.get('size_gal')

                # ColdTES Size
                if coldtes is not None:
                    if (coldtes.get('max_gal') or -1) > 0:
                        results['coldtes_gal'] = coldtes.get('size_gal')

                # Absoprtion Chiller Size
                if absorpchl is not None:
                    if (absorpchl.get('max_ton') or -1) > 0:
                        results['absorpchl_ton'] = absorpchl.get('size_ton')

                # GHP size
                if ghp is not None:
                    if (ghp.get("building_sqft") or -1) > 0:
                        if ghp.get("ghpghx_chosen_outputs"):
                            results['ghp_ton'] = ghp.get('size_heat_pump_ton')
                            results['ghp_bores'] = ghp["ghpghx_chosen_outputs"]["number_of_boreholes"]
                
                # SteamTurbine size
                if steamturbine is not None:
                    if (steamturbine.get('max_kw') or -1) > 0:
                        results['steamturbine_kw'] = steamturbine.get('size_kw')

        except:
            json_response['scenarios'].append(results)
            continue
        else:
            json_response['scenarios'].append(results)
    return json_response

def summary(request, user_uuid):
    """
    Retrieve a summary of scenarios for given user_uuid
    :param request:
    :param user_uuid:
    :return:
        {
            "user_uuid",
            "scenarios":
                [{
                  "run_uuid",                   # Run ID
                  "status",                     # Status
                  "created",                    # Date
                  "description",                # Description
                  "focus",                      # Focus
                  "address",                    # Address
                  "urdb_rate_name",             # Utility Tariff
                  "doe_reference_name",         # Load Profile
                  "npv_us_dollars",             # Net Present Value ($)
                  "net_capital_costs",          # DG System Cost ($)
                  "year_one_savings_us_dollars",# Year 1 Savings ($)
                  "pv_kw",                      # PV Size (kW)
                  "wind_kw",                    # Wind Size (kW)
                  "gen_kw",                     # Generator Size (kW)
                  "batt_kw",                    # Battery Power (kW)
                  "batt_kwh"                    # Battery Capacity (kWh)
                  ""
                }]
        }
    """
    try:
        uuid.UUID(user_uuid)  # raises ValueError if not valid uuid

    except ValueError as e:
        if e.args[0] == "badly formed hexadecimal UUID string":
            return JsonResponse({"Error": str(e.message)}, status=404)
        else:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err = UnexpectedError(exc_type, exc_value, exc_traceback, task='summary', user_uuid=user_uuid)
            err.save_to_db()
            return JsonResponse({"Error": str(err.message)}, status=404)

    try:
        scenarios = ScenarioModel.objects.filter(user_uuid=user_uuid).order_by('-created')
        unlinked_run_uuids = [i.run_uuid for i in UserUnlinkedRuns.objects.filter(user_uuid=user_uuid)]
        scenarios = [s for s in scenarios if s.run_uuid not in unlinked_run_uuids]

        if len(scenarios) == 0:
            response = JsonResponse({"Error": "No scenarios found for user '{}'".format(user_uuid)}, content_type='application/json', status=404)
            return response
    
        json_response = get_user_summary_for_scenarios(scenarios, user_uuid)

        response = JsonResponse(json_response, status=200)
        return response

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err = UnexpectedError(exc_type, exc_value, exc_traceback, task='summary', user_uuid=user_uuid)
        err.save_to_db()
        return JsonResponse({"Error": err.message}, status=404)

def summary_by_chunk(request, user_uuid, chunk):
    """
    Retrieve a summary of scenarios for given user_uuid by chunk (i.e. a chunk is a subset of all user results). 
    Default chunk_size is 30, but this is customizable from the chunk_size URL parameter.
    
    :param request:
    :param user_uuid:
    :param chunk:
    :return:
        {
            "user_uuid",
            "scenarios":
                [{
                  "run_uuid",                   # Run ID
                  "status",                     # Status
                  "created",                    # Date
                  "description",                # Description
                  "focus",                      # Focus
                  "address",                    # Address
                  "urdb_rate_name",             # Utility Tariff
                  "doe_reference_name",         # Load Profile
                  "npv_us_dollars",             # Net Present Value ($)
                  "net_capital_costs",          # DG System Cost ($)
                  "year_one_savings_us_dollars",# Year 1 Savings ($)
                  "pv_kw",                      # PV Size (kW)
                  "wind_kw",                    # Wind Size (kW)
                  "gen_kw",                     # Generator Size (kW)
                  "batt_kw",                    # Battery Power (kW)
                  "batt_kwh"                    # Battery Capacity (kWh)
                  ""
                }]
        }
    """
    try:
        uuid.UUID(user_uuid)  # raises ValueError if not valid uuid

    except ValueError as e:
        if e.args[0] == "badly formed hexadecimal UUID string":
            return JsonResponse({"Error": str(e.message)}, status=404)
        else:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err = UnexpectedError(exc_type, exc_value, exc_traceback, task='summary', user_uuid=user_uuid)
            err.save_to_db()
            return JsonResponse({"Error": str(err.message)}, status=404)

    try:
        try:
            # chunk size is an optional URL parameter which defines the number of chunks into which to 
            # divide all user summary results. It must be a positive integer.
            default_chunk_size = 30
            chunk_size = int(request.GET.get('chunk_size') or default_chunk_size)
            if chunk_size != float(request.GET.get('chunk_size') or default_chunk_size):
                return JsonResponse({"Error": "Chunk size must be an integer."}, status=400)    
        except:
            return JsonResponse({"Error": "Chunk size must be a positive integer."}, status=400)
        
        try:
            # chunk is the 1-indexed indice of the chunks for which to return results. 
            # It must be a positive integer.
            chunk = int(chunk)
            if chunk < 1:
                response = JsonResponse({"Error": "Chunks are 1-indexed, please provide a chunk index greater than or equal to 1"}
                    , content_type='application/json', status=400)
                return response
        except:
            return JsonResponse({"Error": "Chunk number must be a 1-indexed integer."}, status=400)

        # Get all users run_uuids
        scenarios = ScenarioModel.objects.filter(user_uuid=user_uuid).order_by('-created')
        unlinked_run_uuids = [i.run_uuid for i in UserUnlinkedRuns.objects.filter(user_uuid=user_uuid)]
        scenarios = [s for s in scenarios if s.run_uuid not in unlinked_run_uuids]

        # If there are no runs for the user, return a message
        if len(scenarios) == 0:
            response = JsonResponse({"Error": "No scenarios found for user '{}'".format(user_uuid)}, content_type='application/json', status=404)
            return response
        
        # Determine total number of chunks from current query of user results based on the chunk size
        total_chunks = len(scenarios)/float(chunk_size)
        # If the last chunk is only patially full, i.e. there is a remainder, then add 1 so when it 
        # is converted to an integer the result will reflect the true total number of chunks
        if total_chunks%1 > 0: 
            total_chunks = total_chunks + 1
        # Make sure total chunks is an integer
        total_chunks = int(total_chunks)

        # Catch cases where user queries for a chunk that is more than the total chunks for the user
        if chunk > total_chunks:
            response = JsonResponse({"Error": "Chunk index {} is greater than the total number of chunks ({}) at a chunk size of {}".format(
                chunk, total_chunks, chunk_size)}, content_type='application/json', status=400)
            return response
        
        # Filter scenarios to the chunk
        start_idx = max((chunk-1) * chunk_size, 0)
        end_idx = min(chunk * chunk_size, len(scenarios))
        scenarios = scenarios[start_idx: end_idx]        
        
        # Get user results within the chunk range
        json_response = get_user_summary_for_scenarios(scenarios, user_uuid, total_chunks, chunk)
        
        response = JsonResponse(json_response, status=200)
        return response

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err = UnexpectedError(exc_type, exc_value, exc_traceback, task='summary', user_uuid=user_uuid)
        err.save_to_db()
        return JsonResponse({"Error": err.message}, status=404)
