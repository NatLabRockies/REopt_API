# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/load_builder/views.py
import csv
import io
import json
import sys
import numpy as np
from django.http import JsonResponse
from reo.exceptions import UnexpectedError

try:
    from ensitepy.simextension import enlitepyapi
except ImportError:
    enlitepyapi = None

# EnLitePy Configuration Constants
# These constants define default simulation-level parameters exposed to the UI.
# Units & Conventions:
#  * UI-facing aggregate power capacities (e.g., EMS/site charge cap) are in kW.
#  * Internal model power is Watts -> we convert via (kW * 1000) at ingress.
#  * Charging duration inputs are in hours; converted to integer seconds.
#  * Guardrails (min/max) are deliberately generous to catch obvious typos
#    (e.g., 0.1 kW or 1e9 kW) while not constraining legitimate large sites.
DEFAULT_CHARGER_DEFAULTS = {
    "L1": {"count": 0, "power_kW": 2.4, "eff": 0.80, "pci": "LD"},
    "L2": {"count": 0, "power_kW": 13.0, "eff": 0.80, "pci": "LD"},
    "DCFC_LD": {"count": 0, "power_kW": 50.0, "eff": 0.90, "pci": "LD"},
    "DCFC_MDHD": {"count": 0, "power_kW": 250.0, "eff": 0.90, "pci": "MD/HD"},
}

DEFAULT_VEHICLE_DEFAULTS = {
    "LD": {"weekday": 0, "weekend": 0, "battery_kWh": 80, "initSOC": 0.20, "targetSOC": 0.80, "pChgMax_kW": 120},
    "MD": {"weekday": 0, "weekend": 0, "battery_kWh": 200, "initSOC": 0.20, "targetSOC": 0.80, "pChgMax_kW": 300},
    "HD": {"weekday": 0, "weekend": 0, "battery_kWh": 500, "initSOC": 0.20, "targetSOC": 0.85, "pChgMax_kW": 600},
}
MAX_CHG_DURATION_DEFAULT_HR = None  # If set (e.g., 6), becomes default max charge duration (hours) unless UI overrides

SIM_DAYS = 7
EMS_CONFIG = {"type": "basic", "pChgCap": 0, "pap": "FCFS+SMX"}  # pChgCap (W) initialized to 0 until derived from chargers or overridden
SCHEMA_VERSION = 3  
BASE_SIM_CONFIG = {"tStart": 0, "tEnd": 7 * 24 * 3600, "dowStart": 0}
RESULTS_CONFIG_BASE = {"timeseriesDt": 3600, "powerMetricsDt": 3600}
WEEK_TO_YEAR_SCALE = 365 / 7

# Keys for annual scaling
EQUIPMENT_ANNUAL_SCALARS = {"Energy output [kWh]", "Energy loss [kWh]"}
EV_COUNT_SCALARS = {"Total EVs arrived [#]", "Total unique EVs arrived [#]", "EVs no queue wait [#]", "EVs arrived but not charged [#]", "EVs that did not start/complete charge [#]"}
EV_ENERGY_SCALARS = {"Total energy charged [kWh]"}

# ---------------------------------------------------------------------------
# EnLitePy Helper Functions
# ---------------------------------------------------------------------------

def build_arrival_pmf(weekday_pct, weekend_pct, bucket_hours=2):
    """Convert UI bucket percentages to API arrivalTimePMF structure."""
    bucket_seconds = bucket_hours * 3600

    def normalize(side, label):
        if len(side) != 12:
            raise ValueError(f"{label} arrival array must have 12 entries (got {len(side)})")
        if any(x < 0 for x in side):
            raise ValueError(f"{label} arrival percentages must be non-negative")
        active = [(i, x) for i, x in enumerate(side) if x > 0]
        if not active:  # fallback deterministic midnight arrival
            return {"val": [0], "prob": [1.0], "dur": bucket_seconds}
        total = sum(x for _, x in active)
        vals = [i * bucket_seconds for i, _ in active]
        probs = [x / total for _, x in active]
        # Adjust final probability for floating sum errors
        diff = 1.0 - sum(probs)
        if abs(diff) > 1e-9:
            probs[-1] += diff
        return {"val": vals, "prob": [round(p, 6) for p in probs], "dur": bucket_seconds}

    return {"1-5": normalize(weekday_pct, "Weekday"), "0,6": normalize(weekend_pct, "Weekend")}


