# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
# ============================================================================
# MPC (Model Predictive Control) endpoint
# ----------------------------------------------------------------------------
# Rolling-horizon dispatch with one day look-ahead using REopt.run_mpc. Assumes:
#   * PV and ElectricStorage are the only available technologies 
#   * Only perfect forecast scenarios are modeled (no forecast errors)
#   * Sizing: Perform a sizing run first if PV or ElectricStorage sizes are not provided (storage sizes must be > 0)
#   * PV: Use PVWatts if `PV.production_factor_series` is not provided
#   * ElectricLoad: Use commercial reference profiles if `ElectricLoad.loads_kw` is not provided
#   * Code wraps with Jan 1 data to determine Dec 31 dispatch (leap-year inputs are not supported)
#   * MPC settings are currently hard coded (e.g., forecast horizon, control horizon, optimization horizon)
# ============================================================================

"""
    get_month_transition_timesteps(time_steps_per_hour)

Return an array of length 12 specifying the index marking the start of each month in a non-leap year
"""
function get_month_transition_timesteps(time_steps_per_hour::Int)
    # hours in each month for a non-leap year
    hours_per_month = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744]
    starts = Vector{Int}(undef, 12)
    starts[1] = 1
    for m in 2:12
        starts[m] = starts[m-1] + hours_per_month[m-1] * time_steps_per_hour
    end
    return starts
end

"""
    slice_data(arr, idx, end_idx)

Returns arr[idx:end_idx] but wrap around to the start of arr if end_idx > length(arr).
"""
function slice_data(arr::AbstractVector, idx::Int, end_idx::Int)
    n = length(arr)
    if end_idx <= n
        return arr[idx:end_idx]
    else
        wrap_len = end_idx - n
        return vcat(arr[idx:n], arr[1:wrap_len])
    end
end

"""
    check_series_length(name, series, time_steps_per_hour, length_of_data)

Validate that a user-entered time series is of length 8760 * time_steps_per_hour (cannot be a leap year).
"""
function check_series_length(name::String, series::AbstractVector, length_of_data::Int)
    n = length(series)
    if n == length_of_data 
        return series
    end
    error("MPC: $name length $n != 8760 * time_steps_per_hour ($length_of_data).")
end

"""
    get_tariff_inputs(electric_tariff, year, time_steps_per_hour)

Call REopt.ElectricTariff to get energy_rates, monthly_demand_rates, tou_demand_rates, tou_demand_ratchet_time_steps
MPC does not currently model tiers (tiers are flattened), coincident peak charges, or demand lookback.
"""
function get_tariff_inputs(electric_tariff::Dict, year::Union{Int,Nothing}, time_steps_per_hour::Int)
    
    # TODO: Are all of these relevant? Any missing inputs? 
    # TODO: Implement lookback? (demand_lookback_months, demand_lookback_percent, demand_lookback_range) Ignoring coincident peak charges for now
    # TODO: Need to think through NEM or passing back export values (wholesale_rate, export_rate_beyond_net_metering_limit)
    tariff_kwargs = (:urdb_label, :urdb_response, :urdb_utility_name,
                    :urdb_rate_name, :urdb_metadata,
                    :wholesale_rate, :export_rate_beyond_net_metering_limit,
                    :monthly_energy_rates, :monthly_demand_rates,
                    :blended_annual_energy_rate, :blended_annual_demand_rate,
                    :add_monthly_rates_to_urdb_rate,
                    :tou_energy_rates_per_kwh, :add_tou_energy_rates_to_urdb_rate,
                    :demand_lookback_months, :demand_lookback_percent, :demand_lookback_range)
    kwargs = Dict{Symbol,Any}(Symbol(k) => v for (k, v) in electric_tariff if Symbol(k) in tariff_kwargs)

    # MPC does not currently model tiered rates
    kwargs[:remove_tiers] = true
    tariff = reoptjl.ElectricTariff(; year = year, time_steps_per_hour = time_steps_per_hour, kwargs...)

    energy_rates = Float64.(tariff.energy_rates[:, 1])
    monthly_demand_rates = isempty(tariff.monthly_demand_rates) ?
                           zeros(Float64, 12) : Float64.(tariff.monthly_demand_rates[:, 1])
    tou_demand_rates = isempty(tariff.tou_demand_rates) ? Float64[] : Float64.(tariff.tou_demand_rates[:, 1])
    tou_demand_ratchet_time_steps = [Int.(v) for v in tariff.tou_demand_ratchet_time_steps]

    # TODO: Track lookback variables - demand_lookback_months, demand_lookback_percent, demand_lookback_range?
    return (energy_rates = energy_rates,
            monthly_demand_rates = monthly_demand_rates,
            tou_demand_rates = tou_demand_rates,
            tou_demand_ratchet_time_steps = tou_demand_ratchet_time_steps)
