# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.

# New for variable solver setup with v3
function get_solver_model(solver::XpressModel, attributes::SolverAttributes)
    m = direct_model(optimizer_with_attributes(Xpress.Optimizer,
            "MAXTIME" => -attributes.timeout_seconds, 
            "MIPRELSTOP" => attributes.optimality_tolerance,
            "OUTPUTLOG" => 0)
            )
	return m
end

# V1 and V2 Endpoint for calling local REopt.jl module (not the registered Julia package REopt.jl)
# To be End-of-Life deprecated and removed by end of March 2024
function job(req::HTTP.Request)
    d = JSON.parse(String(req.body))
    timeout = pop!(d, "timeout_seconds")
    tol = pop!(d, "tolerance")
    m = REopt.xpress_model(timeout, tol)
    @info "Starting REopt with timeout of $(timeout) seconds..."
	error_response = Dict()
	results = Dict()
	try
    	results = REopt.reopt(m, d)
	catch e
		@error "Something went wrong in the Julia code!" exception=(e, catch_backtrace())
		error_response["error"] = sprint(showerror, e)
	end
    optimizer = backend(m)
	finalize(optimizer)
    Xpress.postsolve(optimizer.inner)
	empty!(m)
	GC.gc()
	if isempty(error_response)
    	@info "REopt model solved with status $(results["status"])."
    	return HTTP.Response(200, JSON.json(results))
	else
		@info "An error occured in the Julia code."
		return HTTP.Response(500, JSON.json(error_response))
	end
end