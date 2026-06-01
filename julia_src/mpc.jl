# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
# ============================================================================
# MPC (Model Predictive Control) endpoint
# ----------------------------------------------------------------------------
# Rolling-horizon dispatch with one day look-ahead using REopt.run_mpc. Assumes:
#   * PV and ElectricStorage are the only available technologies (perfect forecast)
#   * Only perfect forecast scenarios are modeled (no forecast errors)
#   * Sizing: Perform a sizing run first if PV or ElectricStorage sizes are not provided (storage sizes must be greater than zero)
#   * PV: Use PVWatts if `PV.production_factor_series` is not provided
#   * ElectricLoad: Use commercial reference profiles if `ElectricLoad.loads_kw` is not provided
#   * Code currently wraps with Jan 1 data to determine Dec 31 dispatch (allows leap-year data, which avoids the need to wrap)
#   * MPC settings are currently hard coded (e.g., forecast horizon, control horizon, optimization horizon)
# ============================================================================

"""
    get_month_transition_timesteps(time_steps_per_hour)

Return the 1-based timestep index marking the START of each month for a
non-leap year beginning Jan 1 00:00. Length 12; first element == 1.
The last "transition" (end of December) is implicitly `length_of_data + 1`
and is handled by the caller.
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
    _mpc_slice_with_wrap(arr, idx, end_idx)

Return `arr[idx:end_idx]` but wrap around to the start of `arr` if
`end_idx > length(arr)`. The wrap threshold is the actual array length,
not `length_of_data`, so a leap-year-length input (8784*tsh) naturally
supplies the extra day for the year-end look-ahead window before any
wrap is needed.
"""
function _mpc_slice_with_wrap(arr::AbstractVector, idx::Int, end_idx::Int)
    n = length(arr)
    if end_idx <= n
        return arr[idx:end_idx]
    else
        wrap_len = end_idx - n
        return vcat(arr[idx:n], arr[1:wrap_len])
    end
end

"""
    _mpc_check_series_length(name, series, time_steps_per_hour, length_of_data)

Validate that a user-supplied annual time series has either
`8760 * time_steps_per_hour` entries (standard year) or
`8784 * time_steps_per_hour` entries (leap year). Returns the series
unchanged.

The MPC loop iterates over `length_of_data = 8760 * time_steps_per_hour`
timesteps; if a leap-year-length series is supplied, the extra day is
used as additional look-ahead data by `_mpc_slice_with_wrap` (which wraps
on the actual array length, not on `length_of_data`). Any other length is
a hard error — REopt.jl's own `check_and_adjust_load_length` would
silently repeat/pad, masking the mistake.
"""
function _mpc_check_series_length(name::String, series::AbstractVector,
                                  time_steps_per_hour::Int, length_of_data::Int)
    n = length(series)
    n == length_of_data && return series
    if n == 8784 * time_steps_per_hour
        @info "MPC: $name has leap-year length ($n); the extra day will be used " *
              "for year-end look-ahead instead of wrapping to Jan 1."
        return series
    end
    # Diagnostic: if `n` is consistent with 8760 hours at a *different*
    # sub-hourly resolution, the user probably mis-declared
    # `Settings.time_steps_per_hour`.
    tsh_hint = ""
    for tsh_guess in (1, 2, 4)
        tsh_guess == time_steps_per_hour && continue
        if n == 8760 * tsh_guess || n == 8784 * tsh_guess
            tsh_hint = " (length is consistent with time_steps_per_hour=$(tsh_guess); " *
                       "check Settings.time_steps_per_hour)."
            break
        end
    end
    error("MPC: $name length $n != " *
          "8760 * time_steps_per_hour ($length_of_data) " *
          "and != 8784 * time_steps_per_hour ($(8784 * time_steps_per_hour))." *
          tsh_hint)
end

