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
    generate_pv_production_factors(d, time_steps_per_hour)

Generate a PV production factor series using PVWatts by calling REopt.get_production_factor.
This is called by get_mpc_results only when the user does not provide a custom production_factor_series.
"""
function generate_pv_production_factors(d::Dict, time_steps_per_hour::Int)
    site = get(d, "Site", Dict())
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
    get_technology_sizes!(d)

Determine PV and ElectricStorage sizes for the MPC loop. If min_kw != max_kw and/or min_kwh != max_kwh,
call REopt to size technologies. User input battery sizes must also be greater than zero.
"""
function get_technology_sizes!(d::Dict; solver_name::String="HiGHS")
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

    # Check if both PV and BESS sizes fixed
    pv_fixed   = is_fixed(pv,   "min_kw",  "max_kw")
    batt_fixed = is_fixed(batt, "min_kw",  "max_kw") &&
                 is_fixed(batt, "min_kwh", "max_kwh")

    if pv_fixed && batt_fixed
        pv_kw    = Float64(pv["min_kw"])
        batt_kw  = Float64(batt["min_kw"])
        batt_kwh = Float64(batt["min_kwh"])
        return (pv_kw = pv_kw, batt_kw = batt_kw, batt_kwh = batt_kwh, skip_mpc = false)
    end

    @info "MPC: PV and/or ElectricStorage sizes are not specified — running REopt sizing first."
    sizing_post = deepcopy(d)

    # Delete inputs specific to the heuristic battery dispatch run
    if haskey(sizing_post, "ElectricStorage")
        delete!(sizing_post["ElectricStorage"], "dispatch_strategy")
        delete!(sizing_post["ElectricStorage"], "fixed_soc_series_fraction")
    end

    # TODO: Should we "remove tiers" here for sizing or allow for optimizing with tiers? 

    settings = get(sizing_post, "Settings", Dict())
    delete!(settings, "run_bau")  # Remove run_bau from sizing run
    timeout_seconds = pop!(settings, "timeout_seconds", 420)
	optimality_tolerance = pop!(settings, "optimality_tolerance", 0.001)
    solver_attributes = SolverAttributes(timeout_seconds, optimality_tolerance)
    
    m = get_solver_model(get_solver_model_type(solver_name), solver_attributes)

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
    pv_production_factor_series = get(get(sizing_results, "PV", Dict()), "production_factor_series", nothing)

    # Skip the MPC loop if no battery is sized
    if batt_kw <= 0.0 || batt_kwh <= 0.0
        return (pv_kw = pv_kw, batt_kw = 0.0, batt_kwh = 0.0, skip_mpc = true, pv_production_factor_series = pv_production_factor_series)
    end

    println(pv_kw, batt_kw, batt_kwh)

    # Fix inputs for final REopt run in http.jl
    pv["min_kw"]    = pv_kw
    pv["max_kw"]    = pv_kw
    pv["production_factor_series"] = pv_production_factor_series
    batt["min_kw"]  = batt_kw
    batt["max_kw"]  = batt_kw
    batt["min_kwh"] = batt_kwh
    batt["max_kwh"] = batt_kwh

    @info "MPC: REopt sizing solved with PV = $(pv_kw) kW and battery = $(batt_kw) kW / $(batt_kwh) kWh."
    return (; pv_kw, batt_kw, batt_kwh, skip_mpc = false, pv_production_factor_series)
end

