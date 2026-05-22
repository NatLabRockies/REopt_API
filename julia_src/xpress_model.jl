# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
function xpress_model(MAXTIME, MIPRELSTOP)
    m = direct_model(Xpress.Optimizer(MAXTIME=-MAXTIME, MIPRELSTOP=MIPRELSTOP, OUTPUTLOG = 0)) #logfile="output.log"))
	m[:solver_name] = "Xpress"
	m[:timeout_seconds] = MAXTIME
	m[:optimality_tolerance] = MIPRELSTOP
	return m
end