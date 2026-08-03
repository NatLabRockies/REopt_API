# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
function add_continuous_variables(m, p)
    @variables m begin
	    dvSize[p.Tech] >= 0     #X^{\sigma}_{t}: System Size of Technology t [kW]   (NEW)
    	dvSystemSizeSegment[p.Tech, p.Subdivision, p.Seg] >= 0   #X^{\sigma s}_{tks}: System size of technology t allocated to segmentation k, segment s [kW]  (NEW)
		dvGridPurchase[p.PricingTier, p.TimeStep] >= 0   # X^{g}_{uh}: Power from grid dispatched to meet electrical load in demand tier u during time step h [kW]  (NEW)
	    dvRatedProduction[p.Tech, p.TimeStep] >= 0   #X^{rp}_{th}: Rated production of technology t during time step h [kW]  (NEW)
		dvProductionToCurtail[p.Tech, p.TimeStep] >= 0
		dvProductionToStorage[p.Storage, p.Tech, p.TimeStep] >= 0  # X^{ptg}_{bth}: Power from technology t used to charge storage system b during time step h [kW]  (NEW)
	    dvProductionToWaste[p.CHPTechs, p.TimeStep] >= 0  #X^{ptw}_{th}: Thermal production by CHP technology t sent to waste in time step h
		dvDischargeFromStorage[p.Storage, p.TimeStep] >= 0 # X^{pts}_{bh}: Power discharged from storage system b during time step h [kW]  (NEW)
	    dvGridToStorage[p.TimeStep] >= 0 # X^{gts}_{h}: Electrical power delivered to storage by the grid in time step h [kW]  (NEW)
	    dvStorageSOC[p.Storage, p.TimeStepBat] >= 0  # X^{se}_{bh}: State of charge of storage system b in time step h   (NEW)
	    dvStorageCapPower[p.Storage] >= 0   # X^{bkW}_b: Power capacity of storage system b [kW]  (NEW)
	    dvStorageCapEnergy[p.Storage] >= 0   # X^{bkWh}_b: Energy capacity of storage system b [kWh]  (NEW)
	    dvProdIncent[p.Tech] >= 0   # X^{pi}_{t}: Production incentive collected for technology [$]
		dvPeakDemandE[p.Ratchets, p.DemandBin] >= 0  # X^{de}_{re}:  Peak electrical power demand allocated to tier e during ratchet r [kW]
		dvPeakDemandEMonth[p.Month, p.DemandMonthsBin] >= 0  #  X^{dn}_{mn}: Peak electrical power demand allocated to tier n during month m [kW]
		dvPeakDemandELookback[p.Month] >= 0  # X^{lp}: Peak electric demand look back [kW]
		dvPeakDemandCP[p.CPPeriod] >= 0 # X^{cp}_p: Peak electric demand during expected coincident peak hours of CP period p [kW]
		MinChargeAdder >= 0   #to be removed
		#UtilityMinChargeAdder[p.Month] >= 0   #X^{mc}_m: Annual utility minimum charge adder in month m [\$]
		#CHP and Fuel-burning variables
		dvFuelUsage[p.Tech, p.TimeStep] >= 0  # Fuel burned by technology t in time step h (units=kWh)
		dvFuelBurnYIntercept[p.Tech, p.TimeStep] >= 0  #X^{fb}_{th}: Y-intercept of fuel burned by technology t in time step h
		dvThermalProduction[p.Tech, p.TimeStep] >= 0  #X^{tp}_{th}: Thermal production by technology t in time step h
		dvThermalProductionYIntercept[p.Tech, p.TimeStep] >= 0  #X^{tp}_{th}: Thermal production by technology t in time step h
		dvAbsorptionChillerDemand[p.TimeStep] >= 0  #X^{ac}_h: Thermal power consumption by absorption chiller in time step h
		dvElectricChillerDemand[p.TimeStep] >= 0  #X^{ec}_h: Electrical power consumption by electric chiller in time step h
		dvOMByHourBySizeCHP[p.Tech, p.TimeStep] >= 0
        dvSupplementaryThermalProduction[p.CHPTechs, p.TimeStep] >= 0
		dvSupplementaryFiringCHPSize[p.CHPTechs] >= 0  #X^{\sigma db}_{t}: System size of CHP with supplementary firing [kW]
		#Offgrid analyses
		1 >= dvOffgridLoadServedFraction[p.TimeStepsWithoutGrid] >= 0
		dvSRbatt[p.ElecStorage, p.TimeStepsWithoutGrid] >= 0
		dvSR[p.TechsProvidingSR, p.TimeStepsWithoutGrid] >= 0
    end
	if !isempty(p.ExportTiers)
		@variable(m, dvProductionToGrid[p.Tech, p.ExportTiers, p.TimeStep] >= 0)  # X^{ptg}_{tuh}: Exports from electrical production to the grid by technology t in demand tier u during time step h [kW]   (NEW)
	end
    if !isempty(p.SteamTurbineTechs)
        @variable(m, dvThermalToSteamTurbine[p.AllTechsForSteamTurbine, p.TimeStep] >= 0)
    end
end


function add_integer_variables(m, p)
    @variables m begin
        binNMLorIL[p.NMILRegime], Bin    # Z^{nmil}_{v}: 1 If generation is in net metering interconnect limit regime v; 0 otherwise
        binProdIncent[p.Tech], Bin # Z^{pi}_{t}:  1 If production incentive is available for technology t; 0 otherwise
		binSegmentSelect[p.Tech, p.Subdivision, p.Seg], Bin # Z^{\sigma s}_{tks} 1 if technology t, segmentation k is in segment s; 0 ow. (NEW)
        binSingleBasicTech[p.Tech,p.TechClass], Bin   #  Z^\text{sbt}_{tc}: 1 If technology t is used for technology class c; 0 otherwise
        binTechIsOnInTS[p.Tech, p.TimeStep], Bin  # 1 Z^{to}_{th}: If technology t is operating in time step h; 0 otherwise
		binDemandTier[p.Ratchets, p.DemandBin], Bin  # 1 If tier e has allocated demand during ratchet r; 0 otherwise
        binDemandMonthsTier[p.Month, p.DemandMonthsBin], Bin # 1 If tier n has allocated demand during month m; 0 otherwise
		binEnergyTier[p.Month, p.PricingTier], Bin    #  Z^{ut}_{mu} 1 If demand tier $u$ is active in month m; 0 otherwise (NEW)
		binNoGridPurchases[p.TimeStep], Bin  # Binary for the condition where the site load is met by on-site resources so no grid purchases
		binGHP[p.GHPOptions], Bin  # Can be <= 1 if RequireGHPPurchase=0, and is ==1 if RequireGHPPurchase=1
		binUseSupplementaryFiring[p.CHPTechs], Bin  #Z^{db}_{t}: 1 if supplementary firing is included with CHP system, 0 o.w.
	end
end


function add_parameters(m, p)
    m[:r_tax_fraction_owner] = (1 - p.r_tax_owner)
    m[:r_tax_fraction_offtaker] = (1 - p.r_tax_offtaker)

    m[:PVTechs] = filter(t->startswith(t, "PV"), p.Tech)
	if !isempty(p.Tech)
		m[:WindTechs] = p.TechsInClass["WIND"]
		m[:GeneratorTechs] = p.TechsInClass["GENERATOR"]
	else
		m[:WindTechs] = []
		m[:GeneratorTechs] = []
	end
end



function add_cost_expressions(m, p)
	if !isempty(p.CHPTechs)
		m[:TotalTechCapCosts] = @expression(m, p.two_party_factor * (
			sum( p.CapCostSlope[t,s] * m[:dvSystemSizeSegment][t,"CapCost",s] for t in p.Tech, s in 1:p.SegByTechSubdivision["CapCost",t] ) +
			sum( p.CapCostYInt[t,s] * m[:binSegmentSelect][t,"CapCost",s] for t in p.Tech, s in 1:p.SegByTechSubdivision["CapCost",t] ) +
			sum( p.CapCostSupplementaryFiring[t] * m[:dvSupplementaryFiringCHPSize][t] for t in p.CHPTechs )
		))
	else
		m[:TotalTechCapCosts] = @expression(m, p.two_party_factor * (
			sum( p.CapCostSlope[t,s] * m[:dvSystemSizeSegment][t,"CapCost",s] for t in p.Tech, s in 1:p.SegByTechSubdivision["CapCost",t] ) +
			sum( p.CapCostYInt[t,s] * m[:binSegmentSelect][t,"CapCost",s] for t in p.Tech, s in 1:p.SegByTechSubdivision["CapCost",t] )
		))
	end
	m[:TotalStorageCapCosts] = @expression(m, p.two_party_factor *
		sum( p.StorageCostPerKW[b]*m[:dvStorageCapPower][b] + p.StorageCostPerKWH[b]*m[:dvStorageCapEnergy][b] for b in p.Storage )
	)
	m[:TotalPerUnitSizeOMCosts] = @expression(m, p.two_party_factor * p.pwf_om *
		sum( p.OMperUnitSize[t] * m[:dvSize][t] for t in p.Tech )
	)
    FuelBurnAndHeatingTechs = union(p.FuelBurningTechs, p.HeatingTechs)
    if !isempty(FuelBurnAndHeatingTechs)
		m[:TotalPerUnitProdOMCosts] = @expression(m, p.two_party_factor * p.pwf_om * p.TimeStepScaling * 
			sum( p.OMcostPerUnitProd[t] * m[:dvRatedProduction][t,ts] for t in FuelBurnAndHeatingTechs, ts in p.TimeStep )
		)
    else
        m[:TotalPerUnitProdOMCosts] = @expression(m, 0.0)
	end
	if !isempty(p.CHPTechs)
		m[:TotalCHPStandbyCharges] = @expression(m, p.pwf_e * p.CHPStandbyCharge * 12 *
			sum(m[:dvSize][t] for t in p.CHPTechs))
		m[:TotalHourlyCHPOMCosts] = @expression(m, p.two_party_factor * p.pwf_om * p.TimeStepScaling *
			sum(m[:dvOMByHourBySizeCHP][t, ts] for t in p.CHPTechs, ts in p.TimeStep))
	else
		m[:TotalCHPStandbyCharges] = @expression(m, 0.0)
		m[:TotalHourlyCHPOMCosts] = @expression(m, 0.0)
	end
	# TODO is this if else statement necessary or will model value m[:GHPCap/OMCosts] = 0 if isempty(p.GHPOptions)?
	if !isempty(p.GHPOptions)
		m[:GHPCapCosts] = @expression(m, p.two_party_factor *
			sum(p.GHPInstalledCost[g] * m[:binGHP][g] for g in p.GHPOptions)
		)
		m[:GHPOMCosts] = @expression(m, p.two_party_factor * p.pwf_om *
			sum(p.GHPOMCost[g] * m[:binGHP][g] for g in p.GHPOptions)
		)
	else
		m[:GHPCapCosts] = @expression(m, 0.0)
		m[:GHPOMCosts] = @expression(m, 0.0)
	end
end


function add_export_expressions(m, p)
    """
    There are three Export tiers and their associated export rates (negative values):
    1. NEM
    2. Wholesale
    3. Excess

    Only one of NEM and Wholesale can be exported into due to the NMIL binary constraints.
    Excess can be exported into in the same time step as NEM or Wholesale.

    Excess is meant to be combined with NEM: NEM export is limited to the total grid purchased energy in a year and some
    utilities offer a compensation mechanism for export beyond the site load.
    The Excess tier does not have really have a purpose with the Wholesale tier. (It used to be effectively curtailment).
    """

	m[:TotalExportBenefit] = 0
	m[:CurtailedElecWIND] = 0
	m[:ExportedElecWIND] = 0
	m[:ExportedElecGEN] = 0
	m[:ExportBenefitYr1] = 0

	if !isempty(p.Tech)

		m[:CurtailedElecWIND] = @expression(m,
			p.TimeStepScaling * sum(m[:dvProductionToCurtail][t, ts]
				for t in m[:WindTechs], ts in p.TimeStep)
		)

		if !isempty(p.ExportTiers)
			m[:TotalExportBenefit] = @expression(m, p.pwf_e * p.TimeStepScaling * sum(
				+ sum(p.GridExportRates[u,ts] * m[:dvProductionToGrid][t,u,ts]
					for u in p.ExportTiers, t in p.TechsByExportTier[u]
				) for ts in p.TimeStep )
			)  # NOTE: LevelizationFactor is baked into m[:dvProductionToGrid]

			m[:ExportedElecWIND] = @expression(m,
				p.TimeStepScaling * sum(m[:dvProductionToGrid][t,u,ts]
					for t in m[:WindTechs], u in p.ExportTiersByTech[t], ts in p.TimeStep)
			)
			m[:ExportedElecGEN] = @expression(m,
				p.TimeStepScaling * sum(m[:dvProductionToGrid][t,u,ts]
				for t in m[:GeneratorTechs], u in p.ExportTiersByTech[t], ts in p.TimeStep)
			)
			m[:ExportBenefitYr1] = @expression(m,
				p.TimeStepScaling * sum(
				+ sum( p.GridExportRates[u,ts] * m[:dvProductionToGrid][t,u,ts]
					for u in p.ExportTiers, t in p.TechsByExportTier[u])
				for ts in p.TimeStep )
			)
		end
	end
end


function add_bigM_adjustments(m, p)
	m[:NewMaxUsageInTier] = Array{Float64,2}(undef,12, p.PricingTierCount+1)
	m[:NewMaxDemandInTier] = Array{Float64,2}(undef, length(p.Ratchets), p.DemandBinCount)
	m[:NewMaxDemandMonthsInTier] = Array{Float64,2}(undef,12, p.DemandMonthsBinCount)

	# m[:NewMaxDemandMonthsInTier] sets a new minimum if the new peak demand for the month, minus the size of all previous bins, is less than the existing bin size.
	if !isempty(p.ElecStorage)
		added_power = p.StorageMaxSizePower["Elec"]
		added_energy = p.StorageMaxSizeEnergy["Elec"]
	else
		added_power = 1.0e-3
		added_energy = 1.0e-3
	end

    if !isempty(p.GHPOptions)
        add_ghp_heating_elec = 1.0
    else
        add_ghp_heating_elec = 0.0
    end

	for n in p.DemandMonthsBin
		for mth in p.Month
			if n > 1
				m[:NewMaxDemandMonthsInTier][mth,n] = minimum([p.MaxDemandMonthsInTier[n],
					added_power + 2*maximum([100*p.ElecLoad[ts] + p.CoolingLoad[ts] +
                    add_ghp_heating_elec * p.HeatingLoad[ts]
					for ts in p.TimeStepRatchetsMonth[mth]])  -
					sum(m[:NewMaxDemandMonthsInTier][mth,np] for np in 1:(n-1))]
				)
			else
				m[:NewMaxDemandMonthsInTier][mth,n] = minimum([p.MaxDemandMonthsInTier[n],
					added_power + 2*maximum([100*p.ElecLoad[ts] + p.CoolingLoad[ts] +
                    add_ghp_heating_elec * p.HeatingLoad[ts]
					for ts in p.TimeStepRatchetsMonth[mth]])]
                )
			end
		end
	end

	# m[:NewMaxDemandInTier] sets a new minimum if the new peak demand for the ratchet, minus the size of all previous bins for the ratchet, is less than the existing bin size.
	for e in p.DemandBin
		for r in p.Ratchets
			if e > 1
				m[:NewMaxDemandInTier][r,e] = minimum([p.MaxDemandInTier[e]
				added_power + 2*maximum([p.ElecLoad[ts] + p.CoolingLoad[ts] +
                add_ghp_heating_elec * p.HeatingLoad[ts]
					for ts in p.TimeStep])  -
				sum(m[:NewMaxDemandInTier][r,ep] for ep in 1:(e-1))
				])
			else
				m[:NewMaxDemandInTier][r,e] = minimum([p.MaxDemandInTier[e],
				added_power + 2*maximum([p.ElecLoad[ts] + p.CoolingLoad[ts] +
                add_ghp_heating_elec * p.HeatingLoad[ts]
					for ts in p.TimeStep])
				])
			end
		end
	end

	# m[:NewMaxUsageInTier] sets a new minumum if the total demand for the month, minus the size of all previous bins, is less than the existing bin size.
	for u in p.PricingTier
		for mth in p.Month
			if u > 1
				m[:NewMaxUsageInTier][mth,u] = minimum([p.MaxUsageInTier[u],
					added_energy + 2*sum(p.ElecLoad[ts] + p.CoolingLoad[ts] +
                    add_ghp_heating_elec * p.HeatingLoad[ts]
					for ts in p.TimeStepRatchetsMonth[mth]) - sum(m[:NewMaxUsageInTier][mth,up] for up in 1:(u-1))
				])
			else
				m[:NewMaxUsageInTier][mth,u] = minimum([p.MaxUsageInTier[u],
					added_energy + 2*sum(p.ElecLoad[ts] + p.CoolingLoad[ts] +
                    add_ghp_heating_elec * p.HeatingLoad[ts]
					for ts in p.TimeStepRatchetsMonth[mth])
				])
			end
		end
	end

	# NewMaxSize generates a new maximum size that is equal to the largest monthly load of the year.
	# This is intended to be a reasonable upper bound on size that would never be exceeeded,
	# but is sufficienctly small to replace much larger big-M values placed as a default.
	m[:NewMaxSize] = Dict()

	for t in p.BoilerTechs
		m[:NewMaxSize][t] = maximum([sum(p.HeatingLoad[ts] for ts in p.TimeStepRatchetsMonth[mth]) for mth in p.Month])
		if (m[:NewMaxSize][t] > p.MaxSize[t])
			m[:NewMaxSize][t] = p.MaxSize[t]
        end
	end

	for t in p.CoolingTechs
		m[:NewMaxSize][t] = maximum([sum(p.CoolingLoad[ts] for ts in p.TimeStepRatchetsMonth[mth]) for mth in p.Month])
		if (m[:NewMaxSize][t] > p.MaxSize[t])
			m[:NewMaxSize][t] = p.MaxSize[t]
		end
	end

	for c in p.TechClass, t in p.TechsInClass[c]
		if t in p.ElectricTechs
			m[:NewMaxSize][t] = maximum([sum(p.ElecLoad[ts] + p.CoolingLoad[ts] / p.ElectricChillerCOP
										 for ts in p.TimeStepRatchetsMonth[mth]) for mth in p.Month])
			if m[:NewMaxSize][t] > p.MaxSize[t] || m[:NewMaxSize][t] < p.TechClassMinSize[c]
				m[:NewMaxSize][t] = p.MaxSize[t]
			end
		end
	end
end


function add_no_grid_constraints(m, p)
	for ts in p.TimeStepsWithoutGrid
		fix(m[:dvGridToStorage][ts], 0.0, force=true)
		for u in p.PricingTier
			fix(m[:dvGridPurchase][u,ts], 0.0, force=true)
		end
	end
end