"""
    _mpc_build_tariff_arrays(et_input, year, time_steps_per_hour, length_of_data)

Construct a `REopt.ElectricTariff` from the user's ElectricTariff input dict
(which uses the real REopt input schema: `urdb_label`, `urdb_response`,
`urdb_utility_name`+`urdb_rate_name`, `tou_energy_rates_per_kwh`,
`monthly_energy_rates`, `monthly_demand_rates`, `blended_annual_energy_rate`,
`blended_annual_demand_rate`, etc.) and extract the processed arrays MPC
needs for its per-window posts.

Returns a NamedTuple with:
  * `energy_rates::Vector{Float64}` (length `length_of_data`)
  * `monthly_demand_rates::Vector{Float64}` (length 12, all zeros if not set)
  * `tou_demand_rates::Vector{Float64}` (one per ratchet; empty for non-URDB)
  * `tou_demand_time_steps::Vector{Vector{Int}}` (full-year indices per ratchet)

Multi-tier rates are flattened to a single tier (MPC does not model tiers).
"""
function _mpc_build_tariff_arrays(et_input::Dict, year::Union{Int,Nothing},
                                   time_steps_per_hour::Int, length_of_data::Int)
    # Only forward known ElectricTariff kwargs so unrelated keys (e.g. a
    # parsed API artifact) don't trip the constructor.
    known_kwargs = (:urdb_label, :urdb_response, :urdb_utility_name,
                    :urdb_rate_name, :urdb_metadata,
                    :wholesale_rate, :export_rate_beyond_net_metering_limit,
                    :monthly_energy_rates, :monthly_demand_rates,
                    :blended_annual_energy_rate, :blended_annual_demand_rate,
                    :add_monthly_rates_to_urdb_rate,
                    :tou_energy_rates_per_kwh, :add_tou_energy_rates_to_urdb_rate,
                    :remove_tiers, :demand_lookback_months,
                    :demand_lookback_percent, :demand_lookback_range,
                    :coincident_peak_load_active_time_steps,
                    :coincident_peak_load_charge_per_kw)
    kwargs = Dict{Symbol,Any}(Symbol(k) => v for (k, v) in et_input
                              if Symbol(k) in known_kwargs)
    # Force single-tier arrays so MPC sees a flat schedule; without this the
    # constructor could return `length_of_data x n_tiers` and we'd silently
    # only use one tier (and inconsistently across energy vs demand).
    kwargs[:remove_tiers] = get(kwargs, :remove_tiers, true)

    tariff = reoptjl.ElectricTariff(; year = year,
                                      time_steps_per_hour = time_steps_per_hour,
                                      kwargs...)

    # All arrays are single-tier (we forced `remove_tiers=true`).
    energy_rates = vec(Float64.(tariff.energy_rates[:, 1]))
    length(energy_rates) == length_of_data || error(
        "MPC: derived energy_rates length $(length(energy_rates)) != length_of_data $(length_of_data).")

    monthly_demand_rates = isempty(tariff.monthly_demand_rates) ?
        zeros(Float64, 12) : vec(Float64.(tariff.monthly_demand_rates[:, 1]))
    length(monthly_demand_rates) == 12 || error(
        "MPC: derived monthly_demand_rates length $(length(monthly_demand_rates)) != 12.")

    tou_demand_rates = isempty(tariff.tou_demand_rates) ?
        Float64[] : vec(Float64.(tariff.tou_demand_rates[:, 1]))
    tou_demand_time_steps = [Int.(v) for v in tariff.tou_demand_ratchet_time_steps]

    return (energy_rates = energy_rates,
            monthly_demand_rates = monthly_demand_rates,
            tou_demand_rates = tou_demand_rates,
            tou_demand_time_steps = tou_demand_time_steps)
end