def _validate_and_apply_ems_override(ems_override, base_cfg):
    """Validate EMS override accepting only pChgCap_kW (kW)."""
    cfg = dict(base_cfg)
    if not isinstance(ems_override, dict):
        return cfg
    pchgcap_kw = ems_override.get("pChgCap_kW")
    if "pChgCap" in ems_override and pchgcap_kw is None:
        raise ValueError("Unsupported key 'pChgCap'; use 'pChgCap_kW' (kW).")
    if pchgcap_kw is None:
        return cfg  # no override
    try:
        val_kw = float(pchgcap_kw)
        if val_kw <= 0:
            raise ValueError("pChgCap_kW must be > 0")
        cfg["pChgCap"] = int(round(val_kw * 1000))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid EMS capacity override: {exc}")
    return cfg


def build_enlitepy_payload(ui_inputs=None):
    """Translate UI schema into EnLitePy payload.

    UI INPUT SCHEMA (optional sections; omitted -> defaults):
      chargers: { <cat>: { count:int, power_kW:float, eff:float, pci:str } }
      vehicles: { <type>: { weekday:int, weekend:int, battery_kWh:float,
                            initSOC:float(0-1), targetSOC:float(0-1), pChgMax_kW:float } }
      arrival: { weekday:[12 % buckets], weekend:[12 % buckets] }
      ems: { pChgCap_kW:float }
      maxChargeDurationHr: float (>0)

        RULES / CONVERSIONS:
            * kW->W, kWh->Wh (ints); SOC & probabilities floats.
            * EMS capacity auto-derives from chargers if not overridden.
            * pChgMax_kW (kW) defines vehicle max charge power; required only to differ from defaults but is the sole accepted key.
            * Arrival arrays converted to PMF with 2h buckets.
            * maxChargeDurationHr -> seconds (int) stored as chgDurMax.

    Returns dict consumable by enlitepyapi.run(), augmented with schemaVersion.
    """
    ui = ui_inputs or {}

    # 1. Extract raw sections (fall back to empty dicts/lists)
    charger_in = ui.get("chargers") or {}
    vehicle_in = ui.get("vehicles") or {}
    arrival_in = ui.get("arrival") or {}
    ems_override = ui.get("ems") or {}
    max_duration_hr = ui.get("maxChargeDurationHr")
    if max_duration_hr is None and MAX_CHG_DURATION_DEFAULT_HR is not None:
        max_duration_hr = MAX_CHG_DURATION_DEFAULT_HR

    # 2. Merge chargers with defaults
    chargers = {}
    for cat, default_charger in DEFAULT_CHARGER_DEFAULTS.items():
        charger_cfg = {**default_charger}
        if isinstance(charger_in.get(cat), dict):
            charger_cfg.update(charger_in[cat])
        try:
            charger_cfg['count'] = int(charger_cfg.get('count', 0))
        except (TypeError, ValueError):
            raise ValueError(f"Invalid charger count for '{cat}'")
        try:
            charger_cfg['power_kW'] = float(charger_cfg.get('power_kW', default_charger['power_kW']))
        except (TypeError, ValueError):
            raise ValueError(f"Invalid charger power_kW for '{cat}'")
        chargers[cat] = charger_cfg

    # 3. Merge vehicles with defaults & normalize pChgMax
    vehicles = {}
    for vtype, default_vehicle in DEFAULT_VEHICLE_DEFAULTS.items():
        vehicle_cfg = {**default_vehicle}
        if isinstance(vehicle_in.get(vtype), dict):
            vehicle_cfg.update(vehicle_in[vtype])
        def _num(name, cast=float, positive=False, allow_zero=True):
            val = vehicle_cfg.get(name, default_vehicle.get(name))
            try:
                v = cast(val)
            except Exception:
                raise ValueError(f"Invalid value for '{name}' in vehicle '{vtype}'")
            if positive and (v < 0 or (not allow_zero and v == 0)):
                raise ValueError(f"'{name}' must be > 0 in vehicle '{vtype}'")
            return v
        vehicle_cfg['weekday'] = _num('weekday', cast=int)
        vehicle_cfg['weekend'] = _num('weekend', cast=int)
        vehicle_cfg['battery_kWh'] = _num('battery_kWh', cast=float, positive=True)
        vehicle_cfg['initSOC'] = max(0.0, min(1.0, _num('initSOC', cast=float)))
        vehicle_cfg['targetSOC'] = max(0.0, min(1.0, _num('targetSOC', cast=float)))
        if 'pChgMax_kW' in vehicle_cfg:
            try:
                pmax_kw = float(vehicle_cfg['pChgMax_kW'])
            except (TypeError, ValueError):
                raise ValueError(f"Invalid pChgMax_kW in vehicle '{vtype}'")
        else:
            pmax_kw = float(default_vehicle['pChgMax_kW'])
        if pmax_kw <= 0:
            raise ValueError(f"pChgMax_kW must be > 0 for vehicle '{vtype}'")
        vehicle_cfg['pChgMax_kW'] = pmax_kw
        vehicles[vtype] = vehicle_cfg

    # 4. Arrival PMFs
    weekday_pct = arrival_in.get('weekday', [0]*12)
    weekend_pct = arrival_in.get('weekend', [0]*12)
    arrival_pmf = build_arrival_pmf(weekday_pct, weekend_pct)

    # 5. EMS merge & dynamic capacity
    ems_cfg = _validate_and_apply_ems_override(ems_override, EMS_CONFIG)
    if ems_cfg.get('pChgCap') == 0 and not ems_override:
        derived_kw = 0.0
        for charger_cfg in chargers.values():
            try:
                derived_kw += charger_cfg['count'] * float(charger_cfg['power_kW'])
            except Exception:
                pass
        ems_cfg['pChgCap'] = int(round(max(0.0, derived_kw) * 1000))  # stays 0 if no chargers

    # 6. Nodes
    nodes = {
        'grid': {
            'type': 'Grid',
            'pMax': int(ems_cfg.get('pChgCap', 0)),  # no fallback; zero if not derived/overridden
            'pMin': 0,
            'eff': 1.0,
        }
    }
    for cat, charger_cfg in chargers.items():
        for idx in range(1, charger_cfg['count'] + 1):
            nodes[f'EVSE_{cat}_{idx}'] = {
                'type': 'EVSE',
                'pMax': int(round(charger_cfg['power_kW'] * 1000)),
                'pMin': 0,
                'eff': charger_cfg.get('eff', 0.9),
                'nEVPort': 1,
                'pci': charger_cfg.get('pci', cat),
            }

    # 7. EV Types
    def _expand_counts(weekend, weekday):
        return [weekend, weekday, weekday, weekday, weekday, weekday, weekend]
    ev_types = {}
    for vtype, veh_cfg in vehicles.items():
        delta = max(0.0, min(1.0, veh_cfg['targetSOC'] - veh_cfg['initSOC']))
        ev_types[vtype] = {
            'type': vtype,
            'eCap': int(round(veh_cfg['battery_kWh'] * 1000)),
            'pChgMax': int(round(veh_cfg['pChgMax_kW'] * 1000)),
            'count': _expand_counts(veh_cfg['weekend'], veh_cfg['weekday']),
            'targetFinalSOCPMF': {'val': [round(veh_cfg['targetSOC'], 4)], 'prob': [1.0]},
            'energyDemandPMF': {'val': [round(delta, 4)], 'prob': [1.0]},
            'arrivalTimePMF': arrival_pmf,
            'departureTimePMF': None,
        }

    # 8. Simulation config & duration
    sim_cfg = {**BASE_SIM_CONFIG, 'tEnd': SIM_DAYS * 24 * 3600}
    chg_dur_max = None
    if max_duration_hr is not None:
        try:
            md = float(max_duration_hr)
            if md <= 0:
                raise ValueError('maxChargeDurationHr must be > 0')
            chg_dur_max = int(round(md * 3600))
        except (TypeError, ValueError) as exc:
            raise ValueError(f'Invalid maxChargeDurationHr: {exc}')

    # 9. Compose payload
    payload = {
        'simConfig': sim_cfg,
        'hubConfig': {'nodes': nodes, 'ems': ems_cfg},
        'evInfo': {'stochasticModel': 1, 'chgDurMax': chg_dur_max, 'evTypes': ev_types},
        'resultsConfig': {**RESULTS_CONFIG_BASE, 'resultFieldOptions': {
            'nodes': 'Grid', 'portUsage': True, 'queueLength': True, 'nodeStats': True, 'evStats': True
        }},
        'schemaVersion': SCHEMA_VERSION,
    }
    return payload