function add_fuel_constraints(m, p)

	##Constraint (1a): Sum of fuel used must not exceed prespecified limits
	@constraint(m, TotalFuelConsumptionCon[f in p.FuelType],
		sum( m[:dvFuelUsage][t,ts] for t in p.TechsByFuelType[f], ts in p.TimeStep ) <=
		p.FuelLimit[f]
	)

	# Constraint (1b): Fuel burn for non-CHP Constraints
	if !isempty(p.TechsInClass["GENERATOR"])
		@constraint(m, FuelBurnCon[t in p.TechsInClass["GENERATOR"], ts in p.TimeStep],
			m[:dvFuelUsage][t,ts]  == p.TimeStepScaling * (
				p.FuelBurnSlope[t] * p.ProductionFactor[t,ts] * m[:dvRatedProduction][t,ts] +
				p.FuelBurnYInt[t] * m[:binTechIsOnInTS][t,ts] )
		)
		m[:TotalGeneratorFuelCharges] = @expression(m, p.pwf_fuel["GENERATOR"] *
			sum(p.FuelCost["DIESEL",ts] * m[:dvFuelUsage]["GENERATOR",ts] for ts in p.TimeStep)
		)
	end

	if !isempty(p.CHPTechs)
		#Constraint (1c): Total Fuel burn for CHP
		@constraint(m, CHPFuelBurnCon[t in p.CHPTechs, ts in p.TimeStep],
			m[:dvFuelUsage][t,ts]  == p.TimeStepScaling * (
				m[:dvFuelBurnYIntercept][t,ts] +
				p.ProductionFactor[t,ts] * p.FuelBurnSlope[t] * m[:dvRatedProduction][t,ts] +
                m[:dvSupplementaryThermalProduction][t,ts] / p.CHPSupplementaryFireEfficiency
			)
		)

		#Constraint (1d): Y-intercept fuel burn for CHP
		@constraint(m, CHPFuelBurnYIntCon[t in p.CHPTechs, ts in p.TimeStep],
					p.FuelBurnYIntRate[t] * m[:dvSize][t] - m[:NewMaxSize][t] * (1-m[:binTechIsOnInTS][t,ts])  <= m[:dvFuelBurnYIntercept][t,ts]
					)
	end

	if !isempty(p.BoilerTechs)
		#Constraint (1e): Total Fuel burn for Boiler
		@constraint(m, BoilerFuelBurnCon[t in p.BoilerTechs, ts in p.TimeStep],
			m[:dvFuelUsage][t,ts]  ==  p.TimeStepScaling * (
				p.ProductionFactor[t,ts] * m[:dvThermalProduction][t,ts] / p.BoilerEfficiency[t]
			)
		)
	end

	m[:TotalFuelCharges] = @expression(m, sum(sum( p.pwf_fuel[t] * p.FuelCost[f,ts] *
		m[:dvFuelUsage][t,ts] for t in p.TechsByFuelType[f], ts in p.TimeStep)
		for f in p.FuelType)
	)

end

function add_thermal_production_constraints(m, p)
	if !isempty(p.CHPTechs)
		#Constraint (2a-1): Upper Bounds on Thermal Production Y-Intercept
		@constraint(m, CHPYInt2a1Con[t in p.CHPTechs, ts in p.TimeStep],
					m[:dvThermalProductionYIntercept][t,ts] <= p.CHPThermalProdIntercept[t] * m[:dvSize][t]
					)
		# Constraint (2a-2): Upper Bounds on Thermal Production Y-Intercept
		@constraint(m, CHPYInt2a2Con[t in p.CHPTechs, ts in p.TimeStep],
					m[:dvThermalProductionYIntercept][t,ts] <= p.CHPThermalProdIntercept[t] * m[:NewMaxSize][t] * m[:binTechIsOnInTS][t,ts]
					)
		#Constraint (2b): Lower Bounds on Thermal Production Y-Intercept
		@constraint(m, CHPYInt2bCon[t in p.CHPTechs, ts in p.TimeStep],
					m[:dvThermalProductionYIntercept][t,ts] >= p.CHPThermalProdIntercept[t] * m[:dvSize][t] - p.CHPThermalProdIntercept[t] * m[:NewMaxSize][t] * (1 - m[:binTechIsOnInTS][t,ts])
					)
		# Constraint (2c): Thermal Production of CHP
		# Note: p.HotWaterAmbientFactor[t,ts] * p.HotWaterThermalFactor[t,ts] removed from this but present in math
		@constraint(m, CHPThermalProductionCon[t in p.CHPTechs, ts in p.TimeStep],
					m[:dvThermalProduction][t,ts] ==
					p.CHPThermalProdSlope[t] * p.ProductionFactor[t,ts] * m[:dvRatedProduction][t,ts] + m[:dvThermalProductionYIntercept][t,ts] +
                    m[:dvSupplementaryThermalProduction][t,ts]
					)
        # Supplementary firing thermal constraint
        if (!isempty(p.CHPTechs)) && p.CHPSupplementaryFireMaxRatio > 1.0
            # Constrain upper limit of dvSupplementaryThermalProduction, using auxiliary variable for (size * useSupplementaryFiring)
            @constraint(m, CHPSupplementaryFireCon[t in p.CHPTechs, ts in p.TimeStep],
                        m[:dvSupplementaryThermalProduction][t,ts] <=
                        (p.CHPSupplementaryFireMaxRatio - 1.0) * p.ProductionFactor[t,ts] * (p.CHPThermalProdSlope[t] * m[:dvSupplementaryFiringCHPSize][t] + m[:dvThermalProductionYIntercept][t,ts])
                        )
            # Constrain lower limit of 0 if CHP tech is off
            @constraint(m, NoCHPSupplementaryFireOffCon[t in p.CHPTechs, ts in p.TimeStep],
                        !m[:binTechIsOnInTS][t,ts] => {m[:dvSupplementaryThermalProduction][t,ts] <= 0.0}
                        )
            # Constrain lower limit of 0 if binUseSupplementaryFiring is 0
            @constraint(m, NoCHPSupplementaryFireNotChosenCon[t in p.CHPTechs, ts in p.TimeStep],
                        !m[:binUseSupplementaryFiring][t] => {m[:dvSupplementaryThermalProduction][t,ts] <= 0.0}
                        )
        else
			for t in p.CHPTechs
	            for ts in p.TimeStep
    	            fix(m[:dvSupplementaryThermalProduction][t,ts], 0.0, force=true)
				end
			end
        end
	end

	if !isempty(p.SteamTurbineTechs)
		# Force thermal production to steam turbine to zero if not applicable
        for t in setdiff(p.AllTechsForSteamTurbine, p.TechCanSupplySteamTurbine)
            for ts in p.TimeStep
                fix(m[:dvThermalToSteamTurbine][t,ts], 0.0, force=true)
            end
        end
        # Constraint Steam Turbine Thermal Production
		@constraint(m, SteamTurbineThermalProductionCon[t in p.SteamTurbineTechs, ts in p.TimeStep],
					m[:dvThermalProduction][t,ts] == p.ProductionFactor[t,ts] *
                    p.STThermOutToThermInRatio * sum(m[:dvThermalToSteamTurbine][tst,ts] for tst in p.TechCanSupplySteamTurbine)
					)
        # Constraint Steam Turbine Electric Production
        @constraint(m, SteamTurbineElectricProductionCon[t in p.SteamTurbineTechs, ts in p.TimeStep],
                    m[:dvRatedProduction][t,ts] ==
                    p.STElecOutToThermInRatio * sum(m[:dvThermalToSteamTurbine][tst,ts] for tst in p.TechCanSupplySteamTurbine)
                    )
	end
end


function add_binTechIsOnInTS_constraints(m, p)
	### Section 3: Switch Constraints
	#Constraint (3a): Technology must be on for nonnegative output (fuel-burning only)
	@constraint(m, ProduceIfOnCon[t in p.FuelBurningTechs, ts in p.TimeStep],
		m[:dvRatedProduction][t,ts] <= m[:NewMaxSize][t] * m[:binTechIsOnInTS][t,ts]
	)
	if p.OffGridFlag
		# Technologies that are turned on must not be turned down below the MinTurndown
		@constraint(m, MinTurndownCon[t in p.FuelBurningTechs, ts in p.TimeStepsWithoutGrid],
		p.MinTurndown[t] * m[:dvSize][t] - m[:dvRatedProduction][t,ts] <= m[:NewMaxSize][t] * (1-m[:binTechIsOnInTS][t,ts])
		)
	else
        # distinct grid outage model
		# Constraint (3b): Technologies that are turned on must not be turned down below the MinTurndown while grid connected
		@constraint(m, MinTurndownCon[t in p.FuelBurningTechs, ts in p.TimeStepsWithGrid],
		p.MinTurndown[t] * m[:dvSize][t] - m[:dvRatedProduction][t,ts] <= m[:NewMaxSize][t] * (1-m[:binTechIsOnInTS][t,ts])
		)
	end
end


function add_storage_size_constraints(m, p)
	# Constraint (4a): Reconcile initial state of charge for storage systems
	@constraint(m, InitStorageCon[b in p.Storage], m[:dvStorageSOC][b,0] == p.StorageInitSOC[b] * m[:dvStorageCapEnergy][b])
	# Constraint (4b)-1: Lower bound on Storage Energy Capacity
	@constraint(m, StorageEnergyLBCon[b in p.Storage], m[:dvStorageCapEnergy][b] >= p.StorageMinSizeEnergy[b])
	# Constraint (4b)-2: Upper bound on Storage Energy Capacity
	@constraint(m, StorageEnergyUBCon[b in p.Storage], m[:dvStorageCapEnergy][b] <= p.StorageMaxSizeEnergy[b])
	# Constraint (4c)-1: Lower bound on Storage Power Capacity
	@constraint(m, StoragePowerLBCon[b in p.Storage], m[:dvStorageCapPower][b] >= p.StorageMinSizePower[b])
	# Constraint (4c)-2: Upper bound on Storage Power Capacity
	@constraint(m, StoragePowerUBCon[b in p.Storage], m[:dvStorageCapPower][b] <= p.StorageMaxSizePower[b])
end


function add_storage_op_constraints(m, p)
	### Battery Operations
	# Constraint (4d): Electrical production sent to storage or grid must be less than technology's rated production
	if !isempty(p.ExportTiers)
		@constraint(m, ElecTechProductionFlowCon[t in p.ElectricTechs, ts in p.TimeStepsWithGrid],
			sum(m[:dvProductionToStorage][b,t,ts] for b in p.ElecStorage)
		  + sum(m[:dvProductionToGrid][t,u,ts] for u in p.ExportTiersByTech[t])
		  + m[:dvProductionToCurtail][t,ts]
		 <= p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvRatedProduction][t,ts]
		)
	else
		@constraint(m, ElecTechProductionFlowCon[t in p.ElectricTechs, ts in p.TimeStepsWithGrid],
			sum(m[:dvProductionToStorage][b,t,ts] for b in p.ElecStorage)
		  + m[:dvProductionToCurtail][t,ts]
		 <= p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvRatedProduction][t,ts]
		)
	end
	# Constraint (4e): Electrical production sent to storage or grid must be less than technology's rated production - no grid
	@constraint(m, ElecTechProductionFlowNoGridCon[t in p.ElectricTechs, ts in p.TimeStepsWithoutGrid],
		sum(m[:dvProductionToStorage][b,t,ts] for b in p.ElecStorage)
		+ m[:dvProductionToCurtail][t, ts]
		<= p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvRatedProduction][t,ts]
	)
	# Constraint (4f)-1: (Hot) Thermal production sent to storage or grid must be less than technology's rated production
	# Constraint (4f)-1a: BoilerTechs
	if !isempty(p.BoilerTechs)
		if !isempty(p.SteamTurbineTechs)
            @constraint(m, BoilerTechProductionFlowCon[b in p.HotTES, t in p.BoilerTechs, ts in p.TimeStep],
                    m[:dvProductionToStorage][b,t,ts] + m[:dvThermalToSteamTurbine][t,ts]  <=
                    p.ProductionFactor[t,ts] * m[:dvThermalProduction][t,ts]
                    )
        else
            @constraint(m, BoilerTechProductionFlowCon[b in p.HotTES, t in p.BoilerTechs, ts in p.TimeStep],
                    m[:dvProductionToStorage][b,t,ts]  <=
                    p.ProductionFactor[t,ts] * m[:dvThermalProduction][t,ts]
                    )
        end
    end
	# Constraint (4f)-1b: SteamTurbineTechs
	if !isempty(p.SteamTurbineTechs)
		@constraint(m, SteamTurbineTechProductionFlowCon[b in p.HotTES, t in p.SteamTurbineTechs, ts in p.TimeStep],
			m[:dvProductionToStorage][b,t,ts] <= 
			p.ProductionFactor[t,ts] * m[:dvThermalProduction][t,ts]
			)
	end
	# Constraint (4f)-2: (Cold) Thermal production sent to storage or grid must be less than technology's rated production
	if !isempty(p.CoolingTechs)
		@constraint(m, CoolingTechProductionFlowCon[b in p.ColdTES, t in p.CoolingTechs, ts in p.TimeStep],
    	        m[:dvProductionToStorage][b,t,ts]  <=
				p.ProductionFactor[t,ts] * m[:dvThermalProduction][t,ts]
				)
	end
	# Constraint (4g): CHP Thermal production sent to storage or grid must be less than technology's rated production
	if !isempty(p.CHPTechs)
		if !isempty(p.SteamTurbineTechs)
            @constraint(m, CHPTechProductionFlowCon[b in p.HotTES, t in p.CHPTechs, ts in p.TimeStep],
                    m[:dvProductionToStorage][b,t,ts] + m[:dvProductionToWaste][t,ts] + m[:dvThermalToSteamTurbine][t,ts] <=
                    m[:dvThermalProduction][t,ts]
                    )
        else
            @constraint(m, CHPTechProductionFlowCon[b in p.HotTES, t in p.CHPTechs, ts in p.TimeStep],
                    m[:dvProductionToStorage][b,t,ts] + m[:dvProductionToWaste][t,ts] <=
                    m[:dvThermalProduction][t,ts]
                    )
        end
	end
	# Constraint (4h): Reconcile state-of-charge for electrical storage - with grid
	@constraint(m, ElecStorageInventoryCon[b in p.ElecStorage, ts in p.TimeStepsWithGrid],
		m[:dvStorageSOC][b,ts] == m[:dvStorageSOC][b,ts-1] + p.TimeStepScaling * (
			sum(p.ChargeEfficiency[t,b] * m[:dvProductionToStorage][b,t,ts] for t in p.ElectricTechs) +
			p.GridChargeEfficiency*m[:dvGridToStorage][ts] - m[:dvDischargeFromStorage][b,ts]/p.DischargeEfficiency[b]
		)
	)

	# Constraint (4i): Reconcile state-of-charge for electrical storage - no grid
	@constraint(m, ElecStorageInventoryConNoGrid[b in p.ElecStorage, ts in p.TimeStepsWithoutGrid],
		m[:dvStorageSOC][b,ts] == m[:dvStorageSOC][b,ts-1] + p.TimeStepScaling * (  
			sum(p.ChargeEfficiency[t,b] * m[:dvProductionToStorage][b,t,ts] for t in p.ElectricTechs)
			- m[:dvDischargeFromStorage][b,ts] / p.DischargeEfficiency[b]
		)
	)

	# Constraint (4j)-1: Reconcile state-of-charge for (hot) thermal storage
	@constraint(m, HotTESInventoryCon[b in p.HotTES, ts in p.TimeStep],
    	        m[:dvStorageSOC][b,ts] == m[:dvStorageSOC][b,ts-1] + p.TimeStepScaling * (
					sum(p.ChargeEfficiency[t,b] * m[:dvProductionToStorage][b,t,ts] for t in p.HeatingTechs) -
					m[:dvDischargeFromStorage][b,ts]/p.DischargeEfficiency[b] -
					p.StorageDecayRate[b] * m[:dvStorageCapEnergy][b]
					)
				)

	# Constraint (4j)-2: Reconcile state-of-charge for (cold) thermal storage
	@constraint(m, ColdTESInventoryCon[b in p.ColdTES, ts in p.TimeStep],
    	        m[:dvStorageSOC][b,ts] == m[:dvStorageSOC][b,ts-1] + p.TimeStepScaling * (
					sum(p.ChargeEfficiency[t,b] * m[:dvProductionToStorage][b,t,ts] for t in p.CoolingTechs) -
					m[:dvDischargeFromStorage][b,ts]/p.DischargeEfficiency[b] -
					p.StorageDecayRate[b] * m[:dvStorageCapEnergy][b]
					)
				)

	# Constraint (4k): Minimum state of charge
	@constraint(m, MinStorageLevelCon[b in p.Storage, ts in p.TimeStep],
		m[:dvStorageSOC][b,ts] >= p.StorageMinSOC[b] * m[:dvStorageCapEnergy][b]
	)

	#Constraint (4l): Dispatch to and from electrical storage is no greater than power capacity
	@constraint(m, ElecChargeLEQCapConAlt[b in p.ElecStorage, ts in p.TimeStepsWithGrid],
		m[:dvStorageCapPower][b] >=   m[:dvDischargeFromStorage][b,ts] +
			sum(m[:dvProductionToStorage][b,t,ts] for t in p.ElectricTechs) + m[:dvGridToStorage][ts]
	)
	#Constraint (4m): Dispatch to and from electrical storage is no greater than power capacity (no grid interaction)
	@constraint(m, DischargeLEQCapConNoGridAlt[b in p.ElecStorage, ts in p.TimeStepsWithoutGrid],
		m[:dvStorageCapPower][b] >= m[:dvDischargeFromStorage][b,ts] +
			sum(m[:dvProductionToStorage][b,t,ts] for t in p.ElectricTechs)
	)

	#Constraint (4n)-1: Dispatch to and from thermal storage is no greater than power capacity
	@constraint(m, DischargeLEQCapHotCon[b in p.HotTES, ts in p.TimeStep],
    	        m[:dvStorageCapPower][b] >= m[:dvDischargeFromStorage][b,ts] + sum(m[:dvProductionToStorage][b,t,ts] for t in p.HeatingTechs)
				)
	#Constraint (4n)-2: Dispatch to and from thermal storage is no greater than power capacity
	@constraint(m, DischargeLEQCapColdCon[b in p.ColdTES, ts in p.TimeStep],
    	        m[:dvStorageCapPower][b] >= m[:dvDischargeFromStorage][b,ts] + sum(m[:dvProductionToStorage][b,t,ts] for t in p.CoolingTechs)
				)

	#Constraint (4n): State of charge upper bound is storage system size
	@constraint(m, StorageEnergyMaxCapCon[b in p.Storage, ts in p.TimeStep],
		m[:dvStorageSOC][b,ts] <= m[:dvStorageCapEnergy][b]
	)


	if !p.StorageCanGridCharge
		for ts in p.TimeStepsWithGrid
			fix(m[:dvGridToStorage][ts], 0.0, force=true)
		end
	end
end


