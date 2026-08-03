# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
# ============================================================================
# Heuristic battery dispatch sizing pre-solve
# ----------------------------------------------------------------------------
# Validates acceptable technologies and calls REopt to size PV and ElectricStorage 
# when the user does not provide fixed sizes for heuristic battery dispatch strategies:
#   * daily_foresight_optimized (MPC)
#   * peak_shaving_look_ahead, peak_shaving_look_behind, self_consumption (SAM dispatches)
# These strategies require fixed, non-zero technology sizes.
# ============================================================================

"""
    build_dispatch_response(status; skip_heuristic_dispatch=false, messages=Dict(), result_dict=Dict())

Build a consistent heuristic-dispatch response envelope with status, version info, and messages.
Ensures all response paths (success, error, skip) have uniform structure.
"""
function build_dispatch_response(status::String; skip_heuristic_dispatch=false, messages=Dict(), result_dict=Dict())
    response = Dict(
        "status" => status,
        "reopt_version" => string(pkgversion(reoptjl)),
        "Messages" => messages,
        "skip_heuristic_dispatch" => skip_heuristic_dispatch,
    )
    # Merge result data if provided (for success case)
    return merge(response, result_dict)
end

"""
    get_technology_sizes!(d::Dict, model_inputs::reoptjl.REoptInputs, solver_settings::Dict)

Determine PV and ElectricStorage sizes. If min_kw != max_kw and/or min_kwh != max_kwh,
call REopt to size technologies. User input battery sizes must also be greater than zero.
    d is mutated in-place to update PV and ElectricStorage sizes.
    model_inputs has already been processed to remove inputs not used in REopt.jl
"""
function get_technology_sizes!(d::Dict, model_inputs::reoptjl.REoptInputs, solver_settings::Dict) 
    # pv and batt are updated in-place from the dictionary `d` and used in the final REopt run
    pv   = get!(d, "PV", Dict())
    batt = get!(d, "ElectricStorage", Dict())

    function is_fixed(dct, lo_key, hi_key)
        lo = get(dct, lo_key, nothing)
        hi = get(dct, hi_key, nothing)
        return lo !== nothing && hi !== nothing && Float64(lo) == Float64(hi)
    end

    # Check if both PV and BESS sizes fixed
    pv_fixed   = is_fixed(pv,   "min_kw",  "max_kw")
    batt_fixed = is_fixed(batt, "min_kw",  "max_kw") &&
                 is_fixed(batt, "min_kwh", "max_kwh")

    if pv_fixed && batt_fixed
        pv_kw    = Float64(pv["min_kw"])
        batt_kw  = Float64(batt["min_kw"])
        batt_kwh = Float64(batt["min_kwh"])
        return (pv_kw = pv_kw, batt_kw = batt_kw, batt_kwh = batt_kwh, skip_heuristic_dispatch = false, pv_production_factor_series = nothing)
    end

    @info "PV and/or ElectricStorage sizes are not specified — running REopt sizing first."
    # TODO: Should we "remove tiers" here for sizing or allow for optimizing with tiers? 

    m = get_solver_model(get_solver_model_type(solver_settings["solver_name"]), solver_settings["solver_attributes"])

    sizing_results = reoptjl.run_reopt(m, model_inputs)

    if get(sizing_results, "status", "") != "optimal"
        status = get(sizing_results, "status", "unknown")
        msgs = get(sizing_results, "Messages", Dict())
        errs = get(msgs, "errors", [])
        warns = get(msgs, "warnings", [])
        error("REopt sizing pre-step did not solve (status = $(status)). " *
              "REopt errors: $(errs). REopt warnings: $(warns).")
    end

    pv_kw    = Float64(get(get(sizing_results, "PV", Dict()), "size_kw", 0.0))
    batt_kw  = Float64(get(get(sizing_results, "ElectricStorage", Dict()), "size_kw", 0.0))
    batt_kwh = Float64(get(get(sizing_results, "ElectricStorage", Dict()), "size_kwh", 0.0))
    pv_production_factor_series = get(get(sizing_results, "PV", Dict()), "production_factor_series", nothing)

    # Skip the MPC loop if no battery is sized
    if batt_kw <= 0.0 || batt_kwh <= 0.0
        return (pv_kw = pv_kw, batt_kw = 0.0, batt_kwh = 0.0, skip_heuristic_dispatch = true, pv_production_factor_series = pv_production_factor_series)
    end

    # Fix inputs for final REopt run in http.jl
    pv["min_kw"]    = pv_kw
    pv["max_kw"]    = pv_kw
    batt["min_kw"]  = batt_kw
    batt["max_kw"]  = batt_kw
    batt["min_kwh"] = batt_kwh
    batt["max_kwh"] = batt_kwh

    @info "REopt sizing solved with PV = $(pv_kw) kW and battery = $(batt_kw) kW / $(batt_kwh) kWh."
    return (; pv_kw, batt_kw, batt_kwh, skip_heuristic_dispatch = false, pv_production_factor_series)
end

