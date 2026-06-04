# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
#!usr/bin/python
from math import floor
import pandas as pd
from celery import group, shared_task, chord
from time import sleep


@shared_task
def simulate_outage(init_time_step, diesel_kw, fuel_available, b, m, batt_kwh, batt_kw,
                    batt_roundtrip_efficiency, n_timesteps, n_steps_per_hour, batt_soc_kwh, crit_load, chp_kw):
    """
    Determine how long the critical load can be met with gas generator and energy storage.
    Celery task used to parallelize outage simulations starting every time step in a year.
    :param init_time_step: int, initial time step
    :param diesel_kw: float, generator capacity
    :param fuel_available: float, gallons
    :param b: float, diesel fuel burn rate intercept coefficient (y = m*x + b)  [gal/hr]
    :param m: float, diesel fuel burn rate slope (y = m*x + b)  [gal/kWh]
    :param batt_kwh: float, battery capacity
    :param batt_kw: float, battery inverter capacity (AC rating)
    :param batt_roundtrip_efficiency:
    :param batt_soc_kwh: float, battery state of charge in kWh
    :param n_timesteps: int, number of time steps in a year
    :param n_steps_per_hour: int, number of time steps per hour
    :param crit_load: list of float, load after DER (PV, Wind, ...)
    :return: float, number of hours that the critical load can be met using load following
    """
    for i in range(n_timesteps):
        t = (init_time_step + i) % n_timesteps  # for wrapping around end of year
        load_kw = crit_load[t]
        load_kw -= chp_kw  # Run CHP. No limit on fuel, no turndown constraint
        if load_kw < 0:  # load is met
            if batt_soc_kwh < batt_kwh:  # charge battery if there's room in the battery
                batt_soc_kwh += min(
                    batt_kwh - batt_soc_kwh,     # room available
                    batt_kw / n_steps_per_hour * batt_roundtrip_efficiency,  # inverter capacity
                    -load_kw / n_steps_per_hour * batt_roundtrip_efficiency,  # excess energy
                )
        else:  # check if we can meet load with generator then storage
            fuel_needed = (m * load_kw + b) / n_steps_per_hour
            # (gal/kWh * kW + gal/hr) * hr = gal

            if load_kw <= diesel_kw and fuel_needed <= fuel_available:  # diesel can meet load
                fuel_available -= fuel_needed
                load_kw = 0
            else:  # diesel can meet part or no load

                if fuel_needed > fuel_available and load_kw <= diesel_kw:  # tank is limiting factor
                    load_kw -= max(0, (fuel_available * n_steps_per_hour - b) / m)  # (gal/hr - gal/hr) * kWh/gal = kW
                    fuel_available = 0

                    # check if battery can meet remaining load_kw
                    if min(batt_kw, batt_soc_kwh * n_steps_per_hour) >= load_kw:  # battery can carry balance
                        # prevent battery charge from going negative
                        batt_soc_kwh = max(0, batt_soc_kwh - load_kw / n_steps_per_hour)
                        load_kw = 0

                elif fuel_needed <= fuel_available and load_kw > diesel_kw:  # diesel capacity is limiting factor
                    load_kw -= diesel_kw
                    # run diesel gen at max output
                    fuel_available = max(0, fuel_available - (diesel_kw * m + b) / n_steps_per_hour)
                                                              # (kW * gal/kWh + gal/hr) * hr = gal
                    # check if battery can meet remaining load_kw
                    if min(batt_kw, batt_soc_kwh * n_steps_per_hour) >= load_kw:  # battery can carry balance
                        # prevent battery charge from going negative
                        batt_soc_kwh = max(0, batt_soc_kwh - load_kw / n_steps_per_hour)
                        load_kw = 0

                elif min(batt_kw, batt_soc_kwh * n_steps_per_hour) >= load_kw:  # battery can carry balance
                        # prevent battery charge from going negative
                        batt_soc_kwh = max(0, batt_soc_kwh - load_kw / n_steps_per_hour)
                        load_kw = 0

        if round(load_kw, 5) > 0:  # failed to meet load in this time step
            return float(i) / float(n_steps_per_hour)

    return n_timesteps / n_steps_per_hour  # met the critical load for all time steps