function add_thermal_load_constraints(m, p)
	### Constraint set (5) - hot and cold thermal loads
	##Constraint (5a): Cold thermal loads
	if !isempty(p.CoolingTechs)
		@constraint(m, ColdThermalLoadCon[ts in p.TimeStep],
				sum(p.ProductionFactor[t,ts] * m[:dvThermalProduction][t,ts] for t in p.CoolingTechs) +
				sum(m[:dvDischargeFromStorage][b,ts] for b in p.ColdTES) ==
				p.CoolingLoad[ts] -
				sum(p.GHPCoolingThermalServed[g,ts] * m[:binGHP][g] for g in p.GHPOptions) -
                sum(p.CoolingThermalReductionWithGHP[g,ts] * m[:binGHP][g] for g in p.GHPOptions) +
				sum(m[:dvProductionToStorage][b,t,ts] for b in p.ColdTES, t in p.CoolingTechs)
		)
	end

	##Constraint (5b): Hot thermal loads
	if !isempty(p.HeatingTechs)
        if !isempty(p.SteamTurbineTechs)
            @constraint(m, HotThermalLoadCon[ts in p.TimeStep],
                    sum(m[:dvThermalProduction][t,ts] - m[:dvThermalToSteamTurbine][t,ts] for t in p.CHPTechs) +
                    sum(m[:dvThermalProduction][t,ts] for t in p.SteamTurbineTechs) +
                    sum(p.ProductionFactor[t,ts] * (m[:dvThermalProduction][t,ts] - m[:dvThermalToSteamTurbine][t,ts]) for t in p.BoilerTechs) +
                    sum(m[:dvDischargeFromStorage][b,ts] for b in p.HotTES) ==
                    p.HeatingLoad[ts] * p.BoilerEfficiency["BOILER"] -
					sum(p.GHPHeatingThermalServed[g,ts] * m[:binGHP][g] for g in p.GHPOptions) -
                    sum(p.HeatingThermalReductionWithGHP[g,ts] * m[:binGHP][g] for g in p.GHPOptions) +
                    sum(m[:dvProductionToWaste][t,ts] for t in p.CHPTechs) +
                    sum(m[:dvProductionToStorage][b,t,ts] for b in p.HotTES, t in p.HeatingTechs)  +
                    sum(m[:dvThermalProduction][t,ts] for t in p.AbsorptionChillers) / p.AbsorptionChillerCOP
            )
        else
            @constraint(m, HotThermalLoadCon[ts in p.TimeStep],
                    sum(m[:dvThermalProduction][t,ts] for t in p.CHPTechs) +
                    sum(p.ProductionFactor[t,ts] * m[:dvThermalProduction][t,ts] for t in p.BoilerTechs) +
                    sum(m[:dvDischargeFromStorage][b,ts] for b in p.HotTES) ==
                    p.HeatingLoad[ts] * p.BoilerEfficiency["BOILER"] -
					sum(p.GHPHeatingThermalServed[g,ts] * m[:binGHP][g] for g in p.GHPOptions) -
                    sum(p.HeatingThermalReductionWithGHP[g,ts] * m[:binGHP][g] for g in p.GHPOptions) +
                    sum(m[:dvProductionToWaste][t,ts] for t in p.CHPTechs) +
                    sum(m[:dvProductionToStorage][b,t,ts] for b in p.HotTES, t in p.HeatingTechs)  +
                    sum(m[:dvThermalProduction][t,ts] for t in p.AbsorptionChillers) / p.AbsorptionChillerCOP
            )
        end
	end
end


function add_prod_incent_constraints(m, p)
	##Constraint (6a)-1: Production Incentive Upper Bound (unchanged)
	@constraint(m, ProdIncentUBCon[t in p.Tech],
		m[:dvProdIncent][t] <= m[:binProdIncent][t] * p.MaxProdIncent[t] * p.pwf_prod_incent[t] * p.two_party_factor)
	##Constraint (6a)-2: Production Incentive According to Production (updated)
	@constraint(m, IncentByProductionCon[t in p.Tech],
		m[:dvProdIncent][t] <= p.TimeStepScaling * p.ProductionIncentiveRate[t] * p.pwf_prod_incent[t] * p.two_party_factor *
			sum(p.ProductionFactor[t, ts] * m[:dvRatedProduction][t,ts] for ts in p.TimeStep)
	)
	##Constraint (6b): System size max to achieve production incentive
	@constraint(m, IncentBySystemSizeCon[t in p.Tech],
		m[:dvSize][t]  <= p.MaxSizeForProdIncent[t] + m[:NewMaxSize][t] * (1 - m[:binProdIncent][t]))

	if !isempty(p.Tech)
		m[:TotalProductionIncentive] = @expression(m, sum(m[:dvProdIncent][t] for t in p.Tech))
	else
		m[:TotalProductionIncentive] = 0
	end
end



function add_tech_size_constraints(m, p)
	# PV techs can be constrained by space available based on location at site (roof, ground, both)
	@constraint(m, TechMaxSizeByLocCon[loc in p.Location],
		sum( m[:dvSize][t] * p.TechToLocation[t, loc] for t in p.Tech) <= p.MaxSizesLocation[loc]
	)

	#Constraint (7a): Single Basic Technology Constraints
	@constraint(m, TechMaxSizeByClassCon[c in p.TechClass, t in p.TechsInClass[c]],
		m[:dvSize][t] <= m[:NewMaxSize][t] * m[:binSingleBasicTech][t,c]
		)
	##Constraint (7b): At most one Single Basic Technology per Class
	@constraint(m, TechClassMinSelectCon[c in p.TechClass],
		sum( m[:binSingleBasicTech][t,c] for t in p.TechsInClass[c] ) <= 1
		)
	##Constraint (7c): Minimum size for each tech class
	@constraint(m, TechClassMinSizeCon[c in p.TechClass],
				sum( m[:dvSize][t] for t in p.TechsInClass[c] ) >= p.TechClassMinSize[c]
			)

	## Constraint (7d): Non-turndown technologies are always at rated production
	@constraint(m, RenewableRatedProductionCon[t in p.TechsNoTurndown, ts in p.TimeStep],
		m[:dvRatedProduction][t,ts] == m[:dvSize][t]
	)

	##Constraint (7e): Derate factor limits production variable (separate from ProductionFactor)
    for ts in p.TimeStep
        @constraint(m, [t in p.Tech; !(t in p.TechsNoTurndown)],
            m[:dvRatedProduction][t,ts]  <= p.ElectricDerate[t,ts] * m[:dvSize][t]
        )
    end

	##Constraint (7_heating_prod_size): Production limit based on size for boiler
	if !isempty(p.BoilerTechs)
		@constraint(m, HeatingProductionCon[t in p.BoilerTechs, ts in p.TimeStep],
			m[:dvThermalProduction][t,ts] <= m[:dvSize][t]
		)
	end

	##Constraint (7_cooling_prod_size): Production limit based on size for chillers
	if !isempty(p.CoolingTechs)
		@constraint(m, CoolingProductionCon[t in p.CoolingTechs, ts in p.TimeStep],
			m[:dvThermalProduction][t,ts] <= m[:dvSize][t]
		)
	end

	##Constraint (7f)-1: Minimum segment size
	@constraint(m, SegmentSizeMinCon[t in p.Tech, k in p.Subdivision, s in 1:p.SegByTechSubdivision[k,t]],
		m[:dvSystemSizeSegment][t,k,s] >= p.SegmentMinSize[t,k,s] * m[:binSegmentSelect][t,k,s]
	)

	##Constraint (7f)-2: Maximum segment size
	@constraint(m, SegmentSizeMaxCon[t in p.Tech, k in p.Subdivision, s in 1:p.SegByTechSubdivision[k,t]],
		m[:dvSystemSizeSegment][t,k,s] <= p.SegmentMaxSize[t,k,s] * m[:binSegmentSelect][t,k,s]
	)

	##Constraint (7g):  Segments add up to system size
	@constraint(m, SegmentSizeAddCon[t in p.Tech, k in p.Subdivision],
		sum(m[:dvSystemSizeSegment][t,k,s] for s in 1:p.SegByTechSubdivision[k,t]) == m[:dvSize][t]
	)

	##Constraint (7h): At most one segment allowed
	@constraint(m, SegmentSelectCon[c in p.TechClass, t in p.TechsInClass[c], k in p.Subdivision],
		sum(m[:binSegmentSelect][t,k,s] for s in 1:p.SegByTechSubdivision[k,t]) <= m[:binSingleBasicTech][t,c]
	)

	##Constraint GHP: Choose up to 1 option
	if !isempty(p.GHPOptions)
		if p.RequireGHPPurchase == 1
			@constraint(m, GHPOptionSelect,
				sum(m[:binGHP][g] for g in p.GHPOptions) == 1
			)
		else
			@constraint(m, GHPOptionSelect,
				sum(m[:binGHP][g] for g in p.GHPOptions) <= 1
			)
		end
	end

	if p.CHPSupplementaryFireMaxRatio > 1.0
		##Constraint (7_supplementary_firing_size_a): size=0 if not chosen
		@constraint(m, CHPSupplementaryFiringSize_A[t in p.CHPTechs],
            m[:binUseSupplementaryFiring][t] => {m[:dvSupplementaryFiringCHPSize][t] <= m[:NewMaxSize][t]}
		)

		##Constraint (7_supplementary_firing_size_b): size=CHP if not chosen
		@constraint(m, CHPSupplementaryFiringSize_B[t in p.CHPTechs],
            m[:binUseSupplementaryFiring][t] => {m[:dvSupplementaryFiringCHPSize][t] >= m[:dvSize][t]}
		)
	else
		for t in p.CHPTechs
			fix(m[:dvSupplementaryFiringCHPSize][t], 0.0, force=true)
		end
	end
end


function add_load_balance_constraints(m, p)
	if !isempty(p.ExportTiers)
		@constraint(m, ElecLoadBalanceCon[ts in p.TimeStepsWithGrid],
			sum(p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvRatedProduction][t,ts] for t in p.ElectricTechs) +
			sum( m[:dvDischargeFromStorage][b,ts] for b in p.ElecStorage ) +
			sum( m[:dvGridPurchase][u,ts] for u in p.PricingTier ) ==
			sum( sum(m[:dvProductionToStorage][b,t,ts] for b in p.ElecStorage) +
				 sum(m[:dvProductionToGrid][t,u,ts] for u in p.ExportTiersByTech[t]) +
				 m[:dvProductionToCurtail][t,ts]
		    for t in p.ElectricTechs) +
			m[:dvGridToStorage][ts] +
            sum(m[:dvThermalProduction][t,ts] for t in p.ElectricChillers )/ p.ElectricChillerCOP +
            sum(m[:dvThermalProduction][t,ts] for t in p.AbsorptionChillers )/ p.AbsorptionChillerElecCOP +
			p.ElecLoad[ts] +
            sum(p.GHPElectricConsumed[g,ts] * m[:binGHP][g] for g in p.GHPOptions)
		)
	else
		@constraint(m, ElecLoadBalanceCon[ts in p.TimeStepsWithGrid],
			sum(p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvRatedProduction][t,ts] for t in p.ElectricTechs) +
			sum( m[:dvDischargeFromStorage][b,ts] for b in p.ElecStorage ) +
			sum( m[:dvGridPurchase][u,ts] for u in p.PricingTier ) ==
			sum( sum(m[:dvProductionToStorage][b,t,ts] for b in p.ElecStorage) +
				m[:dvProductionToCurtail][t,ts]
			for t in p.ElectricTechs) +
			m[:dvGridToStorage][ts] +
            sum(m[:dvThermalProduction][t,ts] for t in p.ElectricChillers )/ p.ElectricChillerCOP +
            sum(m[:dvThermalProduction][t,ts] for t in p.AbsorptionChillers )/ p.AbsorptionChillerElecCOP +
			p.ElecLoad[ts] +
            sum(p.GHPElectricConsumed[g,ts] * m[:binGHP][g] for g in p.GHPOptions)
		)
	end
	
	##Constraint (8b): Electrical Load Balancing without Grid
	@constraint(m, ElecLoadBalanceNoGridCon[ts in p.TimeStepsWithoutGrid],
		sum(p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvRatedProduction][t,ts] for t in p.ElectricTechs) +
		sum( m[:dvDischargeFromStorage][b,ts] for b in p.ElecStorage )  ==
		sum( sum(m[:dvProductionToStorage][b,t,ts] for b in p.ElecStorage) + 
			 m[:dvProductionToCurtail][t,ts]
		for t in p.ElectricTechs) +
        sum(m[:dvThermalProduction][t,ts] for t in p.ElectricChillers )/ p.ElectricChillerCOP +
        sum(m[:dvThermalProduction][t,ts] for t in p.AbsorptionChillers )/ p.AbsorptionChillerElecCOP +
		(p.ElecLoad[ts] * m[:dvOffgridLoadServedFraction][ts])
	)

	if !p.OffGridFlag # fix dvOffgridLoadServedFraction to 100% for "on-grid" analyses
		for ts in p.TimeStepsWithoutGrid
			fix(m[:dvOffgridLoadServedFraction][ts], 1.0, force=true)
		end
	else
		@constraint(m, sum(m[:dvOffgridLoadServedFraction][ts] * p.ElecLoad[ts] for ts in p.TimeStepsWithoutGrid) >=
			sum(p.ElecLoad) * p.MinLoadMetPct
			# p.AnnualElecLoadkWh * p.MinLoadMetPct
		)
	end
end


function add_spinning_reserve_constraints(m, p)
	# Calculate spinning reserve required
	# 1. Production going to load from Techs Providing SR
	m[:ProductionToLoadSR] = @expression(m, [t in p.TechsProvidingSR, ts in p.TimeStepsWithoutGrid],
		p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvRatedProduction][t,ts] -
        sum(m[:dvProductionToStorage][b, t, ts] for b in p.ElecStorage) -
        m[:dvProductionToCurtail][t, ts]
	)
	# 2. Total SR required by TechsRequiringSR & Load
	m[:SRrequired] = @expression(m, [ts in p.TimeStepsWithoutGrid],
		 sum(m[:ProductionToLoadSR][t,ts] * p.SRrequiredPctTechs[t] for t in p.TechsRequiringSR)
         + p.ElecLoad[ts] * m[:dvOffgridLoadServedFraction][ts] * p.SRrequiredPctLoad
	)
	# 3. Spinning reserve provided - battery
	@constraint(m, [b in p.ElecStorage, ts in p.TimeStepsWithoutGrid],
		m[:dvSRbatt][b,ts] <= (m[:dvStorageSOC][b,ts-1] - p.StorageMinSOC[b] * m[:dvStorageCapEnergy][b]) / p.TimeStepScaling - (m[:dvDischargeFromStorage][b,ts] / p.DischargeEfficiency[b])
	)
	@constraint(m, [b in p.ElecStorage, ts in p.TimeStepsWithoutGrid],
		m[:dvSRbatt][b,ts] <= m[:dvStorageCapPower][b] - m[:dvDischargeFromStorage][b,ts] / p.DischargeEfficiency[b]
	)
	# 4. Spinning reserve provided - TechsProvidingSR
	@constraint(m, [t in p.TechsProvidingSR, ts in p.TimeStepsWithoutGrid],
		 m[:dvSR][t,ts] <= (p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvSize][t] -
		                   m[:ProductionToLoadSR][t,ts]) * (1 - p.SRrequiredPctTechs[t])
	)
	# 5. Upper bound on dvSR
	@constraint(m, [t in p.TechsProvidingSR, ts in p.TimeStepsWithoutGrid],
		m[:dvSR][t,ts] <= m[:binTechIsOnInTS][t,ts] * m[:NewMaxSize][t]
	)
	m[:SRprovided] = @expression(m, [ts in p.TimeStepsWithoutGrid],
		sum(m[:dvSR][t,ts] for t in p.TechsProvidingSR)
        + sum(m[:dvSRbatt][b,ts] for b in p.ElecStorage)
	)
	# 6. SR provided must be greater than SR required
	@constraint(m, [ts in p.TimeStepsWithoutGrid],
        m[:SRprovided][ts] >= m[:SRrequired][ts]
	)

end

function add_storage_grid_constraints(m, p)
	##Constraint (8c): Grid-to-storage no greater than grid purchases
	@constraint(m, GridToStorageCon[ts in p.TimeStepsWithGrid],
		sum( m[:dvGridPurchase][u,ts] for u in p.PricingTier)  >= m[:dvGridToStorage][ts]
	)
end


function add_prod_grid_constraints(m, p)
	##Constraint (8e): Production-to-grid no greater than production
	@constraint(m, ProductionToGridCon[t in p.Tech, ts in p.TimeStepsWithGrid],
		p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvRatedProduction][t,ts] >=
	  	sum(m[:dvProductionToGrid][t,u,ts] for u in p.ExportTiersByTech[t]) + m[:dvProductionToCurtail][t,ts]
	)

	# Cannot export power while importing from Grid
	@constraint(m, NoGridPurchasesBinary[ts in p.TimeStep],
        m[:binNoGridPurchases][ts] => {
            sum(m[:dvGridPurchase][u,ts] for u in p.PricingTier) + m[:dvGridToStorage][ts] <= 0
        }
	)

	@constraint(m, ExportOnlyAfterSiteLoadMetCon[ts in p.TimeStep],
		!m[:binNoGridPurchases][ts] => {
            sum(m[:dvProductionToGrid][t,u,ts] for t in p.Tech, u in p.ExportTiers) <= 0
        }
	)
end


function add_curtail_constraint(m, p)
	# NOTE: not allowing DER to curtail during an outage can lead to an infeasible problem
	for t in p.TechsCannotCurtail, ts in p.TimeStep
		fix(m[:dvProductionToCurtail][t, ts], 0.0, force=true)
	end
end


function add_NMIL_constraints(m, p)
	#Constraint (9a): exactly one net-metering regime must be selected
	@constraint(m, sum(m[:binNMLorIL][n] for n in p.NMILRegime) == 1)

	##Constraint (9b): Maximum system sizes for each net-metering regime
	@constraint(m, NetMeterSizeLimit[n in p.NMILRegime],
		sum(p.TurbineDerate[t] * m[:dvSize][t]
		for t in p.TechsByNMILRegime[n]) <= p.NMILLimits[n] * m[:binNMLorIL][n]
	)
end


function add_nem_constraint(m, p)
	@constraint(m, GridSalesLimit,
		sum(m[:dvProductionToGrid][t, "NEM", ts] for t in p.TechsByExportTier["NEM"], ts in p.TimeStep)
		<= sum(m[:dvGridPurchase][u,ts] for u in p.PricingTier, ts in p.TimeStep)
	)
end


function add_no_grid_export_constraint(m, p)
	for ts in p.TimeStepsWithoutGrid
		for u in p.ExportTiers
			for t in p.TechsByExportTier[u]
				fix(m[:dvProductionToGrid][t, u, ts], 0.0, force=true)
			end
		end
	end
end


function add_energy_price_constraints(m, p)
	##Constraint (10a): Usage limits by pricing tier, by month
	@constraint(m, [u in p.PricingTier, mth in p.Month],
		p.TimeStepScaling * sum( m[:dvGridPurchase][u, ts] for ts in p.TimeStepRatchetsMonth[mth] ) <= m[:binEnergyTier][mth, u] * m[:NewMaxUsageInTier][mth,u])
	##Constraint (10b): Ordering of pricing tiers
	@constraint(m, [u in 2:p.FuelBinCount, mth in p.Month],   #Need to fix, update purchase vs. sales pricing tiers
		m[:binEnergyTier][mth, u] - m[:binEnergyTier][mth, u-1] <= 0)
	## Constraint (10c): One tier must be full before any usage in next tier
	@constraint(m, [u in 2:p.FuelBinCount, mth in p.Month],
		m[:binEnergyTier][mth, u] * m[:NewMaxUsageInTier][mth,u-1] - sum( m[:dvGridPurchase][u-1, ts] for ts in p.TimeStepRatchetsMonth[mth] ) <= 0
	)
	m[:TotalEnergyChargesUtil] = @expression(m, p.pwf_e * p.TimeStepScaling *
		sum( p.ElecRate[u,ts] * m[:dvGridPurchase][u,ts] for ts in p.TimeStep, u in p.PricingTier)
	)
end