"""
    _mpc_generate_pv_production_factor(d, time_steps_per_hour)

Derive a PV production factor series via `REopt.get_production_factor`
(PVWatts) using `Site.latitude`/`Site.longitude` and the PV inputs in `d`.
Returns a `Vector{Float64}`. Throws if lat/lon are missing.
"""
function _mpc_generate_pv_production_factor(d::Dict, time_steps_per_hour::Int)
    site = get(d, "Site", Dict())
    haskey(site, "latitude")  || error(
        "MPC: Site.latitude is required to derive PV.production_factor_series via PVWatts.")
    haskey(site, "longitude") || error(
        "MPC: Site.longitude is required to derive PV.production_factor_series via PVWatts.")
    lat = Float64(site["latitude"])
    lon = Float64(site["longitude"])

    @info "MPC: PV.production_factor_series not provided; deriving via REopt.jl PVWatts (lat=$(lat), lon=$(lon))."

    # Only forward known REopt.PV kwargs that affect the production factor.
    pv = get(d, "PV", Dict())
    pv_pf_kwargs = (:array_type, :tilt, :module_type, :losses, :azimuth, :gcr,
                    :radius, :name, :location, :dc_ac_ratio, :inv_eff)
    kwargs = Dict{Symbol,Any}(Symbol(k) => v for (k, v) in pv
                              if Symbol(k) in pv_pf_kwargs)
    pv_struct = reoptjl.PV(; latitude = lat, kwargs...)
    derived = reoptjl.get_production_factor(pv_struct, lat, lon;
                                            time_steps_per_hour = time_steps_per_hour)
    return collect(Float64.(derived))
end

"""
    _mpc_generate_loads_kw(d, time_steps_per_hour)

Derive an electric load profile via `REopt.ElectricLoad` from the user's
standard ElectricLoad inputs (`doe_reference_name`+`city` /
`blended_doe_reference_names`+`blended_doe_reference_percents`,
`annual_kwh`, `monthly_totals_kwh`, `monthly_peaks_kw`, `year`, etc.) —
the same DOE CRB derivation path the main REopt run would take. Returns a
`Vector{Float64}`. Requires `Site.latitude`/`Site.longitude`.
"""
function _mpc_generate_loads_kw(d::Dict, time_steps_per_hour::Int)
    site = get(d, "Site", Dict())
    haskey(site, "latitude")  || error(
        "MPC: Site.latitude is required to derive ElectricLoad.loads_kw from a DOE CRB profile.")
    haskey(site, "longitude") || error(
        "MPC: Site.longitude is required to derive ElectricLoad.loads_kw from a DOE CRB profile.")
    lat = Float64(site["latitude"])
    lon = Float64(site["longitude"])

    @info "MPC: ElectricLoad.loads_kw not provided; deriving via REopt.jl ElectricLoad (lat=$(lat), lon=$(lon))."

    # Only forward known ElectricLoad kwargs.
    eload = get(d, "ElectricLoad", Dict())
    known_kwargs = (:normalize_and_scale_load_profile_input,
                    :path_to_csv, :doe_reference_name,
                    :blended_doe_reference_names, :blended_doe_reference_percents,
                    :year, :city, :annual_kwh, :monthly_totals_kwh,
                    :monthly_peaks_kw, :critical_loads_kw, :loads_kw_is_net,
                    :critical_loads_kw_is_net, :critical_load_fraction,
                    :operating_reserve_required_fraction,
                    :min_load_met_annual_fraction, :off_grid_flag)
    kwargs = Dict{Symbol,Any}(Symbol(k) => v for (k, v) in eload
                              if Symbol(k) in known_kwargs)
    load_struct = reoptjl.ElectricLoad(; latitude = lat, longitude = lon,
                                         time_steps_per_hour = time_steps_per_hour,
                                         kwargs...)
    return collect(Float64.(load_struct.loads_kw))
end

