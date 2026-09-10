# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
abstract type SolverModel end
struct HiGHSModel <: SolverModel end
struct CbcModel <: SolverModel end
struct SCIPModel <: SolverModel end
struct XpressModel <: SolverModel end

# Solver name used as input, map to instance of [Solver]Model for multiple dispatch of solver_model()
#   for creating the right solver model
# The get_solver_model(XpressModel) is created in the xpress.jl file 
solver_name_type_map = Dict([("HiGHS", HiGHSModel()), 
                            ("Cbc", CbcModel()),
                            ("SCIP", SCIPModel()),
                            ("Xpress", XpressModel())])

struct SolverAttributes
    timeout_seconds::Int64  # Solver times out after this amount of time and returns timeout error
    optimality_tolerance::Float64  # Optimality tolerance - maximum optimality gap, relative to [lp-relaxed] feasible
end

function get_solver_model_type(solver_name::String)
    solver_model_type = solver_name_type_map[solver_name]
    return solver_model_type
end

# Model vs direct_model? Consistent way to assign/set optimizer attributes?
# We use Model in REopt.jl tests, but switching to direct_model consistent with Xpress here
function get_solver_model(solver::HiGHSModel, attributes::SolverAttributes)
    
    m = Model(optimizer_with_attributes(HiGHS.Optimizer, 
            "time_limit" => convert(Float64, attributes.timeout_seconds),
            "mip_rel_gap" => attributes.optimality_tolerance,
            "output_flag" => false, 
            "log_to_console" => false)
            )
    return m
end

function get_solver_model(solver::CbcModel, attributes::SolverAttributes)
    m = Model(optimizer_with_attributes(Cbc.Optimizer,
            "seconds" => attributes.timeout_seconds,
            "ratioGap" => attributes.optimality_tolerance,
            "logLevel" => 0)
            )
    return m
end

function get_solver_model(solver::SCIPModel, attributes::SolverAttributes)
    m = Model(optimizer_with_attributes(SCIP.Optimizer,
            "limits/time" => attributes.timeout_seconds,
            "limits/gap" => attributes.optimality_tolerance,
            "display/verblevel" => 0)
            )
    return m
end