function add_monthly_demand_charge_constraints(m, p)
	## Constraint (11a): Upper bound on peak electrical power demand by tier, by month, if tier is selected (0 o.w.)
	@constraint(m, [n in p.DemandMonthsBin, mth in p.Month],
		m[:dvPeakDemandEMonth][mth,n] <= m[:NewMaxDemandMonthsInTier][mth,n] * m[:binDemandMonthsTier][mth,n])

	## Constraint (11b): Monthly peak electrical power demand tier ordering
	@constraint(m, [mth in p.Month, n in 2:p.DemandMonthsBinCount],
		m[:binDemandMonthsTier][mth, n] <= m[:binDemandMonthsTier][mth, n-1])

	## Constraint (11c): One monthly peak electrical power demand tier must be full before next one is active
	@constraint(m, [mth in p.Month, n in 2:p.DemandMonthsBinCount],
		m[:binDemandMonthsTier][mth, n] * m[:NewMaxDemandMonthsInTier][mth,n-1] <= m[:dvPeakDemandEMonth][mth, n-1])

	## Constraint (11d): Monthly peak demand is >= demand at each hour in the month
	if p.CHPDoesNotReduceDemandCharges == 1
		@constraint(m, [mth in p.Month, ts in p.TimeStepRatchetsMonth[mth]],
				sum( m[:dvPeakDemandEMonth][mth, n] for n in p.DemandMonthsBin ) >=
				sum( m[:dvGridPurchase][u, ts] for u in p.PricingTier ) +
				 sum(p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvRatedProduction][t,ts] for t in p.CHPTechs) -
				 sum(m[:dvProductionToStorage][t,ts] for t in p.CHPTechs) -
				 sum(sum(m[:dvProductionToGrid][t,u,ts] for u in p.ExportTiersByTech[t]) for t in p.CHPTechs)
		)
	else
		@constraint(m, [mth in p.Month, ts in p.TimeStepRatchetsMonth[mth]],
			sum( m[:dvPeakDemandEMonth][mth, n] for n in p.DemandMonthsBin ) >=
			sum( m[:dvGridPurchase][u, ts] for u in p.PricingTier )
		)
	end

	if !isempty(p.DemandRatesMonth)
		m[:DemandFlatCharges] = @expression(m, p.pwf_e * sum( p.DemandRatesMonth[mth,n] * m[:dvPeakDemandEMonth][mth,n] for mth in p.Month, n in p.DemandMonthsBin) )
	else
		m[:DemandFlatCharges] = 0
	end
end


function add_tou_demand_charge_constraints(m, p)
	## Constraint (12a): Upper bound on peak electrical power demand by tier, by ratchet, if tier is selected (0 o.w.)
	@constraint(m, [r in p.Ratchets, e in p.DemandBin],
		m[:dvPeakDemandE][r, e] <= m[:NewMaxDemandInTier][r,e] * m[:binDemandTier][r, e])

	## Constraint (12b): Ratchet peak electrical power ratchet tier ordering
	@constraint(m, [r in p.Ratchets, e in 2:p.DemandBinCount],
		m[:binDemandTier][r, e] <= m[:binDemandTier][r, e-1])

	## Constraint (12c): One ratchet peak electrical power demand tier must be full before next one is active
	@constraint(m, [r in p.Ratchets, e in 2:p.DemandBinCount],
		m[:binDemandTier][r, e] * m[:NewMaxDemandInTier][r,e-1] <= m[:dvPeakDemandE][r, e-1])

	## Constraint (12d): Ratchet peak demand is >= demand at each hour in the ratchet`
	@constraint(m, [r in p.Ratchets, ts in p.TimeStepRatchets[r]],
		sum( m[:dvPeakDemandE][r, e] for e in p.DemandBin ) >=
		sum( m[:dvGridPurchase][u, ts] for u in p.PricingTier )
	)

	if p.DemandLookbackRange != 0  # then the dvPeakDemandELookback varies by month

		##Constraint (12e): dvPeakDemandELookback is the highest peak demand in DemandLookbackMonths
		for mth in p.Month
			if mth > p.DemandLookbackRange
				@constraint(m, [lm in 1:p.DemandLookbackRange, ts in p.TimeStepRatchetsMonth[mth - lm]],
					m[:dvPeakDemandELookback][mth]
					≥ sum( m[:dvGridPurchase][u, ts] for u in p.PricingTier )
				)
			else  # need to handle rollover months
				for lm in 1:p.DemandLookbackRange
					lkbkmonth = mth - lm
					if lkbkmonth ≤ 0
						lkbkmonth += 12
					end
					@constraint(m, [ts in p.TimeStepRatchetsMonth[lkbkmonth]],
						m[:dvPeakDemandELookback][mth]
						≥ sum( m[:dvGridPurchase][u, ts] for u in p.PricingTier )
					)
				end
			end
		end

		##Constraint (12f): Ratchet peak demand charge is bounded below by lookback
		@constraint(m, [mth in p.Month],
			sum( m[:dvPeakDemandEMonth][mth, n] for n in p.DemandMonthsBin ) >=
			p.DemandLookbackPercent * m[:dvPeakDemandELookback][mth]
		)

	else  # dvPeakDemandELookback does not vary by month

		##Constraint (12e): dvPeakDemandELookback is the highest peak demand in DemandLookbackMonths
		@constraint(m, [lm in p.DemandLookbackMonths],
			m[:dvPeakDemandELookback][1] >= sum(m[:dvPeakDemandEMonth][lm, n] for n in p.DemandMonthsBin)
		)

		##Constraint (12f): Ratchet peak demand charge is bounded below by lookback
		@constraint(m, [mth in p.Month],
			sum( m[:dvPeakDemandEMonth][mth, n] for n in p.DemandMonthsBin ) >=
			p.DemandLookbackPercent * m[:dvPeakDemandELookback][1]
		)
	end

	if !isempty(p.DemandRates)
		m[:DemandTOUCharges] = @expression(m, p.pwf_e * sum( p.DemandRates[r,e] * m[:dvPeakDemandE][r,e] for r in p.Ratchets, e in p.DemandBin) )
	else
		m[:DemandTOUCharges] = 0.0
	end
end

function add_coincident_peak_charge_constraints(m, p)
	## Constraint (14a): in each coincident peak period, charged CP demand is the max of demand in all CP timesteps
	@constraint(m, [prd in p.CPPeriod, ts in p.CoincidentPeakLoadTimeSteps[prd,:][p.CoincidentPeakLoadTimeSteps[prd,:].!=nothing]],
		m[:dvPeakDemandCP][prd] >= sum(m[:dvGridPurchase][u,ts] for u in p.PricingTier)
	)
	m[:TotalCPCharges] = @expression(m, p.pwf_e * sum( p.CoincidentPeakRates[prd] * m[:dvPeakDemandCP][prd] for prd in p.CPPeriod) )
end

function add_util_fixed_and_min_charges(m, p)

    m[:TotalFixedCharges] = p.pwf_e * p.FixedMonthlyCharge * 12

	### Constraint (13): Annual minimum charge adder
	if p.AnnualMinCharge > 12 * p.MonthlyMinCharge
        m[:TotalMinCharge] = p.AnnualMinCharge
    else
        m[:TotalMinCharge] = 12 * p.MonthlyMinCharge
    end

	if m[:TotalMinCharge] >= 1e-2
        @constraint(m, MinChargeAddCon, m[:MinChargeAdder] >= m[:TotalMinCharge] - ( 
			m[:TotalEnergyChargesUtil] + m[:TotalDemandCharges] + m[:TotalCPCharges] + m[:TotalExportBenefit] + m[:TotalFixedCharges])
		)
	else
		@constraint(m, MinChargeAddCon, m[:MinChargeAdder] == 0)

	end
end

function add_chp_hourly_om_charges(m, p)
	#Constraint CHP-hourly-om-a: om per hour, per time step >= per_unit_size_cost * size for when on, >= zero when off
	@constraint(m, CHPHourlyOMBySizeA[t in p.CHPTechs, ts in p.TimeStep],
					p.OMcostPerUnitHourPerSize[t] * m[:dvSize][t] -
					m[:NewMaxSize][t] * p.OMcostPerUnitHourPerSize[t] * (1-m[:binTechIsOnInTS][t,ts])
					   <= m[:dvOMByHourBySizeCHP][t, ts]
					)
	#Constraint CHP-hourly-om-b: om per hour, per time step <= per_unit_size_cost * size for each hour
	@constraint(m, CHPHourlyOMBySizeB[t in p.CHPTechs, ts in p.TimeStep],
					p.OMcostPerUnitHourPerSize[t] * m[:dvSize][t]
					   >= m[:dvOMByHourBySizeCHP][t, ts]
					)
	#Constraint CHP-hourly-om-c: om per hour, per time step <= zero when off, <= per_unit_size_cost*max_size
	@constraint(m, CHPHourlyOMBySizeC[t in p.CHPTechs, ts in p.TimeStep],
					m[:NewMaxSize][t] * p.OMcostPerUnitHourPerSize[t] * m[:binTechIsOnInTS][t,ts]
					   >= m[:dvOMByHourBySizeCHP][t, ts]
					)
end

function add_cost_function(m, p)
	m[:REcosts] = @expression(m,

		# Capital Costs
		m[:TotalTechCapCosts] + m[:TotalStorageCapCosts] + m[:GHPCapCosts] +

		## Fixed O&M, tax deductible for owner
		(m[:TotalPerUnitSizeOMCosts] + m[:GHPOMCosts]) * m[:r_tax_fraction_owner] +

        ## Variable O&M, tax deductible for owner
		(m[:TotalPerUnitProdOMCosts] + m[:TotalHourlyCHPOMCosts]) * m[:r_tax_fraction_owner] +

		# Utility Bill, tax deductible for offtaker
		(m[:TotalEnergyChargesUtil] + m[:TotalDemandCharges] + m[:TotalCPCharges] + m[:TotalExportBenefit] + m[:TotalFixedCharges] + 0.999*m[:MinChargeAdder]) * m[:r_tax_fraction_offtaker] +
        
		# CHP Standby Charges
		m[:TotalCHPStandbyCharges] * m[:r_tax_fraction_offtaker] +

        ## Total Fuel Costs for all fuel-burning techs, tax deductible for offtaker
        m[:TotalFuelCharges] * m[:r_tax_fraction_offtaker] -

        # Subtract Incentives, which are taxable
		m[:TotalProductionIncentive] * m[:r_tax_fraction_owner]
	)
    #= Note: 0.9999*m[:MinChargeAdder] in Obj b/c when m[:TotalMinCharge] > (TotalEnergyCharges + m[:TotalDemandCharges] + TotalExportBenefit + m[:TotalFixedCharges])
		it is arbitrary where the min charge ends up (eg. could be in m[:TotalDemandCharges] or m[:MinChargeAdder]).
		0.0001*m[:MinChargeAdder] is added back into LCC when writing to results.  =#

	# Add climate costs
	if p.Include_climate_in_objective # if user selects to include climate in objective
		add_to_expression!(m[:REcosts], m[:Lifecycle_Emissions_Cost_CO2]) 
	end

	# Add Health costs (NOx, SO2, PM2.5)
	if p.Include_health_in_objective
		add_to_expression!(m[:REcosts], m[:Lifecycle_Emissions_Cost_Health])
	end

end

# Renewable electricity calculation
function add_re_elec_calcs(m,p)
	
	# User-selected RE electricity accounting methodology:
	if p.IncludeExportedREElecinTotal
		include_exported_re_elec_in_total = 1
	else
		include_exported_re_elec_in_total = 0
	end

	# Steam turbine RE elec calculations 
	if isempty(p.SteamTurbineTechs)
		SteamTurbineAnnualREEleckWh = 0 
    else  
		# Note: SteamTurbine's input p.TechPercentRE = 0 because it is actually a decision variable dependent on fraction of steam generated by RE fuel
		SteamTurbinePercentREEstimate = @expression(m,
			sum(p.TechPercentRE[tst] for tst in p.TechCanSupplySteamTurbine) / length(p.TechCanSupplySteamTurbine))
		# Note: Steam turbine battery losses, curtailment, and exported RE terms are only accurate if all techs that can supply ST 
		#		have equal RE%, otherwise it is an approximation because the general equation is non linear. 
		SteamTurbineAnnualREEleckWh = @expression(m,p.TimeStepScaling *
			p.STElecOutToThermInRatio * sum(m[:dvThermalToSteamTurbine][tst,ts]*p.TechPercentRE[tst] for ts in p.TimeStep, tst in p.TechCanSupplySteamTurbine) # plus steam turbine RE generation 
			- sum(m[:dvProductionToStorage][b,t,ts] * SteamTurbinePercentREEstimate * (1-p.ChargeEfficiency[t,b]*p.DischargeEfficiency[b]) for t in p.SteamTurbineTechs, b in p.ElecStorage, ts in p.TimeStep) # minus battery storage losses from RE from steam turbine
			- sum(m[:dvProductionToCurtail][t,ts] * SteamTurbinePercentREEstimate for t in p.SteamTurbineTechs, ts in p.TimeStep) # minus curtailment.
			- (1-include_exported_re_elec_in_total)*sum(m[:dvProductionToGrid][t,u,ts]*SteamTurbinePercentREEstimate for t in p.SteamTurbineTechs,  u in p.ExportTiersByTech[t], ts in p.TimeStep)) # minus exported RE from steam turbine, if RE accounting method = 0.
	end

	m[:AnnualREEleckWh] = @expression(m,p.TimeStepScaling*
        (sum(p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvRatedProduction][t,ts] * p.TechPercentRE[t] for t in p.ElectricTechs, ts in p.TimeStep) #total RE elec generation, excl steam turbine
        - sum(m[:dvProductionToStorage][b,t,ts]*p.TechPercentRE[t]*(1-p.ChargeEfficiency[t,b]*p.DischargeEfficiency[b]) for t in p.ElectricTechs, b in p.ElecStorage, ts in p.TimeStep) #minus battery efficiency losses
        - sum(m[:dvProductionToCurtail][t,ts]*p.TechPercentRE[t] for t in p.ElectricTechs, ts in p.TimeStep) # minus curtailment.
        - (1-include_exported_re_elec_in_total)*sum(m[:dvProductionToGrid][t,u,ts]*p.TechPercentRE[t] for t in p.ElectricTechs,  u in p.ExportTiersByTech[t], ts in p.TimeStep)) # minus exported RE, if RE accounting method = 0.
		+ SteamTurbineAnnualREEleckWh ) # SteamTurbine RE Elec, already adjusted for p.TimeStepScaling
		
    # Note: if battery ends up being allowed to discharge to grid, need to make sure only RE that is being consumed onsite is counted so battery doesn't become a back door for RE to grid.
	# Note: calculations currently do not ascribe any renewable energy attribute to grid-purchased electricity

	m[:AnnualEleckWh] = @expression(m,p.TimeStepScaling*
		(sum(p.ElecLoad[ts] for ts in p.TimeStep) # input elec load
		+ sum(m[:dvThermalProduction][t,ts] for t in p.ElectricChillers, ts in p.TimeStep )/ p.ElectricChillerCOP # electric chiller elec load
		+ sum(m[:dvThermalProduction][t,ts] for t in p.AbsorptionChillers, ts in p.TimeStep )/ p.AbsorptionChillerElecCOP # absorportion chiller elec load
		+ sum(p.GHPElectricConsumed[g,ts] * m[:binGHP][g] for g in p.GHPOptions, ts in p.TimeStep))) # GHP elec load

end

#Renewable electricity constraints
function add_re_elec_constraints(m,p)
	if !isnothing(p.MinAnnualPercentREElec)
		@constraint(m, MinREElecCon, m[:AnnualREEleckWh] >= p.MinAnnualPercentREElec*m[:AnnualEleckWh])
	end
	if !isnothing(p.MaxAnnualPercentREElec)
		@constraint(m, MaxREElecCon, m[:AnnualREEleckWh] <= p.MaxAnnualPercentREElec*m[:AnnualEleckWh])
	end
end

#Renewable heat calculations
function add_re_tot_calcs(m,p)

	# Steam turbine RE heat calculations 
	if !isempty(p.HeatingTechs)
		if isempty(p.SteamTurbineTechs)
			AnnualSteamTurbineREThermOut = 0 
			AnnualRESteamToSteamTurbine = 0
			AnnualSteamToSteamTurbine = 0
		else  
			# Note: SteamTurbine's input p.TechPercentRE = 0 because it is actually a decision variable dependent on fraction of steam generated by RE fuel
			# SteamTurbine RE battery losses, RE curtailment, and exported RE terms are based on an approximation of percent RE because the general equation is nonlinear
			# Thus, SteamTurbine %RE is only accurate if all techs that can supply ST have equal %RE fuel or provide equal quantities of steam to the steam turbine
			SteamTurbinePercentREEstimate = @expression(m,
				sum(p.TechPercentRE[tst] for tst in p.TechCanSupplySteamTurbine) / length(p.TechCanSupplySteamTurbine))
			AnnualSteamTurbineREThermOut = @expression(m,p.TimeStepScaling *
				p.STThermOutToThermInRatio * sum(m[:dvThermalToSteamTurbine][tst,ts]*p.TechPercentRE[tst] for ts in p.TimeStep, tst in p.TechCanSupplySteamTurbine) # plus steam turbine RE generation 
				- sum(m[:dvProductionToStorage][b,t,ts] * SteamTurbinePercentREEstimate * (1-p.ChargeEfficiency[t,b]*p.DischargeEfficiency[b]) for t in p.SteamTurbineTechs, b in p.HotTES, ts in p.TimeStep)) # minus battery storage losses from RE heat from steam turbine; note does not account for p.DecayRate
			AnnualRESteamToSteamTurbine = @expression(m,p.TimeStepScaling *
				sum(m[:dvThermalToSteamTurbine][tst,ts]*p.TechPercentRE[tst] for ts in p.TimeStep, tst in p.TechCanSupplySteamTurbine)) # steam to steam turbine from other techs- need to subtract this out from the total 	
			AnnualSteamToSteamTurbine = @expression(m,p.TimeStepScaling *
				sum(m[:dvThermalToSteamTurbine][tst,ts] for ts in p.TimeStep, tst in p.TechCanSupplySteamTurbine)) # steam to steam turbine from other techs- need to subtract this out from the total 	
		end

		# Renewable heat (RE steam/hot water heat that is not being used to generate electricity)
		AnnualREHeatkWh = @expression(m,p.TimeStepScaling*
			(sum(p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvThermalProduction][t,ts] * p.TechPercentRE[t] for t in p.HeatingTechs, ts in p.TimeStep) #total RE heat generation (excl steam turbine, GHP)
			- sum(m[:dvProductionToWaste][t,ts]* p.TechPercentRE[t] for t in p.CHPTechs, ts in p.TimeStep) #minus CHP waste heat
			+ sum(m[:dvSupplementaryThermalProduction][t,ts] * p.TechPercentRE[t] for t in p.CHPTechs, ts in p.TimeStep) # plus CHP supplemental firing thermal generation
			- sum(m[:dvProductionToStorage][b,t,ts]*p.TechPercentRE[t]*(1-p.ChargeEfficiency[t,b]*p.DischargeEfficiency[b]) for t in p.HeatingTechs, b in p.HotTES, ts in p.TimeStep) ) #minus thermal storage losses, note does not account for p.DecayRate
			- AnnualRESteamToSteamTurbine # minus RE steam feeding steam turbine, adjusted by p.TimeStepScaling 
			+ AnnualSteamTurbineREThermOut) #plus steam turbine RE generation, adjusted for storage losses, adjusted by p.TimeStepScaling (not included in first line because p.TechPercentRE for SteamTurbine is 0)

		# Total heat (steam/hot water heat that is not being used to generate electricity)
		AnnualHeatkWh = @expression(m,p.TimeStepScaling*
			(sum(p.ProductionFactor[t,ts] * p.LevelizationFactor[t] * m[:dvThermalProduction][t,ts] for t in p.HeatingTechs, ts in p.TimeStep) #total heat generation (need to see how GHP fits into this)
			- sum(m[:dvProductionToWaste][t,ts] for t in p.CHPTechs, ts in p.TimeStep) #minus CHP waste heat
			+ sum(m[:dvSupplementaryThermalProduction][t,ts] for t in p.CHPTechs, ts in p.TimeStep) # plus CHP supplemental firing thermal generation
			- sum(m[:dvProductionToStorage][b,t,ts]*(1-p.ChargeEfficiency[t,b]*p.DischargeEfficiency[b]) for t in p.HeatingTechs, b in p.HotTES, ts in p.TimeStep)) #minus thermal storage losses
			- AnnualSteamToSteamTurbine) # minus steam going to SteamTurbine; already adjusted by p.TimeStepScaling
	else
		AnnualREHeatkWh = 0 
		AnnualHeatkWh = 0
	end 
	m[:AnnualRETotkWh] = @expression(m,m[:AnnualREEleckWh] + AnnualREHeatkWh)
	m[:AnnualTotkWh] = @expression(m,m[:AnnualEleckWh] + AnnualHeatkWh)
	