"""
    _mpc_resolve_sizes!(d)

Determines PV/ElectricStorage sizes for the MPC loop, using the actual
REopt input schema (`min_kw`/`max_kw`, `min_kwh`/`max_kwh`).

Rules:
  * If `min_kw == max_kw` for PV AND `min_kw == max_kw` AND
    `min_kwh == max_kwh` for ElectricStorage → sizes are already fixed; use
    those values directly. No sizing run.
  * Otherwise → run a regular REopt sizing optimization, then mutate `d` to
    set `min_kw = max_kw = sized_kw` (and similarly for kWh on storage).
    Locking sizes in `d` ensures the downstream main REopt run uses the
    same sizes the MPC SOC trajectory was computed against.

Returns the tuple `(pv_kw, bess_kw, bess_kwh)` for the caller to use when
building per-window MPC posts.
"""
function _mpc_resolve_sizes!(d::Dict)
    pv   = get!(d, "PV", Dict())
    bess = get!(d, "ElectricStorage", Dict())

    function _is_fixed(dct, lo_key, hi_key)
        lo = get(dct, lo_key, nothing)
        hi = get(dct, hi_key, nothing)
        return lo !== nothing && hi !== nothing && Float64(lo) == Float64(hi)
    end

    # Guard: daily_foresight_optimized requires a non-zero ElectricStorage.
    # If the user has pinned kW or kWh to zero (min == max == 0), fail fast
    # with a clear message instead of running a pointless sizing/MPC pass.
    if (_is_fixed(bess, "min_kw",  "max_kw")  && Float64(get(bess, "min_kw",  0)) == 0.0) ||
       (_is_fixed(bess, "min_kwh", "max_kwh") && Float64(get(bess, "min_kwh", 0)) == 0.0)
        error("ElectricStorage power (kW) and energy (kWh) must both be greater than zero to run the daily_foresight_optimized dispatch option. Got min_kw=$(get(bess, "min_kw", nothing)), max_kw=$(get(bess, "max_kw", nothing)), min_kwh=$(get(bess, "min_kwh", nothing)), max_kwh=$(get(bess, "max_kwh", nothing)).")
    end

    pv_fixed   = _is_fixed(pv,   "min_kw",  "max_kw")
    bess_fixed = _is_fixed(bess, "min_kw",  "max_kw") &&
                 _is_fixed(bess, "min_kwh", "max_kwh")

    if pv_fixed && bess_fixed
        pv_kw    = Float64(pv["min_kw"])
        bess_kw  = Float64(bess["min_kw"])
        bess_kwh = Float64(bess["min_kwh"])
        @info "MPC: sizes already fixed via min_kw==max_kw. PV=$(pv_kw) kW, BESS=$(bess_kw) kW / $(bess_kwh) kWh."
        return (pv_kw = pv_kw, bess_kw = bess_kw, bess_kwh = bess_kwh)
    end

    @info "MPC: PV and/or ElectricStorage sizes not fixed — running REopt sizing first."
    sizing_post = deepcopy(d)
    # Strip any API-only sentinels before sizing.
    if haskey(sizing_post, "ElectricStorage")
        delete!(sizing_post["ElectricStorage"], "dispatch_options")
        delete!(sizing_post["ElectricStorage"], "fixed_soc_series_fraction")
    end
    settings = get!(sizing_post, "Settings", Dict())
    settings["run_bau"] = false
    settings["solver_name"] = get(settings, "solver_name", "HiGHS")
    settings["timeout_seconds"] = get(settings, "timeout_seconds", 420)
    settings["optimality_tolerance"] = get(settings, "optimality_tolerance", 0.001)

    solver_attributes = SolverAttributes(
        settings["timeout_seconds"], settings["optimality_tolerance"])
    m = get_solver_model(get_solver_model_type(settings["solver_name"]), solver_attributes)

    model_inputs = reoptjl.REoptInputs(sizing_post)
    sizing_results = reoptjl.run_reopt(m, model_inputs)

    if get(sizing_results, "status", "") != "optimal"
        error("MPC sizing pre-step did not solve to optimality (status = $(get(sizing_results, "status", "unknown"))).")
    end

    pv_kw    = Float64(get(get(sizing_results, "PV", Dict()), "size_kw", 0.0))
    bess_kw  = Float64(get(get(sizing_results, "ElectricStorage", Dict()), "size_kw", 0.0))
    bess_kwh = Float64(get(get(sizing_results, "ElectricStorage", Dict()), "size_kwh", 0.0))

    # Lock the resolved sizes in `d` so the downstream main REopt run uses
    # the SAME sizes that the MPC SOC trajectory is consistent with.
    pv["min_kw"]    = pv_kw
    pv["max_kw"]    = pv_kw
    bess["min_kw"]  = bess_kw
    bess["max_kw"]  = bess_kw
    bess["min_kwh"] = bess_kwh
    bess["max_kwh"] = bess_kwh

    @info "MPC: sized PV=$(pv_kw) kW, BESS=$(bess_kw) kW / $(bess_kwh) kWh (locked into d via min==max)."
    return (pv_kw = pv_kw, bess_kw = bess_kw, bess_kwh = bess_kwh)