def simulate_outages(batt_kwh=0, batt_kw=0, pv_kw_ac_hourly=[], init_soc=0, critical_loads_kw=[], wind_kw_ac_hourly=None,
                     batt_roundtrip_efficiency=0.829, diesel_kw=0, fuel_available=0, b=0, m=0,
                     celery_eager=True, chp_kw=0
                     ):
    """
    :param batt_kwh: float, battery storage capacity
    :param batt_kw: float, battery inverter capacity
    :param pv_kw_ac_hourly: list of floats, AC production of PV system
    :param init_soc: list of floats between 0 and 1 inclusive, initial state-of-charge
    :param critical_loads_kw: list of floats
    :param wind_kw_ac_hourly: list of floats, AC production of wind turbine
    :param batt_roundtrip_efficiency: roundtrip battery efficiency
    :param diesel_kw: float, diesel generator capacity
    :param fuel_available: float, gallons of diesel fuel available
    :param b: float, diesel fuel burn rate intercept coefficient (y = m*x + b*rated_capacity)  [gal/kwh/kw]
    :param m: float, diesel fuel burn rate slope (y = m*x + b*rated_capacity)  [gal/kWh]
    :return: dict,
        {
            "resilience_by_timestep": r,
            "resilience_hours_min": r_min,
            "resilience_hours_max": r_max,
            "resilience_hours_avg": r_avg,
            "outage_durations": x_vals,
            "probs_of_surviving": y_vals,
            "probs_of_surviving_by_month": y_vals_group_month,
            "probs_of_surviving_by_hour_of_the_day": y_vals_group_hour,
        }
    """
    n_timesteps = len(critical_loads_kw)
    n_steps_per_hour = int(n_timesteps / 8760)
    r = [0] * n_timesteps

    if batt_kw == 0 or batt_kwh == 0:
        init_soc = [0] * n_timesteps  # default is None

        if ((pv_kw_ac_hourly in [None, []]) or (sum(pv_kw_ac_hourly) == 0)) and diesel_kw == 0 and chp_kw == 0:
            # no pv, generator, nor battery --> no resilience
            return {"resilience_by_timestep": r,
                    "resilience_hours_min": 0,
                    "resilience_hours_max": 0,
                    "resilience_hours_avg": 0,
                    "outage_durations": [],
                    "probs_of_surviving": [],
                    "probs_of_surviving_by_month": [[0] for _ in range(12)],
                    "probs_of_surviving_by_hour_of_the_day": [[0] for _ in range(24)],
                    }

    if chp_kw >= max(critical_loads_kw):
        return {"resilience_by_timestep": [8760] * n_timesteps,
                "resilience_hours_min": 8760,
                "resilience_hours_max": 8760,
                "resilience_hours_avg": 8760,
                "outage_durations": list(range(1,8761)),
                "probs_of_surviving": [1.0] * n_timesteps,
                "probs_of_surviving_by_month": [[1.0] for _ in range(12)],
                "probs_of_surviving_by_hour_of_the_day": [[1.0] for _ in range(24)],
                }

    if pv_kw_ac_hourly in [None, []]:
        pv_kw_ac_hourly = [0] * n_timesteps
    if wind_kw_ac_hourly in [None, []]:
        wind_kw_ac_hourly = [0] * n_timesteps
    load_minus_der = [ld - pv - wd for (pv, wd, ld) in zip(pv_kw_ac_hourly, wind_kw_ac_hourly, critical_loads_kw)]
    '''
    Simulation starts here
    '''
    # outer loop: do simulation starting at each time step
    if not celery_eager:  # run jobs in parallel
        jobs = group(simulate_outage.s(
            init_time_step=time_step,
            diesel_kw=diesel_kw,
            fuel_available=fuel_available,
            b=b, m=m,
            batt_kwh=batt_kwh,
            batt_kw=batt_kw,
            batt_roundtrip_efficiency=batt_roundtrip_efficiency,
            n_timesteps=n_timesteps,
            n_steps_per_hour=n_steps_per_hour,
            batt_soc_kwh=init_soc[time_step]*batt_kwh,
            crit_load=load_minus_der,
            chp_kw=chp_kw
        ) for time_step in range(n_timesteps)
        )
        result = chord(jobs, process_results.s(n_steps_per_hour, n_timesteps)).delay()
        while not result.ready():
            sleep(2)
        if not result.successful():
            raise Exception("Outage simulator failed.")
        return result.result
    else:  # run jobs serially, faster when each job only takes a small amount of time
        for time_step in range(n_timesteps):
            r[time_step] = simulate_outage(
                init_time_step=time_step,
                diesel_kw=diesel_kw,
                fuel_available=fuel_available,
                b=b, m=m,
                batt_kwh=batt_kwh,
                batt_kw=batt_kw,
                batt_roundtrip_efficiency=batt_roundtrip_efficiency,
                n_timesteps=n_timesteps,
                n_steps_per_hour=n_steps_per_hour,
                batt_soc_kwh=init_soc[time_step] * batt_kwh,
                crit_load=load_minus_der,
                chp_kw=chp_kw
            )
        results = process_results(r, n_steps_per_hour, n_timesteps)
        return results