"""
    validate_and_size_pv_storage!(d::Dict; solver_name, strategy_label)

Validates accepted technologies for heuristic battery dispatch strategies (daily_foresight_optimized,
peak_shaving_look_ahead, peak_shaving_look_behind, self_consumption). Then calls get_technology_sizes
to size PV and ElectricStorage if fixed sizes are not defined by the user. 
"""
function validate_and_size_pv_storage!(d::Dict; solver_name::String="HiGHS", strategy_label::String="a heuristic battery dispatch strategy")
    fail(error_dict) = (; error = error_dict, technology_sizes = nothing, model_inputs = nothing,
                          solver_settings = Dict(), time_steps_per_hour = 1)

    ## Validation on allowable inputs for predetermined heuristic battery dispatch strategies
    # Error if any techs other than PV and ElectricStorage are provided
    allowed_keys = Set(["PV", "ElectricStorage", "ElectricLoad", "ElectricTariff", "ElectricUtility", "Site", "Settings", "Financial"])
    unsupported_keys = setdiff(keys(d), allowed_keys)
    # Ignore disallowed technologies that are explicitly disabled with max_kw = 0
    for key in copy(unsupported_keys)
        val = get(d, key, nothing)
        if val isa AbstractDict && haskey(val, "max_kw") && val["max_kw"] == 0
            setdiff!(unsupported_keys, [key])
        end
    end
    if !isempty(unsupported_keys)
        return fail(build_dispatch_response(
            "error",
            messages = Dict("errors" => ["When using $(strategy_label), only PV and ElectricStorage are supported technologies. " *
                                        "Unsupported inputs found: $(join(unsupported_keys, ", "))."])
        ))
    end

    # Heuristic dispatch through the API only supports a single PV, so error on multiple PVs and normalize a one-element array down to a Dict so downstream code can treat d["PV"] as a Dict.
    # TODO: Handle multiple PVs
    if haskey(d, "PV") && isa(d["PV"], AbstractArray)
        if length(d["PV"]) > 1
            return fail(build_dispatch_response(
                "error",
                messages = Dict("errors" => ["$(strategy_label): Multiple PV systems are not supported at this time."])
            ))
        elseif length(d["PV"]) == 1
            d["PV"] = d["PV"][1]
        else
            delete!(d, "PV")  # empty PV array -> treat as no PV
        end
    end 

    # Check max storage sizing is greater than zero 
    batt = get(d, "ElectricStorage", Dict())
    if Float64(get(batt, "max_kw", 1.0)) <= 0.0 || Float64(get(batt, "max_kwh", 1.0)) <= 0.0
        return fail(build_dispatch_response(
            "error",
            messages = Dict("errors" => ["When using $(strategy_label), ElectricStorage max_kw and max_kwh must both be greater than zero."])
        ))
    end

    settings = get!(d, "Settings", Dict())
    time_steps_per_hour = Int(get(settings, "time_steps_per_hour", 1))

    # Update sizing_post to remove solver settings and dispatch inputs, to be able to validate inputs using REoptInputs
    sizing_post = deepcopy(d)
    sizing_settings = get(sizing_post, "Settings", Dict())
    solver_settings = Dict()
    delete!(sizing_settings, "run_bau")  # Remove run_bau from sizing run
    solver_settings["timeout_seconds"] = pop!(sizing_settings, "timeout_seconds", 600) # Only gets used in sizing run
    solver_settings["optimality_tolerance"] = pop!(sizing_settings, "optimality_tolerance", 0.001) # Update to a higher value if solve time becomes an issue
    solver_settings["solver_attributes"] = SolverAttributes(solver_settings["timeout_seconds"], solver_settings["optimality_tolerance"])
    solver_settings["solver_name"] = solver_name
    # Delete inputs specific to the heuristic battery dispatch run
    if haskey(sizing_post, "ElectricStorage")
        delete!(sizing_post["ElectricStorage"], "dispatch_strategy")
        delete!(sizing_post["ElectricStorage"], "fixed_soc_series_fraction")
    end

    # Process and validate inputs using REoptInputs
    model_inputs = nothing
    try
        model_inputs = reoptjl.REoptInputs(sizing_post)

        # REoptInputs returns an error Dict (rather than throwing) when input validation fails.
        # Surface those messages instead of falling through to get_technology_sizes!, which expects a REoptInputs and would otherwise raise a confusing MethodError.
        if isa(model_inputs, Dict)
            @error "REopt input validation failed during sizing pre-solve." messages=get(model_inputs, "Messages", Dict())
            return fail(build_dispatch_response(
                "error",
                messages = get(model_inputs, "Messages", Dict("errors" => ["REopt input validation failed."]))
            ))
        end
        @info "Successfully processed REopt inputs."
    catch e
        @error "Something went wrong during REopt inputs processing!" exception=(e, catch_backtrace())
        return fail(build_dispatch_response(
            "error",
            messages = Dict("errors" => [sprint(showerror, e)])
        ))
    end

    # If fixed PV and battery sizes are not provided, call REopt first in a sizing run
    technology_sizes = get_technology_sizes!(d, model_inputs, solver_settings)

    return (; error = nothing, technology_sizes, model_inputs, solver_settings, time_steps_per_hour)
end