end

"""
    generate_pv_production_factors(d, time_steps_per_hour)

Generate a PV production factor series using PVWatts by calling REopt.get_production_factor
"""
function generate_pv_production_factors(d::Dict, time_steps_per_hour::Int)
    site = get(d, "Site", Dict())
    if !haskey(site, "latitude")
        error("MPC: Site.latitude is required to generate PV.production_factor_series using PVWatts.")
    end
    if !haskey(site, "longitude")
        error("MPC: Site.longitude is required to generate PV.production_factor_series using PVWatts.")
    end
    lat = Float64(site["latitude"])
    lon = Float64(site["longitude"])

    @info "MPC: PV.production_factor_series not provided; generating using PVWatts through REopt.jl (lat=$(lat), lon=$(lon))."

    pv = get(d, "PV", Dict())
    pv_pf_kwargs = (:array_type, :tilt, :module_type, :losses, :azimuth, :gcr,
                    :radius, :name, :location, :dc_ac_ratio, :inv_eff)
    kwargs = Dict{Symbol,Any}(Symbol(k) => v for (k, v) in pv if Symbol(k) in pv_pf_kwargs)
    pv_struct = reoptjl.PV(; latitude = lat, kwargs...)
    pv_production_factor_series = reoptjl.get_production_factor(pv_struct, lat, lon;
                                                                time_steps_per_hour = time_steps_per_hour)
    return Vector{Float64}(pv_production_factor_series)
end

"""
    generate_loads_kw(d, time_steps_per_hour)

Generate an electric load profile using DOE Commercial Reference buildings by calling REopt.ElectricLoad 
"""
function generate_loads_kw(d::Dict, time_steps_per_hour::Int)
    site = get(d, "Site", Dict())
    if !haskey(site, "latitude")
        error("MPC: Site.latitude is required to generate ElectricLoad.loads_kw using a DOE CRB profile.")
    end
    if !haskey(site, "longitude")
        error("MPC: Site.longitude is required to generate ElectricLoad.loads_kw using a DOE CRB profile.")
    end
    lat = Float64(site["latitude"])
    lon = Float64(site["longitude"])

    @info "MPC: ElectricLoad.loads_kw not provided; generating via REopt.jl ElectricLoad (lat=$(lat), lon=$(lon))."

    electric_load = get(d, "ElectricLoad", Dict())

    # TODO: Double check this list for relevance/missing inputs
    load_kwargs = (:normalize_and_scale_load_profile_input,
                    :path_to_csv, :doe_reference_name,
                    :blended_doe_reference_names, :blended_doe_reference_percents,
                    :year, :city, :annual_kwh, :monthly_totals_kwh,
                    :monthly_peaks_kw, :loads_kw_is_net)
    kwargs = Dict{Symbol,Any}(Symbol(k) => v for (k, v) in electric_load if Symbol(k) in load_kwargs)
    load = reoptjl.ElectricLoad(; latitude = lat, longitude = lon,
                                         time_steps_per_hour = time_steps_per_hour, kwargs...)
    return Vector{Float64}(load.loads_kw)