@shared_task
def process_results(r, n_steps_per_hour, n_timesteps):

    r_min = min(r)
    r_max = max(r)
    r_avg = round((float(sum(r)) / float(len(r))), 2)

    # Create a time series of 8760*n_steps_per_hour elements starting on 1/1/2017
    time = pd.date_range('1/1/2017', periods=8760*n_steps_per_hour, freq='{}min'.format(n_steps_per_hour*60))
    r_series = pd.Series(r, index=time)

    r_group_month = r_series.groupby(r_series.index.month)
    r_group_hour = r_series.groupby(r_series.index.hour)

    x_vals = list(range(1, int(floor(r_max)+1)))
    y_vals = list()
    y_vals_group_month = list()
    y_vals_group_hour = list()

    for hrs in x_vals:
        y_vals.append(round(float(sum([1 if h >= hrs else 0 for h in r])) / float(n_timesteps), 4))

    if len(x_vals) > 0:
        width = 0
        for k, v in r_group_month:
            tmp = list()
            max_hr = int(v.max()) + 1
            for hrs in range(max_hr):
                tmp.append(round(float(sum([1 if h >= hrs else 0 for h in v])) / float(len(v)), 4))
            y_vals_group_month.append(tmp)
            if max_hr > width:
                width = max_hr

        # PostgreSQL requires that the arrays are rectangular
        for i, v in enumerate(y_vals_group_month):
            y_vals_group_month[i] = v + [0] * (width - len(v))

        width = 0
        for k, v in r_group_hour:
            tmp = list()
            max_hr = int(v.max()) + 1
            for hrs in range(max_hr):
                tmp.append(round(float(sum([1 if h >= hrs else 0 for h in v])) / float(len(v)), 4))
            y_vals_group_hour.append(tmp)
            if max_hr > width:
                width = max_hr

        # PostgreSQL requires that the arrays are rectangular
        for i, v in enumerate(y_vals_group_hour):
            y_vals_group_hour[i] = v + [0] * (width - len(v))

    return {"resilience_by_timestep": r,
            "resilience_hours_min": r_min,
            "resilience_hours_max": r_max,
            "resilience_hours_avg": r_avg,
            "outage_durations": x_vals,
            "probs_of_surviving": y_vals,
            "probs_of_surviving_by_month": y_vals_group_month,
            "probs_of_surviving_by_hour_of_the_day": y_vals_group_hour,
            }