function get_mpc_results(d::Dict; solver_name::String="HiGHS")::Dict
    """
    Run a full-year rolling-horizon MPC dispatch for PV + ElectricStorage by 
    calling `REopt.run_mpc` once per timestep with a 24-hour look-ahead.

    Inputs:
        d::Dict, REopt inputs dictionary

    Returns JSON dictionary containing:
    - MPC: Metadata (time_steps_per_hour, horizon_time_steps)
    - PV: Size and dispatch series (to load, storage, grid, curtailed)
    - ElectricStorage: Sizes and state-of-charge series
    - ElectricUtility: Grid dispatch series and emissions
    - ElectricLoad: Load profile used
    - ElectricTariff: Energy and demand costs, peak demands by month/ratchet
    - status: "optimal"
    - reopt_version: Version of REopt.jl used

    """

    ## Validation on allowable inputs for MPC ##
    # Error if any techs other than PV and ElectricStorage are provided
    mpc_allowed_keys = Set(["PV", "ElectricStorage", "ElectricLoad", "ElectricTariff", "ElectricUtility", "Site", "Settings", "Financial"])
    unsupported_keys = setdiff(keys(d), mpc_allowed_keys)
    if !isempty(unsupported_keys)
        error("When using MPC (daily_foresight_optimized dispatch), only PV and ElectricStorage are supported technologies. " *
              "Unsupported inputs found: $(join(unsupported_keys, ", ")).")
    end

    # Error if unsupported CO2/renewable-fraction constraints are set
    _site_input = get(d, "Site", Dict())
    if !isnothing(get(_site_input, "CO2_emissions_reduction_min_fraction", nothing))
        error("MPC: Site.CO2_emissions_reduction_min_fraction is not supported in MPC runs.")
    end
    if get(_site_input, "include_grid_renewable_fraction_in_RE_constraints", false) == true
        error("MPC: Site.include_grid_renewable_fraction_in_RE_constraints is not supported in MPC runs.")
    end
    if get(_site_input, "include_exported_elec_emissions_in_total", true) == false
        error("MPC: Site.include_exported_elec_emissions_in_total = false is not supported in MPC runs.")
    end
    if get(_site_input, "include_exported_renewable_electricity_in_total", true) == false
        error("MPC: Site.include_exported_renewable_electricity_in_total = false is not supported in MPC runs.")
    end

    # TODO: Add warnings for REopt inputs and scenarios that are not modeled in MPC (e.g., coincident peak charges, demand lookback, etc.)
    @warn "Using MPC to determine dispatch. MPC does not model: tiered electricity rates; rates will be flattened to the first tier."

    # TODO: Test with outage inputs before enabling this warning. 
    # # Warning for outage inputs (MPC does not model outages)
    # _utility_input = get(d, "ElectricUtility", Dict())
    # if any(k -> haskey(_utility_input, k), ("outage_start_time_step", "outage_start_time_steps", "outage_durations"))
    #     @warn "MPC: Outage inputs detected (outage_start_time_step, outage_start_time_steps, outage_durations). " *
    #           "MPC does not model outages; these inputs will be ignored."
    # end

    ## Set up MPC inputs ##
    settings = get!(d, "Settings", Dict())
    settings["solver_name"] = solver_name

    # TODO: MPC timeout and optimality tolerance
    optimality_tolerance = Float64(get(settings, "optimality_tolerance", 0.001))

    # TODO: MPC horizons and timeout are currently hard coded
    time_steps_per_hour = Int(get(settings, "time_steps_per_hour", 1))
    length_of_data      = 8760 * time_steps_per_hour
    horizon             = 24 * time_steps_per_hour
    per_iter_timeout_s  = 30.0

    # Process and validate inputs using REoptInputs
    try
        model_inputs = reoptjl.REoptInputs(d)
        @info "Successfully processed REopt inputs."
    catch e
        @error "Something went wrong during REopt inputs processing!" exception=(e, catch_backtrace())
        error_response["error"] = sprint(showerror, e)
    end

    s = model_inputs.s  # Access the processed Scenario struct

    # MPC requires fixed PV and battery sizes. If not provided, call REopt first in a sizing run.
    technology_sizes = get_technology_sizes!(d)

    # Skip MPC if no battery is optimally sized
    if technology_sizes.skip_mpc
        return Dict("skip_mpc" => true)
    end

    # Note: REoptInputs does not provide PV production factors if user doesn't specify custom values
    if !isempty(s.pvs[1].production_factor_series)
        pv_prod_factor = Float64.(s.pvs[1].production_factor_series)
    elseif technology_sizes.pv_production_factor_series !== nothing
        pv_prod_factor = Float64.(technology_sizes.pv_production_factor_series)
    else
        # TODO: These production factors don't consider degradation, problem? 
        # Does MPCPV need a degradation input to calculate the levelization factor used in the optimization?
        pv_prod_factor = generate_pv_production_factors(d, time_steps_per_hour)
    end
    
    loads_kw = Float64.(s.electric_load.loads_kw)
    
    # Extract tariff inputs relevant to MPC (use first tier only if tiered rates)
    # TODO: Are all of these relevant? Any missing inputs? 
    # TODO: Implement lookback? (demand_lookback_months, demand_lookback_percent, demand_lookback_range) Ignoring coincident peak charges for now
    # TODO: Need to think through NEM or passing back export values (wholesale_rate, export_rate_beyond_net_metering_limit)
    # TODO: Track lookback variables - demand_lookback_months, demand_lookback_percent, demand_lookback_range?
    energy_rates = Float64.(s.electric_tariff.energy_rates[:, 1])
    monthly_demand_rates = isempty(s.electric_tariff.monthly_demand_rates) ?
                           zeros(Float64, 12) : Float64.(s.electric_tariff.monthly_demand_rates[:, 1])
    tou_demand_rates = isempty(s.electric_tariff.tou_demand_rates) ? Float64[] : Float64.(s.electric_tariff.tou_demand_rates[:, 1])
    tou_demand_ratchet_time_steps = [Int.(v) for v in s.electric_tariff.tou_demand_ratchet_time_steps]

    # Extract storage efficiency and SOC defaults from processed inputs
    rect_eff  = Float64(s.storage.attr["ElectricStorage"].rectifier_efficiency_fraction)
    inv_eff   = Float64(s.storage.attr["ElectricStorage"].inverter_efficiency_fraction)
    int_eff   = Float64(s.storage.attr["ElectricStorage"].internal_efficiency_fraction)
    charge_eff    = rect_eff * sqrt(int_eff)
    discharge_eff = inv_eff  * sqrt(int_eff)
    soc_0   = Float64(s.storage.attr["ElectricStorage"].soc_init_fraction)
    soc_min = Float64(s.storage.attr["ElectricStorage"].soc_min_fraction)

    # Extract emissions defaults (or use user input if provided)
    co2_grid_emissions_series = Float64.(s.electric_utility.emissions_factor_series_lb_CO2_per_kwh)

    pv_kw    = technology_sizes.pv_kw
    batt_kw  = technology_sizes.batt_kw
    batt_kwh = technology_sizes.batt_kwh

    month_starts = get_month_transition_timesteps(time_steps_per_hour)

    # ts_to_month = 8760 array specifying which month each timestep falls in (1-12)
    ts_to_month = Vector{Int}(undef, length_of_data)
    for m in 1:12
        s_idx = month_starts[m]
        e = m < 12 ? month_starts[m+1] - 1 : length_of_data
        ts_to_month[s_idx:e] .= m
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
        current_horizon_emissions = slice_data(co2_grid_emissions_series, idx, end_ts)

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
              co2_grid_emissions_series[idx] * grid_power / time_steps_per_hour)
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
            "horizon_time_steps" => horizon,
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