end
 
### Year 1 Emissions Calculations
function add_yr1_emissions_calcs(m,p)
	# Components:
	yr1_emissions_from_fuelburningtechs_lbs_CO2, yr1_emissions_from_fuelburningtechs_lbs_NOx, yr1_emissions_from_fuelburningtechs_lbs_SO2, yr1_emissions_from_fuelburningtechs_lbs_PM25 = calc_yr1_emissions_from_onsite_fuel(m,p; tech_array=p.FuelBurningTechs)
	yr1_emissions_from_boilertechs_lbs_CO2, yr1_emissions_from_boilertechs_lbs_NOx, yr1_emissions_from_boilertechs_lbs_SO2, yr1_emissions_from_boilertechs_lbs_PM25 = calc_yr1_emissions_from_onsite_fuel(m,p; tech_array=p.BoilerTechs)
	m[:yr1_emissions_onsite_fuel_lbs_CO2] = yr1_emissions_from_fuelburningtechs_lbs_CO2 + yr1_emissions_from_boilertechs_lbs_CO2
	m[:yr1_emissions_onsite_fuel_lbs_NOx] = yr1_emissions_from_fuelburningtechs_lbs_NOx + yr1_emissions_from_boilertechs_lbs_NOx
	m[:yr1_emissions_onsite_fuel_lbs_SO2] = yr1_emissions_from_fuelburningtechs_lbs_SO2 + yr1_emissions_from_boilertechs_lbs_SO2
	m[:yr1_emissions_onsite_fuel_lbs_PM25] = yr1_emissions_from_fuelburningtechs_lbs_PM25 + yr1_emissions_from_boilertechs_lbs_PM25

	m[:yr1_emissions_from_elec_grid_lbs_CO2], m[:yr1_emissions_from_elec_grid_lbs_NOx], m[:yr1_emissions_from_elec_grid_lbs_SO2], m[:yr1_emissions_from_elec_grid_lbs_PM25]  = calc_yr1_emissions_from_elec_grid_purchase(m,p)
	m[:yr1_emissions_offset_from_elec_exports_lbs_CO2], m[:yr1_emissions_offset_from_elec_exports_lbs_NOx], m[:yr1_emissions_offset_from_elec_exports_lbs_SO2], m[:yr1_emissions_offset_from_elec_exports_lbs_PM25] = calc_yr1_emissions_offset_from_elec_exports(m,p;tech_array=p.ElectricTechs)

	# Total:
	if p.IncludeExportedElecEmissionsInTotal
		include_exported_elec_emissions_in_total = 1
	else
		include_exported_elec_emissions_in_total = 0
	end
	#"net" indicates net of what is getting counted, based on user selection of whether or not to include
	m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_CO2] = m[:yr1_emissions_from_elec_grid_lbs_CO2] - include_exported_elec_emissions_in_total*m[:yr1_emissions_offset_from_elec_exports_lbs_CO2]
	m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_NOx] = m[:yr1_emissions_from_elec_grid_lbs_NOx] - include_exported_elec_emissions_in_total*m[:yr1_emissions_offset_from_elec_exports_lbs_NOx]
	m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_SO2] = m[:yr1_emissions_from_elec_grid_lbs_SO2] - include_exported_elec_emissions_in_total*m[:yr1_emissions_offset_from_elec_exports_lbs_SO2]
	m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_PM25] = m[:yr1_emissions_from_elec_grid_lbs_PM25] - include_exported_elec_emissions_in_total*m[:yr1_emissions_offset_from_elec_exports_lbs_PM25]

	m[:EmissionsYr1_Total_LbsCO2] = m[:yr1_emissions_onsite_fuel_lbs_CO2] + m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_CO2]
	m[:EmissionsYr1_Total_LbsNOx] = m[:yr1_emissions_onsite_fuel_lbs_NOx] + m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_NOx]
	m[:EmissionsYr1_Total_LbsSO2] = m[:yr1_emissions_onsite_fuel_lbs_SO2] + m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_SO2]
	m[:EmissionsYr1_Total_LbsPM25] = m[:yr1_emissions_onsite_fuel_lbs_PM25] + m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_PM25]

end

function calc_yr1_emissions_from_onsite_fuel(m,p; tech_array=p.FuelBurningTechs) # also run this with p.BoilerTechs
	yr1_emissions_onsite_fuel_lbs_CO2 = @expression(m,p.TimeStepScaling*
		sum(m[:dvFuelUsage][t,ts]*p.TechEmissionsFactors_CO2[t] for t in tech_array, ts in p.TimeStep))

	yr1_emissions_onsite_fuel_lbs_NOx = @expression(m,p.TimeStepScaling*
		sum(m[:dvFuelUsage][t,ts]*p.TechEmissionsFactors_NOx[t] for t in tech_array, ts in p.TimeStep))

	yr1_emissions_onsite_fuel_lbs_SO2 = @expression(m,p.TimeStepScaling*
		sum(m[:dvFuelUsage][t,ts]*p.TechEmissionsFactors_SO2[t] for t in tech_array, ts in p.TimeStep))

	yr1_emissions_onsite_fuel_lbs_PM25 = @expression(m,p.TimeStepScaling*
		sum(m[:dvFuelUsage][t,ts]*p.TechEmissionsFactors_PM25[t] for t in tech_array, ts in p.TimeStep))

	return yr1_emissions_onsite_fuel_lbs_CO2, yr1_emissions_onsite_fuel_lbs_NOx, yr1_emissions_onsite_fuel_lbs_SO2, yr1_emissions_onsite_fuel_lbs_PM25
end
function calc_yr1_emissions_from_elec_grid_purchase(m,p)
	yr1_emissions_from_elec_grid_lbs_CO2 = @expression(m,p.TimeStepScaling*
		sum(m[:dvGridPurchase][u,ts]*p.GridEmissionsFactor_CO2[ts] for ts in p.TimeStep, u in p.PricingTier))

	yr1_emissions_from_elec_grid_lbs_NOx = @expression(m,p.TimeStepScaling*
		sum(m[:dvGridPurchase][u,ts]*p.GridEmissionsFactor_NOx[ts] for ts in p.TimeStep, u in p.PricingTier))

	yr1_emissions_from_elec_grid_lbs_SO2 = @expression(m,p.TimeStepScaling*
		sum(m[:dvGridPurchase][u,ts]*p.GridEmissionsFactor_SO2[ts] for ts in p.TimeStep, u in p.PricingTier))

	yr1_emissions_from_elec_grid_lbs_PM25 = @expression(m,p.TimeStepScaling*
		sum(m[:dvGridPurchase][u,ts]*p.GridEmissionsFactor_PM25[ts] for ts in p.TimeStep, u in p.PricingTier))

	return yr1_emissions_from_elec_grid_lbs_CO2, yr1_emissions_from_elec_grid_lbs_NOx, yr1_emissions_from_elec_grid_lbs_SO2, yr1_emissions_from_elec_grid_lbs_PM25
end
function calc_yr1_emissions_offset_from_elec_exports(m,p; tech_array=p.ElectricTechs)
	yr1_emissions_offset_from_elec_exports_lbs_CO2 = @expression(m,p.TimeStepScaling*
		sum(m[:dvProductionToGrid][t,u,ts]  * (p.GridEmissionsFactor_CO2[ts])
		for t in tech_array, ts in p.TimeStep, u in p.ExportTiersByTech[t]))
		# if battery ends up being able to discharge to grid, need to incorporate here- might require complex tracking of what's charging battery

	yr1_emissions_offset_from_elec_exports_lbs_NOx = @expression(m,p.TimeStepScaling*
		sum(m[:dvProductionToGrid][t,u,ts]  * (p.GridEmissionsFactor_NOx[ts])
		for t in tech_array, ts in p.TimeStep, u in p.ExportTiersByTech[t]))

	yr1_emissions_offset_from_elec_exports_lbs_SO2 = @expression(m,p.TimeStepScaling*
		sum(m[:dvProductionToGrid][t,u,ts]  * (p.GridEmissionsFactor_SO2[ts])
		for t in tech_array, ts in p.TimeStep, u in p.ExportTiersByTech[t]))

	yr1_emissions_offset_from_elec_exports_lbs_PM25 = @expression(m,p.TimeStepScaling*
		sum(m[:dvProductionToGrid][t,u,ts]  * (p.GridEmissionsFactor_PM25[ts])
		for t in tech_array, ts in p.TimeStep, u in p.ExportTiersByTech[t]))

	return yr1_emissions_offset_from_elec_exports_lbs_CO2, yr1_emissions_offset_from_elec_exports_lbs_NOx, yr1_emissions_offset_from_elec_exports_lbs_SO2, yr1_emissions_offset_from_elec_exports_lbs_PM25
end

### Lifecycle emissions calculations
function add_lifecycle_emissions_calcs(m,p)

	# BAU Lifecycle lbs CO2
	m[:Lifecycle_Emissions_Lbs_CO2_BAU] = p.BAUYr1Emissions_grid_CO2 * p.pwfs_grid_emissions_lbs["CO2"] + p.analysis_years * (p.BAUYr1Emissions_CO2 - p.BAUYr1Emissions_grid_CO2) # no annual decrease for on-site fuel burn

	# Lifecycle lbs CO2
	m[:Lifecycle_Emissions_Lbs_CO2_grid_net_if_selected] = p.pwfs_grid_emissions_lbs["CO2"] * m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_CO2]
	m[:Lifecycle_Emissions_Lbs_NOx_grid_net_if_selected] = p.pwfs_grid_emissions_lbs["NOx"] * m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_NOx]
	m[:Lifecycle_Emissions_Lbs_SO2_grid_net_if_selected] = p.pwfs_grid_emissions_lbs["SO2"] * m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_SO2]
	m[:Lifecycle_Emissions_Lbs_PM25_grid_net_if_selected] = p.pwfs_grid_emissions_lbs["PM25"] * m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_PM25]

	m[:Lifecycle_Emissions_Lbs_CO2_fuelburn] = p.analysis_years *  m[:yr1_emissions_onsite_fuel_lbs_CO2] # not assuming an annual decrease in on-site fuel burn emissions
	m[:Lifecycle_Emissions_Lbs_NOx_fuelburn] = p.analysis_years *  m[:yr1_emissions_onsite_fuel_lbs_NOx] # not assuming an annual decrease in on-site fuel burn emissions
	m[:Lifecycle_Emissions_Lbs_SO2_fuelburn] = p.analysis_years *  m[:yr1_emissions_onsite_fuel_lbs_SO2] # not assuming an annual decrease in on-site fuel burn emissions
	m[:Lifecycle_Emissions_Lbs_PM25_fuelburn] = p.analysis_years *  m[:yr1_emissions_onsite_fuel_lbs_PM25] # not assuming an annual decrease in on-site fuel burn emissions

	m[:Lifecycle_Emissions_Lbs_CO2] = m[:Lifecycle_Emissions_Lbs_CO2_grid_net_if_selected] + m[:Lifecycle_Emissions_Lbs_CO2_fuelburn]
	m[:Lifecycle_Emissions_Lbs_NOx] = m[:Lifecycle_Emissions_Lbs_NOx_grid_net_if_selected] + m[:Lifecycle_Emissions_Lbs_NOx_fuelburn]
	m[:Lifecycle_Emissions_Lbs_SO2] = m[:Lifecycle_Emissions_Lbs_SO2_grid_net_if_selected] + m[:Lifecycle_Emissions_Lbs_SO2_fuelburn]
	m[:Lifecycle_Emissions_Lbs_PM25] = m[:Lifecycle_Emissions_Lbs_PM25_grid_net_if_selected] + m[:Lifecycle_Emissions_Lbs_PM25_fuelburn]

	# Emissions costs
	m[:Lifecycle_Emissions_Cost_CO2] = p.CO2_dollars_tonne / p.Lbs_per_tonne * ( p.pwfs_emissions_cost["CO2_grid"] * m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_CO2] + p.pwfs_emissions_cost["CO2_onsite"] * m[:yr1_emissions_onsite_fuel_lbs_CO2])
	m[:Lifecycle_Emissions_Cost_NOx] = (p.pwfs_emissions_cost["NOx_grid"] * p.NOx_dollars_tonne_grid * m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_NOx] + p.pwfs_emissions_cost["NOx_onsite"] * p.NOx_dollars_tonne_onsite_fuelburn * m[:yr1_emissions_onsite_fuel_lbs_NOx]) / p.Lbs_per_tonne
	m[:Lifecycle_Emissions_Cost_SO2] = (p.pwfs_emissions_cost["SO2_grid"] * p.SO2_dollars_tonne_grid * m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_SO2] + p.pwfs_emissions_cost["SO2_onsite"] * p.SO2_dollars_tonne_onsite_fuelburn * m[:yr1_emissions_onsite_fuel_lbs_SO2]) / p.Lbs_per_tonne
	m[:Lifecycle_Emissions_Cost_PM25] =  (p.pwfs_emissions_cost["PM25_grid"] * p.PM25_dollars_tonne_grid * m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_PM25] + p.pwfs_emissions_cost["PM25_onsite"] * p.PM25_dollars_tonne_onsite_fuelburn * m[:yr1_emissions_onsite_fuel_lbs_PM25]) / p.Lbs_per_tonne
	m[:Lifecycle_Emissions_Cost_Health] = m[:Lifecycle_Emissions_Cost_NOx] + m[:Lifecycle_Emissions_Cost_SO2] + m[:Lifecycle_Emissions_Cost_PM25]

end

function add_emissions_constraints(m,p)
	if !isnothing(p.MinPercentCO2EmissionsReduction)
		@constraint(m, MinEmissionsReductionCon, m[:Lifecycle_Emissions_Lbs_CO2] <= (1-p.MinPercentCO2EmissionsReduction)*m[:Lifecycle_Emissions_Lbs_CO2_BAU])
	end
	if !isnothing(p.MaxPercentCO2EmissionsReduction)
		@constraint(m, MaxEmissionsReductionCon, m[:Lifecycle_Emissions_Lbs_CO2] >= (1-p.MaxPercentCO2EmissionsReduction)*m[:Lifecycle_Emissions_Lbs_CO2_BAU])
	end
end

function add_yearone_expressions(m, p)
    m[:Year1UtilityEnergy] = @expression(m,  p.TimeStepScaling * sum(
		m[:dvGridPurchase][u,ts] for ts in p.TimeStep, u in p.PricingTier)
	)
    m[:Year1EnergyCost] = m[:TotalEnergyChargesUtil] / p.pwf_e
    m[:Year1DemandCost] = m[:TotalDemandCharges] / p.pwf_e
    m[:Year1DemandTOUCost] = m[:DemandTOUCharges] / p.pwf_e
	m[:Year1DemandFlatCost] = m[:DemandFlatCharges] / p.pwf_e
	m[:Year1CPCost] = m[:TotalCPCharges] / p.pwf_e
    m[:Year1FixedCharges] = m[:TotalFixedCharges] / p.pwf_e
    m[:Year1MinCharges] = m[:MinChargeAdder] / p.pwf_e
    m[:Year1Bill] = m[:Year1EnergyCost] + m[:Year1DemandCost] + m[:Year1CPCost] + m[:Year1FixedCharges] + m[:Year1MinCharges]
	m[:Year1CHPStandbyCharges] = m[:TotalCHPStandbyCharges] / p.pwf_e
end


function reopt(model::JuMP.AbstractModel, model_inputs::Dict)

	t_start = time()
    p = Parameter(model_inputs)
	t = time() - t_start

	results = reopt_run(model, p)
	results["julia_input_construction_seconds"] = t
	return results
end