end

"""
    get_technology_sizes!(d)

Determine PV and ElectricStorage sizes for the MPC loop. If min_kw != max_kw and/or min_kwh != max_kwh,
call REopt to size technologies. User input battery sizes must also be greater than zero.
"""
function get_technology_sizes!(d::Dict)
    pv   = get!(d, "PV", Dict())
    batt = get!(d, "ElectricStorage", Dict())

    function is_fixed(dct, lo_key, hi_key)
        lo = get(dct, lo_key, nothing)
        hi = get(dct, hi_key, nothing)
        return lo !== nothing && hi !== nothing && Float64(lo) == Float64(hi)
    end

    # Check storage sizes are greater than zero
    if Float64(get(batt, "max_kw",  1.0)) <= 0.0 || Float64(get(batt, "max_kwh", 1.0)) <= 0.0
        error("ElectricStorage max_kw and max_kwh must both be greater than zero " *
              "to run the daily_foresight_optimized dispatch option.")
    end

    pv_fixed   = is_fixed(pv,   "min_kw",  "max_kw")
    batt_fixed = is_fixed(batt, "min_kw",  "max_kw") &&
                 is_fixed(batt, "min_kwh", "max_kwh")

    if pv_fixed && batt_fixed
        pv_kw    = Float64(pv["min_kw"])
        batt_kw  = Float64(batt["min_kw"])
        batt_kwh = Float64(batt["min_kwh"])
        @info "MPC: fixed technology sizes entered, PV = $(pv_kw) kW, battery = $(batt_kw) kW / $(batt_kwh) kWh."
        return (pv_kw = pv_kw, batt_kw = batt_kw, batt_kwh = batt_kwh, skip_mpc = false)
    end

    @info "MPC: PV and/or ElectricStorage sizes are not specified — running REopt sizing first."
    sizing_post = deepcopy(d)

    # Delete inputs specific to the heuristic battery dispatch run
    if haskey(sizing_post, "ElectricStorage")
        delete!(sizing_post["ElectricStorage"], "dispatch_strategy")
        delete!(sizing_post["ElectricStorage"], "fixed_soc_series_fraction")
    end

    # TODO: Avoid redefining defaults here?
    settings = get(sizing_post, "Settings", Dict())
    sizing_solver_name = get(settings, "solver_name", "HiGHS")
    sizing_timeout     = Float64(get(settings, "timeout_seconds", 420))
    sizing_opt_tol     = Float64(get(settings, "optimality_tolerance", 0.001))

    solver_attributes = SolverAttributes(sizing_timeout, sizing_opt_tol)
    m = get_solver_model(get_solver_model_type(sizing_solver_name), solver_attributes)

    # Delete Settings inputs specific to the API
    api_only_settings_keys = ("timeout_seconds", "optimality_tolerance", "run_bau")
    if haskey(sizing_post, "Settings")
        for k in api_only_settings_keys
            delete!(sizing_post["Settings"], k)
        end
        if isempty(sizing_post["Settings"])
            delete!(sizing_post, "Settings")
        end
    end

    model_inputs = reoptjl.REoptInputs(sizing_post)
    sizing_results = reoptjl.run_reopt(m, model_inputs)

    if get(sizing_results, "status", "") != "optimal"
        status = get(sizing_results, "status", "unknown")
        msgs = get(sizing_results, "Messages", Dict())
        errs = get(msgs, "errors", [])
        warns = get(msgs, "warnings", [])
        error("MPC sizing pre-step did not solve (status = $(status)). " *
              "REopt errors: $(errs). REopt warnings: $(warns).")
    end

    pv_kw    = Float64(get(get(sizing_results, "PV", Dict()), "size_kw", 0.0))
    batt_kw  = Float64(get(get(sizing_results, "ElectricStorage", Dict()), "size_kw", 0.0))
    batt_kwh = Float64(get(get(sizing_results, "ElectricStorage", Dict()), "size_kwh", 0.0))

    # Skip the MPC loop if no battery is sized
    if batt_kw <= 0.0 || batt_kwh <= 0.0
        return (pv_kw = pv_kw, batt_kw = 0.0, batt_kwh = 0.0, skip_mpc = true)
    end

    pv["min_kw"]    = pv_kw
    pv["max_kw"]    = pv_kw
    batt["min_kw"]  = batt_kw
    batt["max_kw"]  = batt_kw
    batt["min_kwh"] = batt_kwh
    batt["max_kwh"] = batt_kwh

    @info "MPC: REopt sizing solved with PV = $(pv_kw) kW and battery = $(batt_kw) kW / $(batt_kwh) kWh."
    return (pv_kw = pv_kw, batt_kw = batt_kw, batt_kwh = batt_kwh, skip_mpc = false)