end

# Core MPC computation. Takes the already-parsed (and api-key-stripped) request
# dict `d` and returns the results dict (dispatch series, costs, etc.).
# May throw; callers handle error responses.
# Called by both /mpc (standalone) and /reopt (when dispatch_options =
# "daily_foresight_optimized").
function get_mpc_results(d::Dict)::Dict
    # ---- Shared settings (with sensible defaults) ----
    settings = get(d, "Settings", Dict())
    solver_name = get(settings, "solver_name", "HiGHS")
    if solver_name == "Xpress" && xpress_installed != "True"
        solver_name = "HiGHS"
        @warn "Changing solver_name from Xpress to $solver_name because Xpress is not installed. " *
              "Next time specify Settings.solver_name = 'HiGHS' or 'Cbc' or 'SCIP'."
    end

    optimality_tolerance = Float64(get(settings, "optimality_tolerance", 0.001))

    # ---- Hard-coded MPC config ----
    # Full-year, 24-h horizon, year-end wrap-around, 60 s/iter solver cap.
    time_steps_per_hour = Int(get(settings, "time_steps_per_hour", 1))
    length_of_data      = 8760 * time_steps_per_hour
    horizon             = 24 * time_steps_per_hour
    per_iter_timeout_s  = 60.0

    # ---- Guarantee presence of the tech / load sub-dicts ----
    # Done up front so PV/load resolution and sizing can mutate them in
    # place, and downstream code can use plain indexing.
    pv    = get!(d, "PV",              Dict())
    bess  = get!(d, "ElectricStorage", Dict())
    eload = get!(d, "ElectricLoad",    Dict())
    et    = get(d,  "ElectricTariff",  Dict())
    eutil = get(d,  "ElectricUtility", Dict())

    # ---- Resolve PV production factor series ----
    # If not user-provided, derive via REopt.jl PVWatts and cache into `d`
    # so both the sizing pre-step and downstream main REopt run reuse it
    # without a second PVWatts call.
    pv_prod_factor = if haskey(pv, "production_factor_series") && !isempty(pv["production_factor_series"])
        # Broadcast-convert: handles Vector{Any} from JSON parsing
        # (convert(Vector{Float64}, ::Vector{Any}) would throw).
        Float64.(pv["production_factor_series"])
    else
        series = _mpc_generate_pv_production_factor(d, time_steps_per_hour)
        pv["production_factor_series"] = series
        series
    end

    # ---- Resolve electric load series ----
    # Mirror the PV pattern: if user-provided, use it; else derive via
    # REopt.jl ElectricLoad (DOE CRB path) and cache into `d`.
    load_series = if haskey(eload, "loads_kw") && !isempty(eload["loads_kw"])
        Float64.(eload["loads_kw"])
    else
        series = _mpc_generate_loads_kw(d, time_steps_per_hour)
        eload["loads_kw"] = series
        series
    end

    # ---- Length checks (8760 or 8784 * tsh) ----
    # No mutation of user-supplied series. A leap-year-length input
    # (8784*tsh) is accepted as-is; `_mpc_slice_with_wrap` reads the extra
    # day from it for year-end look-ahead instead of wrapping to Jan 1.
    pv_prod_factor = _mpc_check_series_length("PV.production_factor_series",
                             pv_prod_factor, time_steps_per_hour, length_of_data)
    load_series = _mpc_check_series_length("ElectricLoad.loads_kw",
                             load_series, time_steps_per_hour, length_of_data)

    # ---- Resolve PV and ElectricStorage sizes ----
    # Runs AFTER PV/load resolution so the (possibly internal) sizing
    # REopt run reuses the cached series instead of re-deriving them.
    # Either pulls sizes from min_kw==max_kw / min_kwh==max_kwh, or runs
    # a sizing REopt and locks the resolved values into `d` so the
    # downstream main REopt run uses the SAME sizes.
    sizes = _mpc_resolve_sizes!(d)
    pv_kw    = sizes.pv_kw
    bess_kw  = sizes.bess_kw
    bess_kwh = sizes.bess_kwh

    soc_init  = Float64(get(bess, "soc_init_fraction", 0.5))
    soc_min   = Float64(get(bess, "soc_min_fraction", 0.2))
    # REopt ElectricStorage exposes three component efficiencies; MPC's
    # MPCElectricStorage uses combined charge/discharge round-trip halves.
    # Match REopt's own composition: charge = rectifier * sqrt(internal),
    # discharge = inverter * sqrt(internal). Defaults from REopt.jl.
    rect_eff = Float64(get(bess, "rectifier_efficiency_fraction", 0.96))
    inv_eff  = Float64(get(bess, "inverter_efficiency_fraction",  0.96))
    int_eff  = Float64(get(bess, "internal_efficiency_fraction",  0.975))
    charge_eff    = rect_eff * sqrt(int_eff)
    discharge_eff = inv_eff  * sqrt(int_eff)

    # Year for URDB schedule decoding is sourced from ElectricLoad.year
    # (the canonical year input in REopt; ElectricTariff's `year` kwarg is
    # an internal pass-through, not a user input).
    tariff_year = haskey(eload, "year") ? Int(eload["year"]) : nothing
    tariff = _mpc_build_tariff_arrays(et, tariff_year, time_steps_per_hour, length_of_data)
    energy_rates         = tariff.energy_rates
    tou_demand_rates     = tariff.tou_demand_rates      # one per ratchet, $/kW
    tou_demand_ts_all    = tariff.tou_demand_time_steps # full-year indices per ratchet
    monthly_demand_rates = tariff.monthly_demand_rates  # length 12, $/kW per month

    # Optional emissions series — broadcast zero if not provided.
    emissions = haskey(eutil, "emissions_factor_series_lb_CO2_per_kwh") ?
        Float64.(eutil["emissions_factor_series_lb_CO2_per_kwh"]) :
        zeros(Float64, length_of_data)
    emissions = _mpc_check_series_length("ElectricUtility.emissions_factor_series_lb_CO2_per_kwh",
                             emissions, time_steps_per_hour, length_of_data)

    # ---- Demand tracking state ----
    # Reverse indices into the calendar: each timestep maps to its
    # 1-based month (always defined) and 1-based TOU ratchet (0 if no
    # ratchet applies). Both are vector lookups (O(1)) used inside the
    # rolling-horizon loop to build window-local time-step groupings
    # and to attribute realized peaks to the right month/tier.
    month_starts = get_month_transition_timesteps(time_steps_per_hour)
    ts_to_month = Vector{Int}(undef, length_of_data)
    for m in 1:12
        s = month_starts[m]
        e = m < 12 ? month_starts[m+1] - 1 : length_of_data
        ts_to_month[s:e] .= m
    end

    ts_to_tier = zeros(Int, length_of_data)
    for (t, ratchet_ts) in enumerate(tou_demand_ts_all), g in ratchet_ts
        if 1 <= g <= length_of_data
            ts_to_tier[g] = t
        end
    end

    n_tou = length(tou_demand_rates)
    # `monthly_previous_peak_demands` and `tou_previous_peak_demands` are
    # passed into every MPC post AND mutated after each solve so that
    # subsequent windows "see" the realized peaks so far. Both reset at
    # month boundaries (matches REopt billing semantics; multi-month
    # ratchet/lookback support would require a different reset cadence).
    tou_previous_peak_demands     = zeros(Float64, n_tou)
    monthly_previous_peak_demands = zeros(Float64, 12)
    monthly_demand_cost_total = 0.0
    tou_demand_cost_total = 0.0
    tou_peaks_by_month = Vector{Vector{Float64}}()
    monthly_peaks = Float64[]

    # ---- Dispatch accumulators (1 value per executed timestep) ----
    dispatch = Dict(
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
    cost_series = Float64[]
    total_energy_cost = 0.0
    bess_soc_init_fraction = soc_init

    # ---- Build the (reused) MPC post template ----
    # Note: no Settings block here; the solver is constructed below per
    # window and passed directly to run_mpc(model, post). All four demand
    # inputs (TOU + monthly rates and previous-peak vectors) are passed
    # so the optimizer's objective accounts for *both* charges; omitting
    # `monthly_*` would silently optimize without the monthly demand
    # contribution and over-state savings under monthly-demand tariffs.
    function build_mpc_post(window_pv, window_load, window_rates, window_emissions,
                            window_tou_ts, window_monthly_ts,
                            tou_prev_peaks, monthly_prev_peaks, soc_init_frac)
        return Dict(
            "PV" => Dict(
                "size_kw" => pv_kw,
                "production_factor_series" => window_pv,
            ),
            "ElectricStorage" => Dict(
                "size_kw" => bess_kw,
                "size_kwh" => bess_kwh,
                "charge_efficiency" => charge_eff,
                "discharge_efficiency" => discharge_eff,
                "soc_init_fraction" => soc_init_frac,
                "soc_min_fraction" => soc_min,
            ),
            "ElectricLoad" => Dict(
                "loads_kw" => window_load,
            ),
            "ElectricTariff" => Dict(
                "energy_rates" => window_rates,
                "tou_demand_rates" => tou_demand_rates,
                "tou_demand_time_steps" => window_tou_ts,
                "tou_previous_peak_demands" => tou_prev_peaks,
                "monthly_demand_rates" => monthly_demand_rates,
                "time_steps_monthly" => window_monthly_ts,
                "monthly_previous_peak_demands" => monthly_prev_peaks,
            ),
            "ElectricUtility" => Dict(
                "emissions_factor_series_lb_CO2_per_kwh" => window_emissions,
            ),
        )
    end

    @info "MPC: starting rolling-horizon loop ($(length_of_data) iterations, horizon=$(horizon))"
    for idx in 1:length_of_data
        end_ts = idx + horizon - 1
        window_len = end_ts - idx + 1

        window_pv    = _mpc_slice_with_wrap(pv_prod_factor, idx, end_ts)
        window_load  = _mpc_slice_with_wrap(load_series,    idx, end_ts)
        window_rates = _mpc_slice_with_wrap(energy_rates,   idx, end_ts)
        window_emiss = _mpc_slice_with_wrap(emissions,      idx, end_ts)

        # Window-local time-step groupings, both built from a single pass
        # over the horizon. TOU buckets are 1 vector per ratchet (length
        # n_tou); monthly buckets are 1 vector per month (length 12).
        # Global indices wrap on `length_of_data` (8760·tsh) so the month
        # / tier of a wrapped step matches its calendar position.
        window_tou_ts     = [Int[] for _ in 1:n_tou]
        window_monthly_ts = [Int[] for _ in 1:12]
        for k in 1:window_len
            g = idx + k - 1
            if g > length_of_data
                g -= length_of_data
            end
            push!(window_monthly_ts[ts_to_month[g]], k)
            tier = ts_to_tier[g]
            if tier > 0
                push!(window_tou_ts[tier], k)
            end
        end

        post = build_mpc_post(window_pv, window_load, window_rates, window_emiss,
                              window_tou_ts, window_monthly_ts,
                              tou_previous_peak_demands, monthly_previous_peak_demands,
                              bess_soc_init_fraction)

        model = get_solver_model(get_solver_model_type(solver_name),
                                  SolverAttributes(per_iter_timeout_s, optimality_tolerance))
        result = reoptjl.run_mpc(model, post)

        # ---- Extract first-timestep dispatch (perfect-forecast) ----
        pv_res   = result["PV"]
        bess_res = result["ElectricStorage"]
        util_res = result["ElectricUtility"]

        pv_to_load    = pv_res["electric_to_load_series_kw"][1]
        pv_to_bess    = pv_res["electric_to_storage_series_kw"][1]
        pv_to_grid    = haskey(pv_res, "electric_to_grid_series_kw")   ? pv_res["electric_to_grid_series_kw"][1]   : 0.0
        pv_curtailed  = haskey(pv_res, "electric_curtailed_series_kw") ? pv_res["electric_curtailed_series_kw"][1] : 0.0
        bess_to_load  = bess_res["storage_to_load_series_kw"][1]
        bess_soc      = bess_res["soc_series_fraction"][1]
        util_to_load  = util_res["electric_to_load_series_kw"][1]
        util_to_bess  = util_res["electric_to_storage_series_kw"][1]
        grid_power    = max(util_to_load + util_to_bess, 0.0)

        push!(dispatch["PV"]["electric_to_load_series_kw"], pv_to_load)
        push!(dispatch["PV"]["electric_to_storage_series_kw"], pv_to_bess)
        push!(dispatch["PV"]["electric_to_grid_series_kw"], pv_to_grid)
        push!(dispatch["PV"]["electric_curtailed_series_kw"], pv_curtailed)
        push!(dispatch["ElectricStorage"]["storage_to_load_series_kw"], bess_to_load)
        push!(dispatch["ElectricStorage"]["soc_series_fraction"], round(bess_soc, digits=6))
        push!(dispatch["ElectricUtility"]["electric_to_load_series_kw"], util_to_load)
        push!(dispatch["ElectricUtility"]["electric_to_storage_series_kw"], util_to_bess)
        push!(dispatch["ElectricUtility"]["emissions_series_lb_CO2"],
              emissions[idx] * grid_power / time_steps_per_hour)
        push!(dispatch["ElectricLoad"]["load_series_kw"], load_series[idx])

        # ---- Energy cost ----
        step_energy_cost = grid_power * energy_rates[idx] / time_steps_per_hour
        push!(cost_series, step_energy_cost)
        total_energy_cost += step_energy_cost

        # ---- Carry state ----
        bess_soc_init_fraction = bess_soc

        # ---- Demand peak tracking (per-tier and per-month) ----
        # Attribute realized peak grid power to its TOU ratchet (if any)
        # and to its calendar month. Identity comes from the reverse
        # indices, NOT from rate values — so coincident-rate ratchets
        # and equal-rate months remain separate billing pools.
        m_now = ts_to_month[idx]
        monthly_previous_peak_demands[m_now] =
            max(grid_power, monthly_previous_peak_demands[m_now])

        if n_tou > 0
            tier_now = ts_to_tier[idx]
            if tier_now > 0
                tou_previous_peak_demands[tier_now] =
                    max(grid_power, tou_previous_peak_demands[tier_now])
            end
        end

        # ---- Month transition: close out the just-ended month ----
        # Both monthly and TOU peaks reset at month boundaries (matches
        # REopt billing semantics). The last timestep of month m is
        # detected by m_now != ts_to_month[idx+1]; we handle Dec via
        # idx == length_of_data.
        is_month_end = (idx == length_of_data) || (ts_to_month[idx + 1] != m_now)
        if is_month_end
            push!(monthly_peaks, monthly_previous_peak_demands[m_now])
            monthly_demand_cost_total +=
                monthly_previous_peak_demands[m_now] * monthly_demand_rates[m_now]
            monthly_previous_peak_demands[m_now] = 0.0

            if n_tou > 0
                push!(tou_peaks_by_month, copy(tou_previous_peak_demands))
                tou_demand_cost_total += sum(tou_previous_peak_demands .* tou_demand_rates)
                fill!(tou_previous_peak_demands, 0.0)
            end
        end
    end

    @info "MPC: loop complete. total_energy_cost=\$$(round(total_energy_cost, digits=2))"

    return Dict(
        "MPC" => Dict(
            "time_steps_per_hour" => time_steps_per_hour,
            "horizon" => horizon,
        ),
        "PV" => Dict("size_kw" => pv_kw),
        "ElectricStorage" => Dict("size_kw" => bess_kw, "size_kwh" => bess_kwh),
        "dispatch" => dispatch,
        "ElectricTariff" => Dict(
            "total_energy_cost" => total_energy_cost,
            "energy_cost_series_per_timestep" => cost_series,
            "total_tou_demand_cost" => tou_demand_cost_total,
            "total_monthly_demand_cost" => monthly_demand_cost_total,
            "tou_peaks_by_month_kw" => tou_peaks_by_month,
            "monthly_peaks_kw" => monthly_peaks,
        ),
        "status" => "optimal",
        "reopt_version" => string(pkgversion(reoptjl)),
    )
end