def is_ui_input(data):
    """Detect if input is UI format vs direct EnLitePy payload."""
    if not isinstance(data, dict):
        return False
    
    # Check for UI-specific keys
    ui_keys = {"chargers", "vehicles", "arrival", "maxChargeDurationHr", "ems"}
    if any(key in data for key in ui_keys):
        return True
    
    # Check for direct EnLitePy payload keys
    enlitepy_keys = {"simConfig", "hubConfig", "evInfo", "resultsConfig"}
    if any(key in data for key in enlitepy_keys):
        return False
    
    # Default to UI format for safety
    return True

def ensite_view(request):
    """Enhanced EnLitePy endpoint that handles both UI inputs and direct payloads."""
    if enlitepyapi is not None:
        try:
            if request.method == 'POST':
                try:
                    input_data = json.loads(request.body)
                except json.JSONDecodeError as e:
                    return JsonResponse({"Error": f"Invalid JSON in request body: {e}"}, status=400)
                include_debug_payload = False
                if is_ui_input(input_data):
                    try:
                        include_debug_payload = bool(input_data.get('includeDebugPayload'))
                        enlitepy_payload = build_enlitepy_payload(input_data)
                    except Exception as e:
                        return JsonResponse({"Error": f"Failed to build EnLitePy payload: {e}"}, status=400)
                else:
                    enlitepy_payload = input_data
                try:
                    results = enlitepyapi.run(enlitepy_payload)
                    if isinstance(results, dict) and 'logs' not in results:
                        results['logs'] = []
                    if include_debug_payload and isinstance(results, dict):
                        # Attach payload echo for debugging/audit (safe subset of request inputs)
                        results.setdefault('debug', {})
                        results['debug']['payloadEcho'] = enlitepy_payload
                        try:
                            results['logs'].append('Debug: payloadEcho attached (includes computed pChgMax values in Watts).')
                        except Exception:
                            pass
                    # Always normalize and annualize for client convenience
                    _normalize_and_enrich(results)
                    # Bump enrichment version to 2 to reflect unit change (power_in_grid_annual now in kW)
                    results.setdefault('version', 2)
                    return JsonResponse({"results": results})
                except Exception as e:
                    return JsonResponse({"Error": f"EnLitePy execution failed: {e}"}, status=500)
            else:
                return JsonResponse({"Error": "Must POST a JSON body for ensitepy."}, status=400)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err = UnexpectedError(exc_type, exc_value, exc_traceback, task='ensite')
            return JsonResponse({"Error": err.message}, status=500)
    else:
        return JsonResponse({"Error": "ensitepy is not installed."}, status=500)
    