function reopt_run(m, p::Parameter)

	t_start = time()
	results = Dict{String, Any}()

	## Big-M adjustments; these need not be replaced in the parameter object.
	add_bigM_adjustments(m, p)
	results["julia_reopt_preamble_seconds"] = time() - t_start
	t_start = time()

	add_continuous_variables(m, p)
	add_integer_variables(m, p)

	results["julia_reopt_variables_seconds"] = time() - t_start
	t_start = time()
    ##############################################################################
	#############  		Constraints									 #############
	##############################################################################

	if !isempty(p.TimeStepsWithoutGrid)
		add_no_grid_constraints(m, p)
		if !isempty(p.ExportTiers)
			add_no_grid_export_constraint(m, p)
		end
	end

	### Constraint set (1): Fuel Burn Constraints
	add_fuel_constraints(m, p)

	### Constraint set (2): Thermal Production Constraints
	add_thermal_production_constraints(m, p)

	### Constraint set (3): Switch Constraints
	add_binTechIsOnInTS_constraints(m, p)

    ### Constraint set (4): Storage System Constraints
	add_storage_size_constraints(m, p)
	add_storage_op_constraints(m, p)
	### Constraint set (5) - hot and cold thermal loads
	add_thermal_load_constraints(m, p)

	### Constraint set (6): Production Incentive Cap
	add_prod_incent_constraints(m, p)
    ### System Size and Production Constraints
	### Constraint set (7): System Size is zero unless single basic tech is selected for class
	if !isempty(p.Tech)
		add_tech_size_constraints(m, p)
	end

	### Constraint set (8): Electrical Load Balancing and Grid Sales
	##Constraint (8a): Electrical Load Balancing with Grid

	add_load_balance_constraints(m, p)

	if p.OffGridFlag
		add_spinning_reserve_constraints(m, p)
	end

	add_storage_grid_constraints(m, p)
	if !isempty(p.ExportTiers)
		add_prod_grid_constraints(m, p)
	end
	## End constraint (8)

    ### Constraint set (9): Net Meter Module (copied directly from legacy model)
	if !isempty(p.Tech)
		add_NMIL_constraints(m, p)
	end
	##Constraint (9c): Net metering only -- can't sell more than you purchase
	if "NEM" in p.ExportTiers
		add_nem_constraint(m, p)
	end
	###End constraint set (9)

	if !isempty(p.TechsCannotCurtail)
		add_curtail_constraint(m, p)
	end

	### Constraint set (10): Electrical Energy Pricing tiers
	add_energy_price_constraints(m, p)

	### Constraint set (11): Peak Electrical Power Demand Charges: binDemandMonthsTier
	add_monthly_demand_charge_constraints(m, p)
	### Constraint set (12): Peak Electrical Power Demand Charges: Ratchets
	add_tou_demand_charge_constraints(m, p)
	m[:TotalDemandCharges] = @expression(m, m[:DemandTOUCharges] + m[:DemandFlatCharges])
	
	### Constraint set (14): Coincident Peak Charges
	if !isempty(p.CoincidentPeakRates)
		add_coincident_peak_charge_constraints(m, p)
	else
		m[:TotalCPCharges] = 0
	end

	add_parameters(m, p)
	add_cost_expressions(m, p)
	add_export_expressions(m, p)
	add_util_fixed_and_min_charges(m, p)

	## Constraint set (15): renewable energy and emissions calculations and constraints
	# Note: renewable heat calculations are currently added in post-optimization
	add_re_elec_calcs(m,p)
	add_re_elec_constraints(m,p)
	add_yr1_emissions_calcs(m,p)
	add_lifecycle_emissions_calcs(m,p)
	add_emissions_constraints(m,p)

	if !isempty(p.CHPTechs)
		add_chp_hourly_om_charges(m, p)
	end

	add_cost_function(m, p)

    if !(p.AddSOCIncentive == 1)
		@objective(m, Min, m[:REcosts])
	else
		@objective(m, Min, m[:REcosts] - sum(m[:dvStorageSOC]["Elec",ts] for ts in p.TimeStep)/p.TimeStepCount)
	end

	results["julia_reopt_constriants_seconds"] = time() - t_start
	t_start = time()

	optimize!(m)

	results["julia_reopt_optimize_seconds"] = time() - t_start
	t_start = time()

	if termination_status(m) == MOI.TIME_LIMIT
		results["status"] = "timed-out"
    elseif termination_status(m) == MOI.OPTIMAL
        results["status"] = "optimal"
    elseif termination_status(m) == MOI.INFEASIBLE || termination_status(m) == MOI.INFEASIBLE_OR_UNBOUNDED
        results["status"] = "infeasible"
    else
    	@warn "not optimal status: $(termination_status(m))"
		results["status"] = "not optimal"
    end

	##############################################################################
    #############  		Outputs    									 #############
    ##############################################################################
	try
		if p.OffGridFlag
			results["lcc"] = round(value(m[:REcosts]) + p.OtherCapitalCosts + p.OtherAnnualCosts)
		else
			results["lcc"] = round(value(m[:REcosts]) + 0.0001*value(m[:MinChargeAdder]))
		end
		results["lower_bound"] = round(JuMP.objective_bound(m))
		results["optimality_gap"] = JuMP.relative_gap(m)
	catch
		# not optimal, empty objective_value
		return results
	end


	add_yearone_expressions(m, p)

	results = reopt_results(m, p, results)
	results["julia_reopt_postprocess_seconds"] = time() - t_start
	return results
end


function reopt_results(m, p, r::Dict)
	add_re_emissions_results(m, p, r)
	add_storage_results(m, p, r)
	add_pv_results(m, p, r)
	if !isempty(m[:GeneratorTechs])
		add_generator_results(m, p, r)
    else
		add_null_generator_results(m, p, r)
	end
	if !isempty(m[:WindTechs])
		add_wind_results(m, p, r)
	else
		add_null_wind_results(m, p, r)
	end
	if !isempty(p.CHPTechs)
		add_chp_results(m, p, r)
	else
		add_null_chp_results(m, p, r)
	end
	if !isempty(p.BoilerTechs)
		if !("NEWBOILER" in p.BoilerTechs)
            add_boiler_results(m, p, r)
            add_null_newboiler_results(m, p, r)
        elseif !("BOILER" in p.BoilerTechs)
            add_null_boiler_results(m, p, r)
            add_newboiler_results(m, p, r)
        else
            add_boiler_results(m, p, r)
            add_newboiler_results(m, p, r)
        end
	else
        add_null_boiler_results(m, p, r)
        add_null_newboiler_results(m, p, r)
	end
	if !isempty(p.ElectricChillers)
		add_elec_chiller_results(m, p, r)
	else
		add_null_elec_chiller_results(m, p, r)
	end
	if !isempty(p.AbsorptionChillers)
		add_absorption_chiller_results(m, p, r)
	else
		add_null_absorption_chiller_results(m, p, r)
	end
	if !isempty(p.HotTES)
		add_hot_tes_results(m, p, r)
	else
		add_null_hot_tes_results(m, p, r)
	end
	if !isempty(p.ColdTES)
		add_cold_tes_results(m, p, r)
	else
		add_null_cold_tes_results(m, p, r)
	end
    if !isempty(p.SteamTurbineTechs)
		add_steamturbine_results(m, p, r)
	else
		add_null_steamturbine_results(m, p, r)
	end
	if !isempty(p.GHPOptions)
		add_ghp_results(m, p, r)
	else
		add_null_ghp_results(m, p, r)
	end
	add_util_results(m, p, r)

	if p.OffGridFlag
		add_load_results(m, p, r)
		add_offgrid_financial_results(m, p, r)
	else
		add_null_load_results(m, p, r)
		add_null_offgrid_financial_results
	end
	return r
end

function add_re_emissions_results(m, p, r::Dict)

	r["pwf_om"] = round(value(p.pwf_om),digits=4)

	# renewable elec
	r["annual_re_elec_kwh"] = round(value(m[:AnnualREEleckWh]), digits=2)
	r["annual_re_elec_percent"] = round(value(m[:AnnualREEleckWh])/value(m[:AnnualEleckWh]), digits=6)

	# total renewable 
	add_re_tot_calcs(m,p)
	r["annual_total_re_percent"] = round(value(m[:AnnualRETotkWh])/value(m[:AnnualTotkWh]), digits=6)

	# BAU preprocessed emissions (used for emissions reduction target calculations; output for testing purposes)
	r["preprocessed_BAU_year_one_emissions_tCO2"] = round(value(p.BAUYr1Emissions_CO2)/p.Lbs_per_tonne,digits=2)
	r["preprocessed_BAU_lifecycle_emissions_tCO2"] = round(value(m[:Lifecycle_Emissions_Lbs_CO2_BAU]/p.Lbs_per_tonne),digits=2) # no annual decrease for on-site fuel burn
	# pass through for breakeven cost of CO2 calculation:
	r["include_climate_in_objective"] = p.Include_climate_in_objective
	r["pwfs_emissions_cost_CO2_grid"] = p.pwfs_emissions_cost["CO2_grid"]
	r["pwfs_emissions_cost_CO2_onsite"] = p.pwfs_emissions_cost["CO2_onsite"]

	# Year 1 Emissions results at Site level
	r["year_one_emissions_tCO2"] = round(value(m[:EmissionsYr1_Total_LbsCO2]/p.Lbs_per_tonne), digits=2)
	r["year_one_emissions_tNOx"] = round(value(m[:EmissionsYr1_Total_LbsNOx]/p.Lbs_per_tonne), digits=2)
	r["year_one_emissions_tSO2"] = round(value(m[:EmissionsYr1_Total_LbsSO2]/p.Lbs_per_tonne), digits=2)
	r["year_one_emissions_tPM25"] = round(value(m[:EmissionsYr1_Total_LbsPM25]/p.Lbs_per_tonne), digits=2)

	r["year_one_emissions_from_fuelburn_tCO2"] = round(value(m[:yr1_emissions_onsite_fuel_lbs_CO2]/p.Lbs_per_tonne), digits=2)
	r["year_one_emissions_from_fuelburn_tNOx"] = round(value(m[:yr1_emissions_onsite_fuel_lbs_NOx]/p.Lbs_per_tonne), digits=2)
	r["year_one_emissions_from_fuelburn_tSO2"] = round(value(m[:yr1_emissions_onsite_fuel_lbs_SO2]/p.Lbs_per_tonne), digits=2)
	r["year_one_emissions_from_fuelburn_tPM25"] = round(value(m[:yr1_emissions_onsite_fuel_lbs_PM25]/p.Lbs_per_tonne), digits=2)

	r["year_one_emissions_from_elec_grid_tCO2"] = round(value(m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_CO2]/p.Lbs_per_tonne), digits=2)
	r["year_one_emissions_from_elec_grid_tNOx"] = round(value(m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_NOx]/p.Lbs_per_tonne), digits=2)
	r["year_one_emissions_from_elec_grid_tSO2"] = round(value(m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_SO2]/p.Lbs_per_tonne), digits=2)
	r["year_one_emissions_from_elec_grid_tPM25"] = round(value(m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_PM25]/p.Lbs_per_tonne), digits=2)

	# Lifecycle emissions results at Site level
	r["lifecycle_emissions_reduction_CO2_pct"] = round(value(1-m[:Lifecycle_Emissions_Lbs_CO2]/m[:Lifecycle_Emissions_Lbs_CO2_BAU]), digits=6)
	r["lifecycle_emissions_cost_CO2"] = round(value(m[:Lifecycle_Emissions_Cost_CO2]), digits=2)
	r["lifecycle_emissions_cost_Health"] = round(value(m[:Lifecycle_Emissions_Cost_Health]), digits=2)

	r["lifecycle_emissions_tCO2"] = round(value(m[:Lifecycle_Emissions_Lbs_CO2]/p.Lbs_per_tonne), digits=2)
	r["lifecycle_emissions_tNOx"] = round(value(m[:Lifecycle_Emissions_Lbs_NOx]/p.Lbs_per_tonne), digits=2)
	r["lifecycle_emissions_tSO2"] = round(value(m[:Lifecycle_Emissions_Lbs_SO2]/p.Lbs_per_tonne), digits=2)
	r["lifecycle_emissions_tPM25"] = round(value(m[:Lifecycle_Emissions_Lbs_PM25]/p.Lbs_per_tonne), digits=2)

	r["lifecycle_emissions_from_fuelburn_tCO2"] = round(value(m[:Lifecycle_Emissions_Lbs_CO2_fuelburn]/p.Lbs_per_tonne), digits=2)
	r["lifecycle_emissions_from_fuelburn_tNOx"] = round(value(m[:Lifecycle_Emissions_Lbs_NOx_fuelburn]/p.Lbs_per_tonne), digits=2)
	r["lifecycle_emissions_from_fuelburn_tSO2"] = round(value(m[:Lifecycle_Emissions_Lbs_SO2_fuelburn]/p.Lbs_per_tonne), digits=2)
	r["lifecycle_emissions_from_fuelburn_tPM25"] = round(value(m[:Lifecycle_Emissions_Lbs_PM25_fuelburn]/p.Lbs_per_tonne), digits=2)

	r["lifecycle_emissions_from_elec_grid_tCO2"] = round(value(m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_CO2]/p.Lbs_per_tonne*p.pwfs_grid_emissions_lbs["CO2"]), digits=2)
	r["lifecycle_emissions_from_elec_grid_tNOx"] = round(value(m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_NOx]/p.Lbs_per_tonne*p.pwfs_grid_emissions_lbs["NOx"]), digits=2)
	r["lifecycle_emissions_from_elec_grid_tSO2"] = round(value(m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_SO2]/p.Lbs_per_tonne*p.pwfs_grid_emissions_lbs["SO2"]), digits=2)
	r["lifecycle_emissions_from_elec_grid_tPM25"] = round(value(m[:yr1_emissions_from_elec_grid_net_if_selected_lbs_PM25]/p.Lbs_per_tonne*p.pwfs_grid_emissions_lbs["PM25"]), digits=2)

end

function add_null_generator_results(m, p, r::Dict)
	r["gen_net_fixed_om_costs"] = 0
	r["gen_net_variable_om_costs"] = 0
	r["gen_total_fuel_cost"] = 0
	r["gen_year_one_fuel_cost"] = 0
	r["gen_year_one_variable_om_costs"] = 0
	r["GENERATORtoBatt"] = []
	r["GENERATORtoGrid"] = []
	r["GENERATORtoLoad"] = []
	r["fuel_used_kwh"] = 0
	r["year_one_gen_energy_produced"] = 0.0
	r["average_yearly_gen_energy_produced"] = 0.0
	nothing
end

function add_null_wind_results(m, p, r::Dict)
	r["WINDtoLoad"] = []
	r["WINDtoGrid"] = []
	nothing
end

function add_null_chp_results(m, p, r::Dict)
	r["chp_kw"] = 0.0
    r["chp_supplemental_firing_kw"] = 0.0
	r["year_one_chp_fuel_used"] = 0.0
	r["year_one_chp_electric_energy_produced"] = 0.0
	r["year_one_chp_thermal_energy_produced"] = 0.0
	r["chp_electric_production_series"] = []
	r["chp_to_battery_series"] = []
	r["chp_electric_to_load_series"] = []
	r["chp_to_grid_series"] = []
	r["chp_thermal_to_load_series"] = []
	r["chp_thermal_to_tes_series"] = []
    r["chp_thermal_to_steamturbine_series"] = []
	r["chp_thermal_to_waste_series"] = []
	r["total_chp_fuel_cost"] = 0.0
	r["year_one_chp_fuel_cost"] = 0.0
	nothing
end

function add_null_boiler_results(m, p, r::Dict)
	r["fuel_to_boiler_series"] = []
	r["boiler_thermal_production_series"] = []
	r["boiler_thermal_to_load_series"] = []
	r["boiler_thermal_to_tes_series"] = []
    r["boiler_thermal_to_steamturbine_series"] = []
	r["year_one_fuel_to_boiler_kwh"] = 0.0
	r["year_one_boiler_thermal_production_kwh"] = 0.0
	r["total_boiler_fuel_cost"] = 0.0
	r["year_one_boiler_fuel_cost"] = 0.0
	nothing
end

function add_null_elec_chiller_results(m, p, r::Dict)
	r["electric_chiller_to_load_series"] = []
	r["electric_chiller_to_tes_series"] = []
	r["electric_chiller_consumption_series"] = []
	r["year_one_electric_chiller_electric_kwh"] = 0.0
	r["year_one_electric_chiller_thermal_kwh"] = 0.0
	nothing
end

function add_null_absorption_chiller_results(m, p, r::Dict)
	r["absorpchl_kw"] = 0.0
	r["absorption_chiller_to_load_series"] = []
	r["absorption_chiller_to_tes_series"] = []
	r["absorption_chiller_consumption_series"] = []
	r["year_one_absorp_chiller_thermal_consumption_kwh"] = 0.0
	r["year_one_absorp_chiller_thermal_prod_kwh"] = 0.0
	nothing
end

function add_null_hot_tes_results(m, p, r::Dict)
	r["hot_tes_size_kwh"] = 0.0
	r["hot_tes_thermal_production_series"] = []
	r["hot_tes_pct_soc_series"] = []
	nothing
end

function add_null_cold_tes_results(m, p, r::Dict)
	r["cold_tes_size_kwht"] = 0.0
	r["cold_tes_thermal_production_series"] = []
	r["cold_tes_pct_soc_series"] = []
	nothing
end

function add_null_load_results(m, p, r::Dict)
	r["load_met"] = []
	r["load_sr_required"] = []
	nothing
end

function add_null_offgrid_financial_results(m, p, r::Dict)
	r["total_other_cap_costs"] = []
	r["total_annual_costs"] = []
	r["microgrid_lcoe"] = []
	nothing
end

function add_load_results(m, p, r::Dict)
	@expression(m, LoadMet[ts in p.TimeStepsWithoutGrid], p.ElecLoad[ts] * m[:dvOffgridLoadServedFraction][ts])
	r["load_met"] = round.(value.(LoadMet), digits=6)
	@expression(m, LoadMetPct, sum(m[:dvOffgridLoadServedFraction][ts] * p.ElecLoad[ts] for ts in p.TimeStepsWithoutGrid) /
	 		sum(p.ElecLoad))
	r["load_met_pct"] = round(value(LoadMetPct), digits=6)

	@expression(m, SRrequiredLoad[ts in p.TimeStepsWithoutGrid], p.ElecLoad[ts] * m[:dvOffgridLoadServedFraction][ts] * p.SRrequiredPctLoad)
	r["sr_required_load"] = round.(value.(SRrequiredLoad), digits=3)

	#Debug outputs
	@expression(m, TotSRrequired[ts in p.TimeStepsWithoutGrid], m[:SRrequired][ts])
	r["tot_sr_required"] = round.(value.(TotSRrequired), digits=3)
	@expression(m, TotSRprovided[ts in p.TimeStepsWithoutGrid], m[:SRprovided][ts])
	r["tot_sr_provided"] = round.(value.(TotSRprovided), digits=3)
	nothing
end

function add_offgrid_financial_results(m, p, r::Dict)
	lcc = round(value(m[:REcosts]) + p.OtherCapitalCosts + p.OtherAnnualCosts)
	@expression(m, AnnualkWhServed, sum(p.ElecLoad[ts] * value(m[:dvOffgridLoadServedFraction][ts]) for  ts in p.TimeStepsWithoutGrid))
	r["total_other_cap_costs"] = p.OtherCapitalCosts
	r["total_annual_costs"] = p.OtherAnnualCosts

	if p.two_party_factor == 1  # Direct ownership (two_party_factor = 1 if third_party_ownership is False)
		pwf = p.pwf_offtaker
	else
		pwf = p.pwf_owner
	end
	r["microgrid_lcoe"] = round(lcc / pwf / value(AnnualkWhServed), digits=4)
	nothing
end

function add_storage_results(m, p, r::Dict)
    r["batt_kwh"] = value(m[:dvStorageCapEnergy]["Elec"])
    r["batt_kw"] = value(m[:dvStorageCapPower]["Elec"])

    if r["batt_kwh"] != 0
    	@expression(m, soc[ts in p.TimeStep], m[:dvStorageSOC]["Elec",ts] / r["batt_kwh"])
        r["year_one_soc_series_pct"] = value.(soc)
    else
        r["year_one_soc_series_pct"] = []
    end
    @expression(m, GridToBatt[ts in p.TimeStep], m[:dvGridToStorage][ts])
	r["GridToBatt"] = round.(value.(GridToBatt), digits=3)

	@expression(m, ElecFromBatt[ts in p.TimeStep],
		sum(m[:dvDischargeFromStorage][b,ts] for b in p.ElecStorage))
	r["ElecFromBatt"] = round.(value.(ElecFromBatt), digits=3)
	r["ElecFromBattExport"] = zeros(length(p.TimeStep))

	#Offgrid
	if p.OffGridFlag
		@expression(m, SRprovidedBatt[ts in p.TimeStepsWithoutGrid], sum(m[:dvSRbatt][b, ts] for b in p.ElecStorage))
		r["sr_provided_batt"] = round.(value.(SRprovidedBatt), digits=3)
	else
		r["sr_provided_batt"] = []
    end

	nothing
end

function add_null_newboiler_results(m, p, r::Dict)
	r["newboiler_size_kw"] = 0.0
    r["fuel_to_newboiler_series"] = []
	r["newboiler_thermal_production_series"] = []
	r["newboiler_thermal_to_load_series"] = []
	r["newboiler_thermal_to_tes_series"] = []
	r["newboiler_thermal_to_steamturbine_series"] = []
	r["year_one_fuel_to_newboiler_kwh"] = 0.0
	r["year_one_newboiler_thermal_production_kwh"] = 0.0
	r["total_newboiler_fuel_cost"] = 0.0
	r["year_one_newboiler_fuel_cost"] = 0.0
	nothing