end

function get_mpc_results(d::Dict; solver_name::String="HiGHS")::Dict
    """
    Run a full-year rolling-horizon MPC dispatch for PV + ElectricStorage by 
    calling `REopt.run_mpc` once per timestep with a 24-hour look-ahead.

    Inputs:
        d::Dict, REopt inputs dictionary 
        solver_name::String, solver to use ("HiGHS", "Cbc", "SCIP", or "Xpress")

    Returns a Dict with PV and BATT sizes, dispatch time series, and cost metrics
    """
    
    settings = get!(d, "Settings", Dict())
    settings["solver_name"] = solver_name

    # TODO: MPC timeout and optimality tolerance
    optimality_tolerance = Float64(get(settings, "optimality_tolerance", 0.001))

    # TODO: MPC horizons and timeout are currently hard coded
    time_steps_per_hour = Int(get(settings, "time_steps_per_hour", 1))
    length_of_data      = 8760 * time_steps_per_hour
    horizon             = 24 * time_steps_per_hour
    per_iter_timeout_s  = 30.0

    # TODO: Should MPC handle multiple PVs?
    pv               = get!(d, "PV",              Dict())
    electric_storage = get!(d, "ElectricStorage", Dict())
    electric_load    = get!(d, "ElectricLoad",    Dict())
    electric_tariff  = get(d,  "ElectricTariff",  Dict())
    electric_utility = get(d,  "ElectricUtility", Dict())

    # Read timeseries PV production factors or generate using PVWatts, save generated values to reduce PVWatts calls
    if haskey(pv, "production_factor_series") && !isempty(pv["production_factor_series"])
        pv_prod_factor = Float64.(pv["production_factor_series"])
    else
        # TODO: These production factors don't consider degradation, problem? 
        # Does MPCPV need a degradation input to calculate the levelization factor used in the optimization?
        pv_prod_factor = generate_pv_production_factors(d, time_steps_per_hour)
        pv["production_factor_series"] = pv_prod_factor
    end

    # Read timeseries electric load inputs or generate using CRBs
    if haskey(electric_load, "loads_kw") && !isempty(electric_load["loads_kw"])
        loads_kw = Float64.(electric_load["loads_kw"])
    else
        loads_kw = generate_loads_kw(d, time_steps_per_hour)

        # Previously caching to save an extra CRB call but loads_kw conflicts with other load inputs
        # electric_load["loads_kw"] = loads_kw
    end

    # Check data series lengths 
    # TODO: Do API inputs validation when calling the MPC endpoint directly? 
    # Should we even have an MPC endpoint? 
    pv_prod_factor = check_series_length("PV.production_factor_series", pv_prod_factor, length_of_data)
    loads_kw = check_series_length("ElectricLoad.loads_kw", loads_kw, length_of_data)

    # MPC requires fixed PV and battery sizes. If not provided, call REopt first in a sizing run.
    technology_sizes = get_technology_sizes!(d)

    # Skip MPC if no battery is optimally sized
    if technology_sizes.skip_mpc
        return Dict("skip_mpc" => true)
    end

    pv_kw    = technology_sizes.pv_kw
    batt_kw  = technology_sizes.batt_kw
    batt_kwh = technology_sizes.batt_kwh

    # TODO: Should these defaults be read from somewhere so that they don't have to be updated in various places?
    soc_0  = Float64(get(electric_storage, "soc_init_fraction", 0.5))
    soc_min   = Float64(get(electric_storage, "soc_min_fraction", 0.2))
    rect_eff  = Float64(get(electric_storage, "rectifier_efficiency_fraction", 0.96))
    inv_eff   = Float64(get(electric_storage, "inverter_efficiency_fraction",  0.96))
    int_eff   = Float64(get(electric_storage, "internal_efficiency_fraction",  0.975))
    charge_eff    = rect_eff * sqrt(int_eff)
    discharge_eff = inv_eff  * sqrt(int_eff)

    # Process utility rate
    year = haskey(electric_load, "year") ? Int(electric_load["year"]) : nothing
    tariff = get_tariff_inputs(electric_tariff, year, time_steps_per_hour)
    energy_rates = tariff.energy_rates
    tou_demand_rates = tariff.tou_demand_rates      
    tou_demand_ratchet_time_steps = tariff.tou_demand_ratchet_time_steps 
    monthly_demand_rates = tariff.monthly_demand_rates 

    # TODO: MPC loop cherry picked one specific emissions type - remove or keep and add others?
    # TODO: If keep, add function to pull defaults? Currently only allowing user upload
    emissions = haskey(electric_utility, "emissions_factor_series_lb_CO2_per_kwh") ?
                Float64.(electric_utility["emissions_factor_series_lb_CO2_per_kwh"]) : zeros(Float64, length_of_data)
    emissions = check_series_length("ElectricUtility.emissions_factor_series_lb_CO2_per_kwh", emissions, length_of_data)

    month_starts = get_month_transition_timesteps(time_steps_per_hour)

    # ts_to_month = 8760 array specifying which month each timestep falls in (1-12)
    ts_to_month = Vector{Int}(undef, length_of_data)
    for m in 1:12
        s = month_starts[m]
        e = m < 12 ? month_starts[m+1] - 1 : length_of_data
        ts_to_month[s:e] .= m
    end

    # ts_to_ratchet = 8760 array specifying which ratchet each timestep falls in
    ts_to_ratchet = zeros(Int, length_of_data)
    for (t, ratchet_ts) in enumerate(tou_demand_ratchet_time_steps), g in ratchet_ts
        if 1 <= g <= length_of_data
            ts_to_ratchet[g] = t
        end
    end

    # TODO: Monthly demand has never been tested
    n_tou_ratchets = length(tou_demand_rates) # Number of TOU ratchets
    tou_previous_peak_demands = zeros(Float64, n_tou_ratchets) # Tracks past TOU peak demand per ratchet
    monthly_previous_peak_demands = zeros(Float64, 12) # Tracks past monthly peak demand

    # Saved dispatch series (first timestep of each MPC loop)
    dispatch_series = Dict(
        "PV" => Dict(
            "electric_to_load_series_kw"    => Float64[],
            "electric_to_storage_series_kw" => Float64[],
            "electric_to_grid_series_kw"    => Float64[],
            "electric_curtailed_series_kw"  => Float64[],
        ),
        "ElectricStorage" => Dict(
            "storage_to_load_series_kw" => Float64[],
            "soc_series_fraction"       => Float64[],
        ),
        "ElectricUtility" => Dict(
            "electric_to_load_series_kw"    => Float64[],
            "electric_to_storage_series_kw" => Float64[],
            "emissions_series_lb_CO2"       => Float64[],
        ),
        "ElectricLoad" => Dict(
            "load_series_kw" => Float64[],
        ),
    )
    energy_cost_series = Float64[]
    total_energy_cost = 0.0
    soc_init_frac = soc_0

    # Build MPC post
    function build_mpc_post(current_horizon_pv, current_horizon_load, current_horizon_energy_rates, 
                            current_horizon_emissions, current_horizon_tou_ts, current_horizon_monthly_ts,
                            tou_previous_peak_demands, monthly_previous_peak_demands, soc_init_frac)
        return Dict(
            "PV" => Dict(
                "size_kw" => pv_kw,
                "production_factor_series" => current_horizon_pv,
            ),
            "ElectricStorage" => Dict(
                "size_kw" => batt_kw,
                "size_kwh" => batt_kwh,
                "charge_efficiency" => charge_eff,
                "discharge_efficiency" => discharge_eff,
                "soc_init_fraction" => soc_init_frac,
                "soc_min_fraction" => soc_min,
            ),
            "ElectricLoad" => Dict(
                "loads_kw" => current_horizon_load,
            ),
            "ElectricTariff" => Dict(
                "energy_rates" => current_horizon_energy_rates,
                "tou_demand_rates" => tou_demand_rates,
                "tou_demand_ratchet_time_steps" => current_horizon_tou_ts,
                "tou_previous_peak_demands" => tou_previous_peak_demands,
                "monthly_demand_rates" => monthly_demand_rates,
                "time_steps_monthly" => current_horizon_monthly_ts,
                "monthly_previous_peak_demands" => monthly_previous_peak_demands,
            ),
            "ElectricUtility" => Dict(
                "emissions_factor_series_lb_CO2_per_kwh" => current_horizon_emissions,
            ),
        )
    end

    @info "MPC: starting rolling-horizon optimization ($(length_of_data) iterations, horizon = $(horizon) timesteps)"
    for idx in 1:length_of_data
        end_ts = idx + horizon - 1

        current_horizon_pv = slice_data(pv_prod_factor, idx, end_ts)
        current_horizon_load = slice_data(loads_kw, idx, end_ts)
        current_horizon_energy_rates = slice_data(energy_rates, idx, end_ts)
        current_horizon_emissions = slice_data(emissions, idx, end_ts)

        # List of length n_tou_ratchets, specifies which ts of the current horizon are in each TOU ratchet 
        # by placing values 1 to horizon into the corresponding element of the array based on ratchet number
        current_horizon_tou_ts = [Int[] for _ in 1:n_tou_ratchets]

        # 12 element list, each element for one month of the year. Specifies which timesteps of the current horizon are 
        # in each month by placing values 1 - horizon into the corresponding element of the array based on month number
        current_horizon_monthly_ts = [Int[] for _ in 1:12]
        for k in 1:horizon
            g = idx + k - 1
            if g > length_of_data
                g -= length_of_data
            end
            push!(current_horizon_monthly_ts[ts_to_month[g]], k)
            ratchet = ts_to_ratchet[g]
            if ratchet > 0
                push!(current_horizon_tou_ts[ratchet], k)
            end
        end

        post = build_mpc_post(current_horizon_pv, current_horizon_load, current_horizon_energy_rates, 
                              current_horizon_emissions, current_horizon_tou_ts, current_horizon_monthly_ts,
                              tou_previous_peak_demands, monthly_previous_peak_demands, soc_init_frac)

        model = get_solver_model(get_solver_model_type(solver_name),
                                  SolverAttributes(per_iter_timeout_s, optimality_tolerance))
        result = reoptjl.run_mpc(model, post)

        # Assume perfect forecast; save first timestep of results as the executed state
        pv_res   = result["PV"]
        batt_res = result["ElectricStorage"]
        util_res = result["ElectricUtility"]

        pv_to_load    = pv_res["electric_to_load_series_kw"][1]
        pv_to_batt    = pv_res["electric_to_storage_series_kw"][1]
        pv_to_grid    = haskey(pv_res, "electric_to_grid_series_kw")   ? pv_res["electric_to_grid_series_kw"][1]   : 0.0
        pv_curtailed  = haskey(pv_res, "electric_curtailed_series_kw") ? pv_res["electric_curtailed_series_kw"][1] : 0.0
        batt_to_load  = batt_res["storage_to_load_series_kw"][1]
        batt_soc      = batt_res["soc_series_fraction"][1]
        util_to_load  = util_res["electric_to_load_series_kw"][1]
        util_to_batt  = util_res["electric_to_storage_series_kw"][1]
        grid_power    = max(util_to_load + util_to_batt, 0.0)

        push!(dispatch_series["PV"]["electric_to_load_series_kw"], pv_to_load)
        push!(dispatch_series["PV"]["electric_to_storage_series_kw"], pv_to_batt)
        push!(dispatch_series["PV"]["electric_to_grid_series_kw"], pv_to_grid)
        push!(dispatch_series["PV"]["electric_curtailed_series_kw"], pv_curtailed)
        push!(dispatch_series["ElectricStorage"]["storage_to_load_series_kw"], batt_to_load)
        push!(dispatch_series["ElectricStorage"]["soc_series_fraction"], batt_soc)
        push!(dispatch_series["ElectricUtility"]["electric_to_load_series_kw"], util_to_load)
        push!(dispatch_series["ElectricUtility"]["electric_to_storage_series_kw"], util_to_batt)
        push!(dispatch_series["ElectricUtility"]["emissions_series_lb_CO2"],
              emissions[idx] * grid_power / time_steps_per_hour)
        push!(dispatch_series["ElectricLoad"]["load_series_kw"], loads_kw[idx])

        # Running energy costs
        step_energy_cost = grid_power * energy_rates[idx] / time_steps_per_hour
        push!(energy_cost_series, step_energy_cost)
        total_energy_cost += step_energy_cost

        soc_init_frac = batt_soc

        # Update monthly and TOU peak demand as max(current ts grid_power, previous max)
        current_month = ts_to_month[idx]
        monthly_previous_peak_demands[current_month] = max(grid_power, monthly_previous_peak_demands[current_month])

        if n_tou_ratchets > 0
            current_ratchet = ts_to_ratchet[idx]
            if current_ratchet > 0
                tou_previous_peak_demands[current_ratchet] = max(grid_power, tou_previous_peak_demands[current_ratchet])
            end
        end

    end

    @info "MPC looping completed."

    # Calculate final demand costs 
    monthly_demand_cost_total = sum(monthly_previous_peak_demands .* monthly_demand_rates)
    tou_demand_cost_total = n_tou_ratchets > 0 ?
                            sum(tou_previous_peak_demands .* tou_demand_rates) : 0.0

    return Dict(
        "MPC" => Dict(
            "time_steps_per_hour" => time_steps_per_hour,
            "horizon" => horizon,
        ),
        "PV" => merge(Dict("size_kw" => pv_kw), dispatch_series["PV"]),
        "ElectricStorage" => merge(Dict("size_kw" => batt_kw, "size_kwh" => batt_kwh), dispatch_series["ElectricStorage"]),
        "ElectricUtility" => dispatch_series["ElectricUtility"],
        "ElectricLoad" => dispatch_series["ElectricLoad"],
        "ElectricTariff" => Dict(
            "total_energy_cost" => total_energy_cost,
            "energy_cost_series_per_timestep" => energy_cost_series,
            "total_tou_demand_cost" => tou_demand_cost_total,
            "total_monthly_demand_cost" => monthly_demand_cost_total,
            "tou_peaks_by_ratchet_kw" => tou_previous_peak_demands,
            "monthly_peaks_kw" => monthly_previous_peak_demands,
        ),
        "status" => "optimal",
        "reopt_version" => string(pkgversion(reoptjl)),
    )
end