def check_load_builder_inputs(loads_table):
    required_inputs = ["Power (W)", "Quantity", "% Run Time", "Start Mo.", "Stop Mo.", "Start Hr.", "Stop Hr."]
    for load in loads_table:
        inputs = load.keys()
        for required_input in required_inputs:
            if required_input in inputs:
                pass
            else:
                return False
    return True


def validate_load_builder_inputs(loads_table):
    numeric_inputs = ["Power (W)", "Quantity", "% Run Time"]
    hour_inputs = ["Start Hr.", "Stop Hr."]
    month_inputs = ["Start Mo.", "Stop Mo."]
    required_hours = list(np.linspace(0,24,25).astype(int))
    required_months= ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    for load in loads_table:

        for numeric_input in numeric_inputs:
            try:
                float(load[numeric_input])
            except Exception:
                return False

        for month_input in month_inputs:
            if load[month_input] not in required_months:
                return False

        for hour_input in hour_inputs:
            if int(load[hour_input]) not in required_hours:
                return False

    return True


def load_builder(request):
    """
    Convert the SolarResilient Component Load Builder CSV into an 8760 Load
    :param request:
    :return: 8760 list for critical_load_kw input into REOpt
    """
    try:
        if request.method == 'POST':
            post = request.body
            try:
                # Try to import JSON, then fall back to CSV
                try:
                    loads_table = json.loads(post)
                except Exception:
                    loads_table = post.decode("utf-8")
                finally:
                    if not isinstance(loads_table, list):
                        csv_reader = csv.DictReader(io.StringIO(loads_table))
                        loads_table = list(csv_reader)
            except Exception:
                return JsonResponse({"Error": "Invalid JSON or CSV"})

            # Validation
            if not check_load_builder_inputs(loads_table):
                return JsonResponse({"Error": "There are missing required inputs. Must include the following: 'Power (W)', 'Quantity', '% Run Time', 'Start Mo.', 'Stop Mo.', 'Start Hr.', 'Stop Hr.'"})
            if not validate_load_builder_inputs(loads_table):
                return JsonResponse({"Error": "Some input values are invalid"})

            # Run conversion and respond
            loads_kw = convert_loads(loads_table)
            return JsonResponse({"critical_loads_kw": loads_kw})

        else:
            return JsonResponse({"Error": "Must POST a JSON based on the SolarResilient component based load builder downloadable CSV"})

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err = UnexpectedError(exc_type, exc_value, exc_traceback, task='load_builder')
        err.save_to_db()
        return JsonResponse({"Error": err.message}, status=500)