end

function add_null_steamturbine_results(m, p, r::Dict)
	r["steamturbine_kw"] = 0.0
	r["year_one_steamturbine_thermal_consumption"] = 0.0
	r["year_one_steamturbine_electric_energy_produced"] = 0.0
	r["year_one_steamturbine_thermal_energy_produced"] = 0.0
    r["steamturbine_thermal_consumption_series"] = []
	r["steamturbine_electric_production_series"] = []
	r["steamturbine_to_battery_series"] = []
	r["steamturbine_electric_to_load_series"] = []
	r["steamturbine_to_grid_series"] = []
	r["steamturbine_thermal_to_load_series"] = []
	r["steamturbine_thermal_to_tes_series"] = []
	nothing
end

function add_null_ghp_results(m, p, r::Dict)
	r["GHPOptionChosen"] = 0
    r["HeatingThermalReductionWithGHP"] = []
    r["CoolingThermalReductionWithGHP"] = []
	nothing
end

function add_generator_results(m, p, r::Dict)
	m[:GenPerUnitSizeOMCosts] = @expression(m, p.two_party_factor *
		sum(p.OMperUnitSize[t] * p.pwf_om * m[:dvSize][t] for t in m[:GeneratorTechs])
	)
	m[:GenPerUnitProdOMCosts] = @expression(m, p.two_party_factor *
		sum(m[:dvRatedProduction][t,ts] * p.TimeStepScaling * p.ProductionFactor[t,ts] * p.OMcostPerUnitProd[t] * p.pwf_om
			for t in m[:GeneratorTechs], ts in p.TimeStep)
	)
	if value(sum(m[:dvSize][t] for t in m[:GeneratorTechs])) > 0
		r["generator_kw"] = value(sum(m[:dvSize][t] for t in m[:GeneratorTechs]))
		r["gen_net_fixed_om_costs"] = round(value(m[:GenPerUnitSizeOMCosts]) * m[:r_tax_fraction_owner], digits=0)
		r["gen_net_variable_om_costs"] = round(value(m[:GenPerUnitProdOMCosts]) * m[:r_tax_fraction_owner], digits=0)
		r["gen_total_fuel_cost"] = round(value(m[:TotalGeneratorFuelCharges]) * m[:r_tax_fraction_offtaker], digits=2)
		r["gen_year_one_fuel_cost"] = round(value(m[:TotalGeneratorFuelCharges]) / p.pwf_fuel["GENERATOR"], digits=2)
		r["gen_year_one_variable_om_costs"] = round(value(m[:GenPerUnitProdOMCosts]) / (p.pwf_om * p.two_party_factor), digits=0)
		r["gen_year_one_fixed_om_costs"] = round(value(m[:GenPerUnitSizeOMCosts]) / (p.pwf_om * p.two_party_factor), digits=0)
	end
	@expression(m, GENERATORtoBatt[ts in p.TimeStep],
				sum(m[:dvProductionToStorage]["Elec",t,ts] for t in m[:GeneratorTechs]))
	r["GENERATORtoBatt"] = round.(value.(GENERATORtoBatt), digits=3)

	r["GENERATORtoGrid"] = zeros(length(p.TimeStep))
	if !isempty(p.ExportTiers)
		@expression(m, GENERATORtoGrid[ts in p.TimeStep],
					sum(m[:dvProductionToGrid][t,u,ts] for t in m[:GeneratorTechs], u in p.ExportTiersByTech[t]))
		r["GENERATORtoGrid"] = round.(value.(GENERATORtoGrid), digits=3)
	end

	@expression(m, GENERATORtoLoad[ts in p.TimeStep],
				sum(m[:dvRatedProduction][t, ts] * p.ProductionFactor[t, ts] * p.LevelizationFactor[t]
					for t in m[:GeneratorTechs]) - 
					GENERATORtoBatt[ts] - r["GENERATORtoGrid"][ts]
					)
	r["GENERATORtoLoad"] = round.(value.(GENERATORtoLoad), digits=3)

    @expression(m, GeneratorFuelUsed, sum(m[:dvFuelUsage][t, ts] for t in m[:GeneratorTechs], ts in p.TimeStep))
	r["fuel_used_kwh"] = round(value(GeneratorFuelUsed), digits=2)

	@expression(m, GeneratorFuelSeries[ts in p.TimeStep], sum(m[:dvFuelUsage][t, ts] for t in m[:GeneratorTechs]))
	r["fuel_used_kwh_series"] = round.(value.(GeneratorFuelSeries), digits=2)

	m[:Year1GenProd] = @expression(m,
		p.TimeStepScaling * sum(m[:dvRatedProduction][t,ts] * p.ProductionFactor[t, ts]
			for t in m[:GeneratorTechs], ts in p.TimeStep)
	)
	r["year_one_gen_energy_produced"] = round(value(m[:Year1GenProd]), digits=0)
	m[:AverageGenProd] = @expression(m,
		p.TimeStepScaling * sum(m[:dvRatedProduction][t,ts] * p.ProductionFactor[t, ts] * p.LevelizationFactor[t]
			for t in m[:GeneratorTechs], ts in p.TimeStep)
	)
	r["average_yearly_gen_energy_produced"] = round(value(m[:AverageGenProd]), digits=0)

	# This is for the off-grid microgrid LCOE
	m[:TotalGeneratorCapCosts] = @expression(m, p.two_party_factor * (
		sum( p.CapCostSlope[t,s] * m[:dvSystemSizeSegment][t,"CapCost",s] for t in m[:GeneratorTechs], s in 1:p.SegByTechSubdivision["CapCost",t] ) +
		sum( p.CapCostYInt[t,s] * m[:binSegmentSelect][t,"CapCost",s] for t in m[:GeneratorTechs], s in 1:p.SegByTechSubdivision["CapCost",t] )
	))
	r["total_generator_capital_costs"] = round(value(m[:TotalGeneratorCapCosts]), digits=2)

	#Offgrid
	if p.OffGridFlag
		@expression(m, GenProvidedSR[ts in p.TimeStepsWithoutGrid], sum(m[:dvSR][t,ts] for t in ["GENERATOR"]))
		r["sr_provided_gen"] = round.(value.(GenProvidedSR), digits=3)
	else
		r["sr_provided_gen"] = []
    end
	nothing
end

function add_wind_results(m, p, r::Dict)
	r["wind_kw"] = round(value(sum(m[:dvSize][t] for t in m[:WindTechs])), digits=4)
	@expression(m, WINDtoBatt[ts in p.TimeStep],
	            sum(sum(m[:dvProductionToStorage][b, t, ts] for t in m[:WindTechs]) for b in p.ElecStorage))
	r["WINDtoBatt"] = round.(value.(WINDtoBatt), digits=3)

	@expression(m, WINDtoCurtail[ts in p.TimeStep],
				sum(m[:dvProductionToCurtail][t,ts] for t in m[:WindTechs]))

	r["WINDtoCurtail"] = round.(value.(WINDtoCurtail), digits=3)

	r["WINDtoGrid"] = zeros(length(p.TimeStep))
	if !isempty(p.ExportTiers)
		@expression(m, WINDtoGrid[ts in p.TimeStep],
					sum(m[:dvProductionToGrid][t,u,ts] for t in m[:WindTechs], u in p.ExportTiersByTech[t]))
		r["WINDtoGrid"] = round.(value.(WINDtoGrid), digits=3)
	end

	@expression(m, WINDtoLoad[ts in p.TimeStep],
				sum(m[:dvRatedProduction][t, ts] * p.ProductionFactor[t, ts] * p.LevelizationFactor[t]
					for t in m[:WindTechs]) - r["WINDtoGrid"][ts] - WINDtoBatt[ts] - WINDtoCurtail[ts] )
	r["WINDtoLoad"] = round.(value.(WINDtoLoad), digits=3)
	m[:Year1WindProd] = @expression(m,
		p.TimeStepScaling * sum(m[:dvRatedProduction][t,ts] * p.ProductionFactor[t, ts]
			for t in m[:WindTechs], ts in p.TimeStep)
	)
	r["year_one_wind_energy_produced"] = round(value(m[:Year1WindProd]), digits=0)
	m[:AverageWindProd] = @expression(m,
		p.TimeStepScaling * sum(m[:dvRatedProduction][t,ts] * p.ProductionFactor[t, ts] * p.LevelizationFactor[t]
			for t in m[:WindTechs], ts in p.TimeStep)
	)
	r["average_wind_energy_produced"] = round(value(m[:AverageWindProd]), digits=0)

	nothing
end


function add_pv_results(m, p, r::Dict)
	PVclasses = filter(tc->startswith(tc, "PV"), p.TechClass)
    for PVclass in PVclasses
		PVtechs_in_class = filter(t->startswith(t, PVclass), m[:PVTechs])
		PVtechs_in_class_noNEM = filter(t->endswith(t, "NM"), m[:PVTechs])

		if !isempty(PVtechs_in_class)

			r[string(PVclass, "_kw")] = round(value(sum(m[:dvSize][t] for t in PVtechs_in_class)), digits=4)

			# NOTE: must use anonymous expressions in this loop to overwrite values for cases with multiple PV
            if !isempty(p.ElecStorage)
				PVtoBatt = @expression(m, [ts in p.TimeStep],
					sum(m[:dvProductionToStorage][b, t, ts] for t in PVtechs_in_class, b in p.ElecStorage))
			else
				PVtoBatt = @expression(m, [ts in p.TimeStep], 0.0)
            end
			r[string(PVclass, "toBatt")] = round.(value.(PVtoBatt), digits=3)

			PVtoCurtail = @expression(m, [ts in p.TimeStep],
					sum(m[:dvProductionToCurtail][t, ts] for t in PVtechs_in_class))
    	    r[string(PVclass, "toCurtail")] = round.(value.(PVtoCurtail), digits=3)
			
			r[string(PVclass, "toGrid")] = zeros(length(p.TimeStep))
			r[string("average_annual_energy_exported_", PVclass)] = 0.0
			if !isempty(p.ExportTiers)
				PVtoGrid = @expression(m, [ts in p.TimeStep],
						sum(m[:dvProductionToGrid][t,u,ts] for t in PVtechs_in_class, u in p.ExportTiersByTech[t]))
				r[string(PVclass, "toGrid")] = round.(value.(PVtoGrid), digits=3)

				ExportedElecPV = @expression(m, sum(m[:dvProductionToGrid][t,u,ts]
					for t in PVtechs_in_class, u in p.ExportTiersByTech[t], ts in p.TimeStep) * p.TimeStepScaling)
				r[string("average_annual_energy_exported_", PVclass)] = round(value(ExportedElecPV), digits=0)
			end
			
			PVtoLoad = @expression(m, [ts in p.TimeStep],
				sum(m[:dvRatedProduction][t, ts] * p.ProductionFactor[t, ts] * p.LevelizationFactor[t] for t in PVtechs_in_class) 
				- r[string(PVclass, "toGrid")][ts] - PVtoBatt[ts] - PVtoCurtail[ts]
				)
            r[string(PVclass, "toLoad")] = round.(value.(PVtoLoad), digits=3)

			Year1PvProd = @expression(m, sum(m[:dvRatedProduction][t,ts] * p.ProductionFactor[t, ts]
				for t in PVtechs_in_class, ts in p.TimeStep) * p.TimeStepScaling)
			r[string("year_one_energy_produced_", PVclass)] = round(value(Year1PvProd), digits=0)

			AveragePvProd = @expression(m, sum(m[:dvRatedProduction][t,ts] * p.ProductionFactor[t, ts] * p.LevelizationFactor[t]
			    for t in PVtechs_in_class, ts in p.TimeStep) * p.TimeStepScaling)
            r[string("average_yearly_energy_produced_", PVclass)] = round(value(AveragePvProd), digits=0)

            PVPerUnitSizeOMCosts = @expression(m, sum(p.OMperUnitSize[t] * p.pwf_om * m[:dvSize][t] for t in PVtechs_in_class))
            r[string(PVclass, "_net_fixed_om_costs")] = round(value(PVPerUnitSizeOMCosts) * m[:r_tax_fraction_owner], digits=0)

			#Offgrid
			if p.OffGridFlag
				PVrequiredSR = @expression(m, [ts in p.TimeStepsWithoutGrid],
                    sum(m[:ProductionToLoadSR][t,ts] * p.SRrequiredPctTechs[t] for t in PVtechs_in_class_noNEM)
                )
				r[string("SRrequired", PVclass)] = round.(value.(PVrequiredSR), digits=3)

				PVprovidedSR = @expression(m, [ts in p.TimeStepsWithoutGrid], sum(m[:dvSR][t,ts] for t in PVtechs_in_class_noNEM))
				r[string("SRprovided", PVclass)] = round.(value.(PVprovidedSR), digits=3)
			else
				r[string("SRrequired", PVclass)] = []
				r[string("SRprovided", PVclass)] = []
			end
        end
	end
	nothing
end

function add_chp_results(m, p, r::Dict)
	r["CHP"] = Dict()
	r["chp_kw"] = value(sum(m[:dvSize][t] for t in p.CHPTechs))
	r["chp_supplemental_firing_kw"] = value(sum(m[:dvSupplementaryFiringCHPSize][t] for t in p.CHPTechs))
	@expression(m, CHPFuelUsed, sum(m[:dvFuelUsage][t, ts] for t in p.CHPTechs, ts in p.TimeStep))
	r["year_one_chp_fuel_used"] = round(value(CHPFuelUsed), digits=3)
	@expression(m, Year1CHPElecProd,
		p.TimeStepScaling * sum(m[:dvRatedProduction][t,ts] * p.ProductionFactor[t, ts]
			for t in p.CHPTechs, ts in p.TimeStep))
	r["year_one_chp_electric_energy_produced"] = round(value(Year1CHPElecProd), digits=3)
	@expression(m, Year1CHPThermalProd,
		p.TimeStepScaling * sum(m[:dvThermalProduction][t,ts]+m[:dvSupplementaryThermalProduction][t,ts]-m[:dvProductionToWaste][t,ts] for t in p.CHPTechs, ts in p.TimeStep))
	r["year_one_chp_thermal_energy_produced"] = round(value(Year1CHPThermalProd), digits=3)
	@expression(m, CHPElecProdTotal[ts in p.TimeStep],
		sum(m[:dvRatedProduction][t,ts] * p.ProductionFactor[t, ts] for t in p.CHPTechs))
	r["chp_electric_production_series"] = round.(value.(CHPElecProdTotal), digits=3)
	@expression(m, CHPtoGrid[ts in p.TimeStep], sum(m[:dvProductionToGrid][t,u,ts]
			for t in p.CHPTechs, u in p.ExportTiersByTech[t]))
	r["chp_to_grid_series"] = round.(value.(CHPtoGrid), digits=3)
	@expression(m, CHPtoBatt[ts in p.TimeStep],
		sum(m[:dvProductionToStorage]["Elec",t,ts] for t in p.CHPTechs))
	r["chp_to_battery_series"] = round.(value.(CHPtoBatt), digits=3)
	@expression(m, CHPtoLoad[ts in p.TimeStep],
		sum(m[:dvRatedProduction][t, ts] * p.ProductionFactor[t, ts] * p.LevelizationFactor[t]
			for t in p.CHPTechs) - CHPtoBatt[ts] - CHPtoGrid[ts])
	r["chp_electric_to_load_series"] = round.(value.(CHPtoLoad), digits=3)
	@expression(m, CHPtoHotTES[ts in p.TimeStep],
		sum(m[:dvProductionToStorage]["HotTES",t,ts] for t in p.CHPTechs))
	r["chp_thermal_to_tes_series"] = round.(value.(CHPtoHotTES), digits=5)
    if !isempty(p.SteamTurbineTechs)
        @expression(m, CHPToSteamTurbine[ts in p.TimeStep], sum(m[:dvThermalToSteamTurbine][t,ts] for t in p.CHPTechs))
        r["chp_thermal_to_steamturbine_series"] = round.(value.(CHPToSteamTurbine), digits=3)
    else
        CHPToSteamTurbine = zeros(p.TimeStepCount)
        r["chp_thermal_to_steamturbine_series"] = round.(CHPToSteamTurbine, digits=3)
    end
	@expression(m, CHPThermalToWaste[ts in p.TimeStep],
		sum(m[:dvProductionToWaste][t,ts] for t in p.CHPTechs))
	r["chp_thermal_to_waste_series"] = round.(value.(CHPThermalToWaste), digits=5)
	@expression(m, CHPThermalToLoad[ts in p.TimeStep],
		sum(m[:dvThermalProduction][t,ts] + m[:dvSupplementaryThermalProduction][t,ts]
			for t in p.CHPTechs) - CHPtoHotTES[ts] - CHPToSteamTurbine[ts] - CHPThermalToWaste[ts])
	r["chp_thermal_to_load_series"] = round.(value.(CHPThermalToLoad), digits=5)
	@expression(m, TotalCHPFuelCharges,
		p.pwf_fuel["CHP"] * p.TimeStepScaling * sum(p.FuelCost["CHPFUEL",ts] * m[:dvFuelUsage]["CHP",ts]
			for ts in p.TimeStep))
	r["total_chp_fuel_cost"] = round(value(TotalCHPFuelCharges) * m[:r_tax_fraction_offtaker], digits=3)
	r["year_one_chp_fuel_cost"] = round(value(TotalCHPFuelCharges / p.pwf_fuel["CHP"]), digits=3)
	r["year_one_chp_standby_cost"] = round(value(m[:Year1CHPStandbyCharges]), digits=0)
	r["total_chp_standby_cost"] = round(value(m[:TotalCHPStandbyCharges] * m[:r_tax_fraction_offtaker]), digits=0)

	nothing
end

function add_boiler_results(m, p, r::Dict)
	##Boiler results go here; need to populate expressions for first collection
	@expression(m, FuelToBoiler[ts in p.TimeStep], m[:dvFuelUsage]["BOILER", ts])
	r["fuel_to_boiler_series"] = round.(value.(FuelToBoiler), digits=3)
	@expression(m, BoilerThermalProd[ts in p.TimeStep], p.ProductionFactor["BOILER",ts] * m[:dvThermalProduction]["BOILER",ts])
	r["boiler_thermal_production_series"] = round.(value.(BoilerThermalProd), digits=3)
	@expression(m, BoilerFuelUsed, sum(m[:dvFuelUsage]["BOILER", ts] for ts in p.TimeStep))
	r["year_one_fuel_to_boiler_kwh"] = round(value(BoilerFuelUsed), digits=3)
	@expression(m, BoilerThermalProduced, sum(p.ProductionFactor["BOILER",ts] * m[:dvThermalProduction]["BOILER",ts]
		for ts in p.TimeStep))
	r["year_one_boiler_thermal_production_kwh"] = round(value(BoilerThermalProduced), digits=3)
	@expression(m, BoilerToHotTES[ts in p.TimeStep],
		m[:dvProductionToStorage]["HotTES","BOILER",ts])
	r["boiler_thermal_to_tes_series"] = round.(value.(BoilerToHotTES), digits=3)
    if !isempty(p.SteamTurbineTechs)
        @expression(m, BoilerToSteamTurbine[ts in p.TimeStep], m[:dvThermalToSteamTurbine]["BOILER",ts])
        r["boiler_thermal_to_steamturbine_series"] = round.(value.(BoilerToSteamTurbine), digits=3)
    else
        BoilerToSteamTurbine = zeros(p.TimeStepCount)
        r["boiler_thermal_to_steamturbine_series"] = round.(BoilerToSteamTurbine, digits=3)
    end
	@expression(m, BoilerToLoad[ts in p.TimeStep],
		m[:dvThermalProduction]["BOILER",ts] * p.ProductionFactor["BOILER",ts] - BoilerToHotTES[ts] - BoilerToSteamTurbine[ts])
	r["boiler_thermal_to_load_series"] = round.(value.(BoilerToLoad), digits=3)
	@expression(m, TotalBoilerFuelCharges,
		p.pwf_fuel["BOILER"] * p.TimeStepScaling * sum(p.FuelCost["BOILERFUEL",ts] * m[:dvFuelUsage]["BOILER",ts]
			for ts in p.TimeStep))
	r["total_boiler_fuel_cost"] = round(value(TotalBoilerFuelCharges * m[:r_tax_fraction_offtaker]), digits=3)
	r["year_one_boiler_fuel_cost"] = round(value(TotalBoilerFuelCharges / p.pwf_fuel["BOILER"]), digits=3)

	nothing
