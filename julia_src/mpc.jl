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
This is called by get_mpc_results! only when the user does not provide a custom production_factor_series and REopt is not called for sizing.
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

function get_mpc_results!(d::Dict; solver_name::String="HiGHS")::Dict
    """
    Run a full-year rolling-horizon MPC dispatch for PV + ElectricStorage by 
    calling `REopt.run_mpc` once per timestep with a 24-hour look-ahead.

    Inputs:
        d::Dict, REopt inputs dictionary (will be modified in-place to store computed fixed sizes and PV production factors.)

    Returns JSON dictionary containing:
    - status: "optimal", "error", or "skipped"
    - reopt_version: Version of REopt.jl used
    - Messages: Dict with optional errors, warnings, or info
    - skip_heuristic_dispatch: Boolean indicating if MPC was skipped
    
    For "optimal" status, also includes:
    - MPC: Metadata (time_steps_per_hour, horizon_time_steps)
    - PV: Size and dispatch series (to load, storage, grid, curtailed)
    - ElectricStorage: Sizes and state-of-charge series
    - ElectricUtility: Grid dispatch series and emissions
    - ElectricLoad: Load profile used
    - ElectricTariff: Separate cost components (total_energy_cost, total_export_benefit,
      total_tou_demand_cost, total_non_tou_monthly_demand_cost), a combined total_electricity_bill,
      per-timestep energy/export series, and peak demands by month/ratchet

    """

    # The checks below are removed because when MPC is called through REopt, the last REopt run will error if these goals are not met. 
    # If MPC is called directly, specifying these inputs IS an issue (because they're not consdired in MPC dispatch). If the MPC endpoint becomes public, we should re-enable these checks.
    # # Error if unsupported CO2/renewable-fraction constraints are set
    # _site_input = get(d, "Site", Dict())
    # if !isnothing(get(_site_input, "CO2_emissions_reduction_min_fraction", nothing))
    #     error("MPC: Site.CO2_emissions_reduction_min_fraction is not supported in MPC runs.")
    # end
    # if get(_site_input, "include_grid_renewable_fraction_in_RE_constraints", false) == true
    #     error("MPC: Site.include_grid_renewable_fraction_in_RE_constraints is not supported in MPC runs.")
    # end
    # if get(_site_input, "include_exported_elec_emissions_in_total", true) == false
    #     error("MPC: Site.include_exported_elec_emissions_in_total = false is not supported in MPC runs.")
    # end
    # if get(_site_input, "include_exported_renewable_electricity_in_total", true) == false
    #     error("MPC: Site.include_exported_renewable_electricity_in_total = false is not supported in MPC runs.")
    # end

    # Error for off-grid runs
    if haskey(d, "Settings") && get(d["Settings"], "off_grid_flag", false) == true
        return build_dispatch_response(
            "error",
            messages = Dict("errors" => ["MPC: Off-grid runs are not currently supported in MPC."])
        )
    end

    # Error if rate tariff contains lookbacks or coincident peak charges. (These are not currently supported in MPC.)
    if (haskey(d["ElectricTariff"], "demand_lookback_months") && length(d["ElectricTariff"]["demand_lookback_months"]) > 0 ) ||
        (haskey(d["ElectricTariff"], "demand_lookback_percent") && d["ElectricTariff"]["demand_lookback_percent"] > 0) || 
        (haskey(d["ElectricTariff"], "demand_lookback_range") && d["ElectricTariff"]["demand_lookback_range"] > 0)
            return build_dispatch_response(
                "error",
                messages = Dict("errors" => ["MPC: ElectricTariff with demand lookbacks is not currently supported in MPC runs."])
            )
    end
    if haskey(d["ElectricTariff"], "coincident_peak_load_active_time_steps") && d["ElectricTariff"]["coincident_peak_load_active_time_steps"] != [Int64[]]
        return build_dispatch_response(
            "error",
            messages = Dict("errors" => ["MPC: ElectricTariff with coincident peak charges is not currently supported in MPC runs."])
        )
    end

    # TODO: show this warning only if tiered rates are detected in the tariff.
    @warn "Using MPC to determine dispatch. MPC does not model: tiered electricity rates; rates will be flattened to the first tier."

    # Restrict inputs to PV + ElectricStorage and run a REopt "optimized" sizing pass if sizes are
    # not user-fixed. This mutates `d` to fix the resulting PV/ElectricStorage sizes.
    sized = validate_and_size_pv_storage!(d; solver_name=solver_name,
                                          strategy_label="MPC (daily_foresight_optimized dispatch)")
    if sized.error !== nothing
        return sized.error
    end
    technology_sizes    = sized.technology_sizes
    model_inputs        = sized.model_inputs
    solver_settings     = sized.solver_settings
    time_steps_per_hour = sized.time_steps_per_hour

    ## Set up MPC inputs
    # TODO: MPC horizons and timeout are currently hard coded
    per_iter_timeout_s  = 30.0
    length_of_data      = 8760 * time_steps_per_hour
    horizon             = 24 * time_steps_per_hour

    s = model_inputs.s  # Access the processed Scenario struct

    # Skip MPC if no battery is optimally sized
    if technology_sizes.skip_heuristic_dispatch
        return build_dispatch_response(
            "skipped",
            skip_heuristic_dispatch = true,
            messages = Dict("info" => ["No battery was optimally sized in REopt pre-step; MPC dispatch not needed."])
        )
    end

    # Sizes from user or initial REopt run
    pv_kw    = technology_sizes.pv_kw
    batt_kw  = technology_sizes.batt_kw
    batt_kwh = technology_sizes.batt_kwh

    # Note: REoptInputs does not provide PV production factors if user doesn't specify custom values
    # PV production is NOT levelized in MPC but IS levelized in REopt. This will result in a slight mis-match.
    if !isempty(s.pvs) # Get prod factors if PV considered.
        if !isnothing(s.pvs[1].production_factor_series)
            pv_prod_factor = Float64.(s.pvs[1].production_factor_series)
        elseif technology_sizes.pv_production_factor_series !== nothing
            pv_prod_factor = Float64.(technology_sizes.pv_production_factor_series)
        else
            pv_prod_factor = generate_pv_production_factors(d, time_steps_per_hour)
        end
        # Avoid another PVWatts call in the final REopt run.
        d["PV"]["production_factor_series"] = pv_prod_factor
    else
        pv_prod_factor = zeros(Float64, length_of_data)
    end
    
    loads_kw = Float64.(s.electric_load.loads_kw)
    
    # Extract tariff inputs relevant to MPC (use first tier only if tiered rates)
    # TODO: Implement lookbacks (demand_lookback_months, demand_lookback_percent, demand_lookback_range), coincident peak charges, and handling of tiered rates here and in REopt.jl.
    energy_rates = Float64.(s.electric_tariff.energy_rates[:, 1])
    monthly_demand_rates = isempty(s.electric_tariff.monthly_demand_rates) ?
                           zeros(Float64, 12) : Float64.(s.electric_tariff.monthly_demand_rates[:, 1])
    tou_demand_rates = isempty(s.electric_tariff.tou_demand_rates) ? Float64[] : Float64.(s.electric_tariff.tou_demand_rates[:, 1])
    tou_demand_ratchet_time_steps = [Int.(v) for v in s.electric_tariff.tou_demand_ratchet_time_steps]
    n_tou_ratchets = length(tou_demand_rates) # Number of TOU ratchets
    tou_previous_peak_demands = zeros(Float64, n_tou_ratchets) # Tracks past TOU peak demand per ratchet
    monthly_previous_peak_demands = zeros(Float64, 12) # Tracks past monthly peak demand

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

    # --- Export / net metering setup (mirror the sizing-run scenario) ---
    # NEM is enabled in MPC when ElectricUtility.net_metering_limit_kw > 0.
    nm_limit_kw = Float64(s.electric_utility.net_metering_limit_kw)

    # WHL (net billing) rate: export_rates[:WHL] in the processed scenario is a negative "cost";
    # MPCElectricTariff expects a positive wholesale_rate (it negates internally).
    whl_rate_full = (:WHL in s.electric_tariff.export_bins) ?
                    -1.0 .* Float64.(s.electric_tariff.export_rates[:WHL]) : nothing

    # PV export capability comes from the processed PV struct.
    pv_can_net_meter = !isempty(s.pvs) ? Bool(s.pvs[1].can_net_meter) : false
    pv_can_wholesale = !isempty(s.pvs) ? Bool(s.pvs[1].can_wholesale) : false

    # Battery export capability comes from the processed ElectricStorage struct
    _batt_attr = s.storage.attr["ElectricStorage"]
    batt_can_net_meter = Bool(_batt_attr.can_net_meter)
    batt_can_wholesale = Bool(_batt_attr.can_wholesale)

    # NEM export is credited (approximately) at the retail energy rate; used for cost reporting below.
    nem_active = nm_limit_kw > 0 && (pv_can_net_meter || batt_can_net_meter)

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
            "storage_to_grid_series_kw" => Float64[],
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
    energy_cost_series = Float64[]      # grid purchase (energy) charges per timestep
    export_benefit_series = Float64[]   # NEM/WHL export credits per timestep (positive = revenue)
    total_energy_cost = 0.0
    total_export_benefit = 0.0
    soc_init_frac = soc_0

    # Build MPC post
    # Update this fn if mpc capabilities are updated (e.g., to support outages, multiple PVs, or more tariff inputs)
    function build_mpc_post(current_horizon_pv, current_horizon_load, current_horizon_energy_rates, 
                            current_horizon_emissions, current_horizon_tou_ts, current_horizon_monthly_ts,
                            tou_previous_peak_demands, monthly_previous_peak_demands, soc_init_frac,
                            current_horizon_whl_rate)
        tariff = Dict(
            "energy_rates" => current_horizon_energy_rates,
            "tou_demand_rates" => tou_demand_rates,
            "tou_demand_time_steps" => current_horizon_tou_ts,
            "tou_previous_peak_demands" => tou_previous_peak_demands,
            "monthly_demand_rates" => monthly_demand_rates,
            "time_steps_monthly" => current_horizon_monthly_ts,
            "monthly_previous_peak_demands" => monthly_previous_peak_demands,
        )
        # WHL (net billing) export: MPCElectricTariff reads a positive `wholesale_rate` and
        # builds the :WHL export bin when it is provided.
        if current_horizon_whl_rate !== nothing
            tariff["wholesale_rate"] = current_horizon_whl_rate
        end
        return Dict(
            "PV" => Dict(
                "size_kw" => pv_kw,
                "production_factor_series" => current_horizon_pv,
                "can_net_meter" => pv_can_net_meter,
                "can_wholesale" => pv_can_wholesale,
            ),
            "ElectricStorage" => Dict(
                "size_kw" => batt_kw,
                "size_kwh" => batt_kwh,
                "charge_efficiency" => charge_eff,
                "discharge_efficiency" => discharge_eff,
                "soc_init_fraction" => soc_init_frac,
                "soc_min_fraction" => soc_min,
                "can_net_meter" => batt_can_net_meter,
                "can_wholesale" => batt_can_wholesale,
            ),
            "ElectricLoad" => Dict(
                "loads_kw" => current_horizon_load,
            ),
            "ElectricTariff" => tariff,
            # net_metering_limit_kw drives the NEM export bin in MPCElectricTariff (NEM on if > 0)
            "ElectricUtility" => Dict(
                "net_metering_limit_kw" => nm_limit_kw,
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
        current_horizon_whl_rate = whl_rate_full === nothing ? nothing : slice_data(whl_rate_full, idx, end_ts)

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
                              tou_previous_peak_demands, monthly_previous_peak_demands, soc_init_frac,
                              current_horizon_whl_rate
                              )

        model = get_solver_model(get_solver_model_type(solver_name),
                                  SolverAttributes(per_iter_timeout_s, solver_settings["optimality_tolerance"]))
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
        batt_to_grid  = haskey(batt_res, "storage_to_grid_series_kw") ? batt_res["storage_to_grid_series_kw"][1] : 0.0
        batt_soc      = batt_res["soc_series_fraction"][1]
        util_to_load  = util_res["electric_to_load_series_kw"][1]
        util_to_batt  = util_res["electric_to_storage_series_kw"][1]
        grid_power    = max(util_to_load + util_to_batt, 0.0)

        push!(dispatch_series["PV"]["electric_to_load_series_kw"], pv_to_load)
        push!(dispatch_series["PV"]["electric_to_storage_series_kw"], pv_to_batt)
        push!(dispatch_series["PV"]["electric_to_grid_series_kw"], pv_to_grid)
        push!(dispatch_series["PV"]["electric_curtailed_series_kw"], pv_curtailed)
        push!(dispatch_series["ElectricStorage"]["storage_to_load_series_kw"], batt_to_load)
        push!(dispatch_series["ElectricStorage"]["storage_to_grid_series_kw"], batt_to_grid)
        push!(dispatch_series["ElectricStorage"]["soc_series_fraction"], batt_soc)
        push!(dispatch_series["ElectricUtility"]["electric_to_load_series_kw"], util_to_load)
        push!(dispatch_series["ElectricUtility"]["electric_to_storage_series_kw"], util_to_batt)
        push!(dispatch_series["ElectricUtility"]["emissions_series_lb_CO2"],
              co2_grid_emissions_series[idx] * grid_power / time_steps_per_hour)
        push!(dispatch_series["ElectricLoad"]["load_series_kw"], loads_kw[idx])

        # Running electricity costs (reported as separate components; see results below)
        # Energy (grid purchase) charge for this timestep
        step_energy_charge = grid_power * energy_rates[idx] / time_steps_per_hour

        # Export credit for this timestep. NEM credits at the retail energy rate; otherwise WHL credits
        # at the wholesale rate. NOTE: when both NEM and WHL are available the model chooses per horizon
        # and the executed-timestep bin split is not returned, so this can misprice such timesteps.
        step_export_kw = pv_to_grid + batt_to_grid
        export_rate_idx = nem_active ? energy_rates[idx] :
                          (whl_rate_full !== nothing ? whl_rate_full[idx] : 0.0)
        step_export_benefit = step_export_kw * export_rate_idx / time_steps_per_hour

        push!(energy_cost_series, step_energy_charge)
        push!(export_benefit_series, step_export_benefit)
        total_energy_cost += step_energy_charge
        total_export_benefit += step_export_benefit

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

    return build_dispatch_response(
        "optimal",
        result_dict = Dict(
            "MPC" => Dict(
                "time_steps_per_hour" => time_steps_per_hour,
                "horizon_time_steps" => horizon,
            ),
            "PV" => merge(Dict("size_kw" => pv_kw), dispatch_series["PV"]),
            "ElectricStorage" => merge(Dict("size_kw" => batt_kw, "size_kwh" => batt_kwh), dispatch_series["ElectricStorage"]),
            "ElectricUtility" => dispatch_series["ElectricUtility"],
            "ElectricLoad" => dispatch_series["ElectricLoad"],
            "ElectricTariff" => Dict(
                # --- Cost components (before tax); combine for the total bill below ---
                "total_energy_cost"                   => total_energy_cost,   # grid purchases (energy) only
                "total_export_benefit"                => total_export_benefit,  # NEM/WHL credits (positive = revenue)
                "total_tou_demand_cost"               => tou_demand_cost_total,
                "total_non_tou_monthly_demand_cost"   => monthly_demand_cost_total,
                # --- Total electricity bill = energy charge - export benefit + demand charges ---
                "total_electricity_bill"              => total_energy_cost - total_export_benefit +
                                                         tou_demand_cost_total + monthly_demand_cost_total,
                "energy_cost_series_per_timestep"     => energy_cost_series,
                "export_benefit_series_per_timestep"  => export_benefit_series,
                "tou_peaks_by_ratchet_kw"             => tou_previous_peak_demands,
                "monthly_peaks_kw"                    => monthly_previous_peak_demands, # Optimal peaks (whereas REopt's ElectricLoad.monthly_peaks_kw is BAU peaks)
            ),
        )
    )
end