def convert_loads(loads_table):
    """
    Generates critical load profile from critical load builder
    :param loads_table: (json string) contain data from load table
    :return: (1 list) hourly load values (8,760 values) in kw
    """

    class Load:
        def __init__(self, power_total, start_hour, stop_hour, start_month, stop_month):
            self.power_total = power_total
            self.start_hour = start_hour
            self.stop_hour = stop_hour
            self.start_month = start_month
            self.stop_month = stop_month

    def translate_months(string):
        """
        Translate month names to number
        :param string: (str) name of month
        :return: (int) number of month
        """
        switcher = {
            "January": 0,
            "February": 1,
            "March": 2,
            "April": 3,
            "May": 4,
            "June": 5,
            "July": 6,
            "August": 7,
            "September": 8,
            "October": 9,
            "November": 10,
            "December": 11,
        }
        return switcher.get(string, 0)

    loads = []
    for row in loads_table:
        power = int(row["Power (W)"]) * int(row["Quantity"]) * (float(row["% Run Time"]) / 100) / 1000  # total hourly power in kW
        # checks if stop_month has a smaller value than start_month
        start_mo = int(translate_months(row["Start Mo."]))
        stop_mo = int(translate_months(row["Stop Mo."]))
        months = []
        if start_mo < stop_mo:
            months.append((start_mo, stop_mo))
        else:
            months.append((start_mo, 11))
            months.append((0, stop_mo))
        # check if fixture/appliance is running over midnight
        start_hr = int(row["Start Hr."])
        stop_hr = int(row["Stop Hr."])
        hours = []
        if start_hr <= stop_hr:
            hours.append((start_hr, stop_hr))
        else:
            hours.append((start_hr, 24))
            hours.append((0, stop_hr))
        for (start_mo, stop_mo) in months:
            for (start_hr, stop_hr) in hours:
                loads.append(Load(power, start_hr, stop_hr, start_mo, stop_mo))
    loads_kw = []
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for month in range(12):
        number_days = days_per_month[month]
        for days in range(number_days):
            for hr in range(24):
                hour_load = 0
                for load in loads:
                    if load.start_month <= month and load.stop_month >= month:
                        if load.start_hour <= hr and load.stop_hour > hr:
                            hour_load += load.power_total
                loads_kw.append(hour_load)
    return loads_kw

# (Removed duplicate constant definitions that appeared earlier in file)

def _replicate_to_8760(series):
    if not isinstance(series, list) or len(series) == 0:
        return series
    if len(series) == 8760:
        return series
    reps = (8760 // len(series)) + 1
    return (series * reps)[:8760]

def _annualize_equipment(stats_list):
    if not isinstance(stats_list, list):
        return []
    out = []
    for row in stats_list:
        if not isinstance(row, dict):
            continue
        copy = row.copy()
        for k in EQUIPMENT_ANNUAL_SCALARS:
            v = copy.get(k)
            if isinstance(v, (int, float)):
                copy[k] = round(v * WEEK_TO_YEAR_SCALE, 2)
        out.append(copy)
    return out

def _annualize_ev(stats_list):
    if not isinstance(stats_list, list):
        return []
    out = []
    for row in stats_list:
        if not isinstance(row, dict):
            continue
        copy = row.copy()
        for k, v in list(copy.items()):
            if k in EV_COUNT_SCALARS or k in EV_ENERGY_SCALARS:
                if isinstance(v, (int, float)):
                    copy[k] = round(v * WEEK_TO_YEAR_SCALE, 2)
            if k.endswith('[min]') and isinstance(v, (int, float)):
                copy[k.replace('[min]', '[h]')] = round(v / 60.0, 2)
                del copy[k]
        out.append(copy)
    return out



def _normalize_and_enrich(results_dict):
    if not isinstance(results_dict, dict):
        return
    # Normalize stringified JSON lists
    for key in ('equipment_statistics', 'ev_statistics'):
        val = results_dict.get(key)
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    results_dict[key] = parsed
            except json.JSONDecodeError:
                pass
    equipment = results_dict.get('equipment_statistics') or []
    evstats = results_dict.get('ev_statistics') or []
    timeseries = results_dict.get('timeseries')
    # Annual replication for timeseries
    if isinstance(timeseries, dict) and 'power_in_grid' in timeseries:
        annual_series = _replicate_to_8760(timeseries['power_in_grid'])
        if isinstance(annual_series, list) and len(annual_series) == 8760:
            # Convert from W (simulation native) to kW for annual series exposure
            timeseries['power_in_grid_annual'] = [x / 1000 for x in annual_series]
    equip_annual = _annualize_equipment(equipment) if equipment else []
    ev_annual = _annualize_ev(evstats) if evstats else []
    if equip_annual:
        results_dict['equipment_statistics_annual'] = equip_annual
    if ev_annual:
        results_dict['ev_statistics_annual'] = ev_annual