end

function add_elec_chiller_results(m, p, r::Dict)
	@expression(m, ELECCHLtoTES[ts in p.TimeStep],
		sum(m[:dvProductionToStorage][b,t,ts] for b in p.ColdTES, t in p.ElectricChillers))
	r["electric_chiller_to_tes_series"] = round.(value.(ELECCHLtoTES), digits=3)
	@expression(m, ELECCHLtoLoad[ts in p.TimeStep],
		sum(m[:dvThermalProduction][t,ts] * p.ProductionFactor[t,ts] for t in p.ElectricChillers)
			- ELECCHLtoTES[ts])
	r["electric_chiller_to_load_series"] = round.(value.(ELECCHLtoLoad), digits=3)
	@expression(m, ELECCHLElecConsumptionSeries[ts in p.TimeStep],
		sum(m[:dvThermalProduction][t,ts] / p.ElectricChillerCOP for t in p.ElectricChillers))
	r["electric_chiller_consumption_series"] = round.(value.(ELECCHLElecConsumptionSeries), digits=3)
	@expression(m, Year1ELECCHLElecConsumption,
		p.TimeStepScaling * sum(m[:dvThermalProduction][t,ts] / p.ElectricChillerCOP
			for t in p.ElectricChillers, ts in p.TimeStep))
	r["year_one_electric_chiller_electric_kwh"] = round(value(Year1ELECCHLElecConsumption), digits=3)
	@expression(m, Year1ELECCHLThermalProd,
		p.TimeStepScaling * sum(m[:dvThermalProduction][t,ts]
			for t in p.ElectricChillers, ts in p.TimeStep))
	r["year_one_electric_chiller_thermal_kwh"] = round(value(Year1ELECCHLThermalProd), digits=3)
	nothing
end

function add_absorption_chiller_results(m, p, r::Dict)
	r["absorpchl_kw"] = value(sum(m[:dvSize][t] for t in p.AbsorptionChillers))
	@expression(m, ABSORPCHLtoTES[ts in p.TimeStep],
		sum(m[:dvProductionToStorage][b,t,ts] for b in p.ColdTES, t in p.AbsorptionChillers))
	r["absorption_chiller_to_tes_series"] = round.(value.(ABSORPCHLtoTES), digits=3)
	@expression(m, ABSORPCHLtoLoad[ts in p.TimeStep],
		sum(m[:dvThermalProduction][t,ts] * p.ProductionFactor[t,ts] for t in p.AbsorptionChillers)
			- ABSORPCHLtoTES[ts])
	r["absorption_chiller_to_load_series"] = round.(value.(ABSORPCHLtoLoad), digits=3)
	@expression(m, ABSORPCHLThermalConsumptionSeries[ts in p.TimeStep],
		sum(m[:dvThermalProduction][t,ts] / p.AbsorptionChillerCOP for t in p.AbsorptionChillers))
	r["absorption_chiller_consumption_series"] = round.(value.(ABSORPCHLThermalConsumptionSeries), digits=3)
	@expression(m, Year1ABSORPCHLThermalConsumption,
		p.TimeStepScaling * sum(m[:dvThermalProduction][t,ts] / p.AbsorptionChillerCOP
			for t in p.AbsorptionChillers, ts in p.TimeStep))
	r["year_one_absorp_chiller_thermal_consumption_kwh"] = round(value(Year1ABSORPCHLThermalConsumption), digits=3)
	@expression(m, Year1ABSORPCHLThermalProd,
		p.TimeStepScaling * sum(m[:dvThermalProduction][t,ts]
			for t in p.AbsorptionChillers, ts in p.TimeStep))
	r["year_one_absorp_chiller_thermal_prod_kwh"] = round(value(Year1ABSORPCHLThermalProd), digits=3)
    @expression(m, ABSORPCHLElectricConsumptionSeries[ts in p.TimeStep],
        sum(m[:dvThermalProduction][t,ts] / p.AbsorptionChillerElecCOP for t in p.AbsorptionChillers))
    r["absorption_chiller_electric_consumption_series"] = round.(value.(ABSORPCHLElectricConsumptionSeries), digits=3)
    @expression(m, Year1ABSORPCHLElectricConsumption,
        p.TimeStepScaling * sum(m[:dvThermalProduction][t,ts] / p.AbsorptionChillerElecCOP 
            for t in p.AbsorptionChillers, ts in p.TimeStep))
    r["year_one_absorp_chiller_electric_consumption_kwh"] = round(value(Year1ABSORPCHLElectricConsumption), digits=3)
    nothing
end

function add_hot_tes_results(m, p, r::Dict)
	@expression(m, HotTESSizeKWH, sum(m[:dvStorageCapEnergy][b] for b in p.HotTES))
	r["hot_tes_size_kwh"] = round(value(HotTESSizeKWH), digits=3)
	@expression(m, HotTESDischargeSeries[ts in p.TimeStep], sum(m[:dvDischargeFromStorage][b, ts]
		for b in p.HotTES))
	r["hot_tes_thermal_production_series"] = round.(value.(HotTESDischargeSeries), digits=5)
	@expression(m, HotTESsoc[ts in p.TimeStep], sum(m[:dvStorageSOC][b,ts] for b in p.HotTES))
	r["hot_tes_pct_soc_series"] = round.(value.(HotTESsoc) / value(HotTESSizeKWH), digits=5)
	nothing
end

function add_cold_tes_results(m, p, r::Dict)
	@expression(m, ColdTESSizeKWHT, sum(m[:dvStorageCapEnergy][b] for b in p.ColdTES))
	r["cold_tes_size_kwht"] = round(value(ColdTESSizeKWHT), digits=5)
	@expression(m, ColdTESDischargeSeries[ts in p.TimeStep], sum(m[:dvDischargeFromStorage][b, ts]
		for b in p.ColdTES))
	r["cold_tes_thermal_production_series"] = round.(value.(ColdTESDischargeSeries), digits=5)
	@expression(m, ColdTESsoc[ts in p.TimeStep], sum(m[:dvStorageSOC][b,ts] for b in p.ColdTES))
	r["cold_tes_pct_soc_series"] = round.(value.(ColdTESsoc) / value(ColdTESSizeKWHT), digits=5)
	nothing
end

function add_newboiler_results(m, p, r::Dict)
	##NewBoiler results go here; need to populate expressions for first collection
	r["newboiler_size_kw"] = round(value(m[:dvSize]["NEWBOILER"]), digits=3)
    @expression(m, FuelToNewBoiler[ts in p.TimeStep], m[:dvFuelUsage]["NEWBOILER", ts])
	r["fuel_to_newboiler_series"] = round.(value.(FuelToNewBoiler), digits=3)
	@expression(m, NewBoilerThermalProd[ts in p.TimeStep], p.ProductionFactor["NEWBOILER",ts] * m[:dvThermalProduction]["NEWBOILER",ts])
	r["newboiler_thermal_production_series"] = round.(value.(NewBoilerThermalProd), digits=3)
	@expression(m, NewBoilerFuelUsed, sum(m[:dvFuelUsage]["NEWBOILER", ts] for ts in p.TimeStep))
	r["year_one_fuel_to_newboiler_kwh"] = round(value(NewBoilerFuelUsed), digits=3)
	@expression(m, NewBoilerThermalProduced, sum(p.ProductionFactor["NEWBOILER",ts] * m[:dvThermalProduction]["NEWBOILER",ts]
		for ts in p.TimeStep))
	r["year_one_newboiler_thermal_production_kwh"] = round(value(NewBoilerThermalProduced), digits=3)
	@expression(m, NewBoilerToHotTES[ts in p.TimeStep],
		sum(m[:dvProductionToStorage]["HotTES","NEWBOILER",ts]))
	r["newboiler_thermal_to_tes_series"] = round.(value.(NewBoilerToHotTES), digits=3)
    if !isempty(p.SteamTurbineTechs)
        @expression(m, NewBoilerToSteamTurbine[ts in p.TimeStep], m[:dvThermalToSteamTurbine]["NEWBOILER",ts])
        r["newboiler_thermal_to_steamturbine_series"] = round.(value.(NewBoilerToSteamTurbine), digits=3)
    else
		@expression(m, NewBoilerToSteamTurbine[ts in p.TimeStep], 0.0)
        r["newboiler_thermal_to_steamturbine_series"] = round.(zeros(p.TimeStepCount), digits=3)
    end
	@expression(m, NewBoilerToLoad[ts in p.TimeStep],
		sum((m[:dvThermalProduction]["NEWBOILER",ts] - NewBoilerToSteamTurbine[ts]) * p.ProductionFactor["NEWBOILER",ts] - NewBoilerToHotTES[ts] ))
	r["newboiler_thermal_to_load_series"] = round.(value.(NewBoilerToLoad), digits=3)
	@expression(m, TotalNewBoilerFuelCharges,
		p.pwf_fuel["NEWBOILER"] * p.TimeStepScaling * sum(p.FuelCost["NEWBOILERFUEL",ts] * m[:dvFuelUsage]["NEWBOILER",ts]
			for ts in p.TimeStep))
	r["total_newboiler_fuel_cost"] = round(value(TotalNewBoilerFuelCharges * m[:r_tax_fraction_offtaker]), digits=3)
	r["year_one_newboiler_fuel_cost"] = round(value(TotalNewBoilerFuelCharges / p.pwf_fuel["NEWBOILER"]), digits=3)
	nothing
end

function add_steamturbine_results(m, p, r::Dict)
	r["SteamTurbine"] = Dict()
	r["steamturbine_kw"] = round(value(sum(m[:dvSize][t] for t in p.SteamTurbineTechs)), digits=3)
    @expression(m, Year1SteamTurbineThermalConsumption,
		p.TimeStepScaling * sum(m[:dvThermalToSteamTurbine][tst,ts] for tst in p.TechCanSupplySteamTurbine, ts in p.TimeStep))
    r["year_one_steamturbine_thermal_consumption"] = round(value(Year1SteamTurbineThermalConsumption), digits=3)
    @expression(m, Year1SteamTurbineElecProd,
		p.TimeStepScaling * sum(m[:dvRatedProduction][t,ts] * p.ProductionFactor[t, ts]
			for t in p.SteamTurbineTechs, ts in p.TimeStep))
	r["year_one_steamturbine_electric_energy_produced"] = round(value(Year1SteamTurbineElecProd), digits=3)
	@expression(m, Year1SteamTurbineThermalProd,
		p.TimeStepScaling * sum(m[:dvThermalProduction][t,ts] for t in p.SteamTurbineTechs, ts in p.TimeStep))
	r["year_one_steamturbine_thermal_energy_produced"] = round(value(Year1SteamTurbineThermalProd), digits=3)
    @expression(m, SteamTurbineThermalConsumption[ts in p.TimeStep],
		sum(m[:dvThermalToSteamTurbine][tst,ts] for tst in p.TechCanSupplySteamTurbine))
    r["steamturbine_thermal_consumption_series"] = round.(value.(SteamTurbineThermalConsumption), digits=3)
	@expression(m, SteamTurbineElecProdTotal[ts in p.TimeStep],
		sum(m[:dvRatedProduction][t,ts] * p.ProductionFactor[t, ts] for t in p.SteamTurbineTechs))
	r["steamturbine_electric_production_series"] = round.(value.(SteamTurbineElecProdTotal), digits=3)
	@expression(m, SteamTurbinetoGrid[ts in p.TimeStep], sum(m[:dvProductionToGrid][t,u,ts]
			for t in p.SteamTurbineTechs, u in p.ExportTiersByTech[t]))
	r["steamturbine_to_grid_series"] = round.(value.(SteamTurbinetoGrid), digits=3)
	@expression(m, SteamTurbinetoBatt[ts in p.TimeStep],
		sum(m[:dvProductionToStorage]["Elec",t,ts] for t in p.SteamTurbineTechs))
	r["steamturbine_to_battery_series"] = round.(value.(SteamTurbinetoBatt), digits=3)
	@expression(m, SteamTurbinetoLoad[ts in p.TimeStep],
		sum(m[:dvRatedProduction][t, ts] * p.ProductionFactor[t, ts] * p.LevelizationFactor[t]
			for t in p.SteamTurbineTechs) - SteamTurbinetoBatt[ts] - SteamTurbinetoGrid[ts])
	r["steamturbine_electric_to_load_series"] = round.(value.(SteamTurbinetoLoad), digits=3)
	@expression(m, SteamTurbinetoHotTES[ts in p.TimeStep],
		sum(m[:dvProductionToStorage]["HotTES",t,ts] for t in p.SteamTurbineTechs))
	r["steamturbine_thermal_to_tes_series"] = round.(value.(SteamTurbinetoHotTES), digits=3)
	@expression(m, SteamTurbineThermalToLoad[ts in p.TimeStep],
		sum(m[:dvThermalProduction][t,ts] for t in p.SteamTurbineTechs) - SteamTurbinetoHotTES[ts])
	r["steamturbine_thermal_to_load_series"] = round.(value.(SteamTurbineThermalToLoad), digits=3)
	nothing
end

function add_ghp_results(m, p, r::Dict)
	@expression(m, GHPOptionChosen, sum(g * m[:binGHP][g] for g in p.GHPOptions))
	r["GHPOptionChosen"] = convert(Int64, value(GHPOptionChosen))
    if r["GHPOptionChosen"] > 0
        @expression(m, HeatingThermalReductionWithGHP[ts in p.TimeStep],
		    sum(p.HeatingThermalReductionWithGHP[g,ts] * m[:binGHP][g] for g in p.GHPOptions))
        r["HeatingThermalReductionWithGHP"] = round.(value.(HeatingThermalReductionWithGHP), digits=3)
        @expression(m, CoolingThermalReductionWithGHP[ts in p.TimeStep],
		    sum(p.CoolingThermalReductionWithGHP[g,ts] * m[:binGHP][g] for g in p.GHPOptions))
        r["CoolingThermalReductionWithGHP"] = round.(value.(CoolingThermalReductionWithGHP), digits=3)
    else
        r["HeatingThermalReductionWithGHP"] = zeros(length(p.TimeStep))
        r["CoolingThermalReductionWithGHP"] = zeros(length(p.TimeStep))
    end
    nothing
end

function add_util_results(m, p, r::Dict)
    net_capital_costs_plus_om = value(m[:TotalTechCapCosts] + m[:TotalStorageCapCosts] + m[:GHPCapCosts]) +
                                value(m[:TotalPerUnitSizeOMCosts] + m[:TotalPerUnitProdOMCosts] 
                                    + m[:TotalHourlyCHPOMCosts] + m[:GHPOMCosts]) * m[:r_tax_fraction_owner] +
                                value(m[:TotalFuelCharges]) * m[:r_tax_fraction_offtaker]

    total_om_costs_after_tax = value(m[:TotalPerUnitSizeOMCosts] + m[:TotalPerUnitProdOMCosts] 
                                   + m[:TotalHourlyCHPOMCosts] + m[:GHPOMCosts]) * m[:r_tax_fraction_owner]

	year_one_om_costs_after_tax = total_om_costs_after_tax / (p.pwf_om * p.two_party_factor)

    push!(r, Dict("year_one_utility_kwh" => round(value(m[:Year1UtilityEnergy]), digits=2),
						"year_one_energy_cost" => round(value(m[:Year1EnergyCost]), digits=2),
						"year_one_demand_cost" => round(value(m[:Year1DemandCost]), digits=2),
						"year_one_demand_tou_cost" => round(value(m[:Year1DemandTOUCost]), digits=2),
						"year_one_demand_flat_cost" => round(value(m[:Year1DemandFlatCost]), digits=2),
						"year_one_coincident_peak_cost" => round(value(m[:Year1CPCost]), digits=2),
						"year_one_export_benefit" => round(value(m[:ExportBenefitYr1]), digits=0),
						"year_one_fixed_cost" => round(m[:Year1FixedCharges], digits=0),
						"year_one_min_charge_adder" => round(value(m[:Year1MinCharges]), digits=2),
						"year_one_bill" => round(value(m[:Year1Bill]), digits=2),
						"year_one_payments_to_third_party_owner" => round(value(m[:TotalDemandCharges]) / p.pwf_e, digits=0),
						"total_energy_cost" => round(value(m[:TotalEnergyChargesUtil]) * m[:r_tax_fraction_offtaker], digits=2),
						"total_demand_cost" => round(value(m[:TotalDemandCharges]) * m[:r_tax_fraction_offtaker], digits=2),
						"total_coincident_peak_cost" => round(value(m[:TotalCPCharges]) * m[:r_tax_fraction_offtaker], digits=2),
						"total_fixed_cost" => round(m[:TotalFixedCharges] * m[:r_tax_fraction_offtaker], digits=2),
						"total_export_benefit" => round(value(m[:TotalExportBenefit]) * m[:r_tax_fraction_offtaker], digits=2),
						"total_min_charge_adder" => round(value(m[:MinChargeAdder]) * m[:r_tax_fraction_offtaker], digits=2),
						"net_capital_costs_plus_om" => round(net_capital_costs_plus_om, digits=0),
						"average_annual_energy_exported_wind" => round(value(m[:ExportedElecWIND]), digits=0),
						"average_annual_energy_curtailed_wind" => round(value(m[:CurtailedElecWIND]), digits=0),
                        "average_annual_energy_exported_gen" => round(value(m[:ExportedElecGEN]), digits=0),
						"net_capital_costs" => round(value(m[:TotalTechCapCosts] + m[:TotalStorageCapCosts] + m[:GHPCapCosts]), digits=2),
						"total_om_costs_after_tax" => round(total_om_costs_after_tax, digits=0),
						"year_one_om_costs_after_tax" => round(year_one_om_costs_after_tax, digits=0),
						"year_one_om_costs_before_tax" => round(year_one_om_costs_after_tax / m[:r_tax_fraction_owner], digits=0),
						"off_grid_flag" => p.OffGridFlag,
						"total_production_incentive_after_tax" => round(value(m[:TotalProductionIncentive]) * m[:r_tax_fraction_owner], digits=2),
						"total_fuel_charges_after_tax" => round(value(m[:TotalFuelCharges]) * m[:r_tax_fraction_offtaker], digits=2)
					)...)

    @expression(m, GridToLoad[ts in p.TimeStep],
                sum(m[:dvGridPurchase][u,ts] for u in p.PricingTier) - m[:dvGridToStorage][ts] )
    r["GridToLoad"] = round.(value.(GridToLoad), digits=3)

end
