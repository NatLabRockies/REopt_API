# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NREL/REopt_API/blob/master/LICENSE.

function string_dictkeys_tosymbols(d::Dict)
    d2 = Dict()
    for (k, v) in d
        d2[Symbol(k)] = v
    end
    return d2
end

function filter_dict_to_match_struct_field_names(d::Dict, s::DataType)
    f = fieldnames(s)
    d2 = Dict()
    for k in f
        if haskey(d, k)
            d2[k] = d[k]
        else
            @warn "utils.jl: dict is missing struct field $(k)!"
        end
    end
    return d2
end 

"""
    array_of_array_to_2D_array(aa)

Convert Array of Array to a two dimensional array
```@example
array_of_array_to_2D_array([[1,2,3], [4, 5, 6]])
````
"""
function array_of_array_to_2D_array(aa)
    transpose([aa[i][j] for j in 1:length(aa[1]), i in 1:length(aa)])
end


Base.@kwdef struct Parameter
	 ###  Sets  ###
	 Storage::Array{String,1}      # Set B in math; new; B = "Elec","HotThermal","ColdThermal"
     TechClass::Array{String,1}    # Set C
	 DemandBin::UnitRange{Int64}   # Set E
	 FuelType::Array{String,1}     # Set F; new; F = {"NaturalGas"} for CHP and whatever fuel source is used for Boiler
     TimeStep::UnitRange{Int64}    # Set H
     TimeStepBat::UnitRange{Int64} # Set H union {0}
	 Subdivision::Array{String,1}	# Set K; new; elements = { "CapCost", "FuelBurn" }
	 Month::UnitRange{Int64} 	    # Set M
	 DemandMonthsBin::UnitRange{Int64}	# Set N
	 Ratchets::UnitRange{Int64}	   # Set R
     Seg::UnitRange{Int64}	       # Set S
	 Tech::Array{String,1}         # Set T in math
	 FuelBin::UnitRange{Int64}	   # To be removed
	 PricingTier::UnitRange{Int64}  # Set U: Pricing Tiers (proposed revision) #new
	 NMILRegime::Array{String,1}	# Set V: Net-metering Regimes
     CPPeriod::UnitRange{Int64}     # Set P: Coincident Peak Periods

	 ###  Subsets and Indexed Sets  ####
	 ElecStorage::Array{String,1}  # B^{e} \subset B: Electrical energy storage systems
	 TimeStepRatchetsMonth::Array{Array{Int64,1},1}   #  H_m: Time steps in month m
	 TimeStepRatchets::Array{Array{Int64,1},1}   #  H_r: Time steps in ratchet r
     TimeStepsWithGrid::Array{Int64,1}  # H_g: Time steps with grid connection
     TimeStepsWithoutGrid::Array{Int64,1}	 # H \setminus H_g: Time steps without grid connection 
	 DemandLookbackMonths::Array{Any,1}   # M^{lb}: fixed Look back months considered for peak pricing
	 DemandLookbackRange::Int   # number of Look back months considered for peak pricing
	 SegByTechSubdivision::AxisArray # S_{kt}: System size segments from segmentation k applied to technology t
	 TechsInClass::AxisArray # T_c \subset T: Technologies that are in class c
	 TechsByFuelType::AxisArray # T_f \subset T: Technologies that burn fuel type f
	 TechsByNMILRegime::AxisArray # T_v \subset T: Technologies that may acess net-meterng regime v
	 ElectricTechs::Array{String,1}  # T^{e} \subset T: Electricity-producing technologies
	 FuelBurningTechs::Array{String,1}  # T^{f} \subset T: Fuel-burning technologies
	 TechsNoTurndown::Array{String,1}  # T^{ac} \subset T: Technologies that cannot turn down, i.e., PV and wind
     CoincidentPeakLoadTimeSteps::AxisArray # H^{cp}_m: Coincident peak time steps in month m
     
	 ###  Parameters and Tables supporting Indexed Sets ###
	 TechToNMILMapping::AxisArray  # Defines set T_v: Technologies that may be access net-metering regime v

	 ###  Scaling Parameters ###
	 TimeStepScaling::Float64  # \Delta: Time step scaling [h], eg. 30 minute resolution -> TimeStepScaling = 0.5
	 
	 ###  Parameters for Costs and their Functional Forms ###
     AnnualMinCharge::Float64    # c^{amc}: Utility annual minimum charge
     MonthlyMinCharge::Float64    # c^{mmc}: Utility monthly minimum charge  (not in math; will use this in min charge calculation)
	 FixedMonthlyCharge::Float64  # c^{fmc}: Utility monthly fixed charge
	 FuelCost::AxisArray # c^{u}_{f}: Unit cost of fuel type f [$/kWh]  in math  (NEW)
	 ElecRate::Array{Float64, 2}  #   c^{g}_{uh}: Grid energy cost in energy demand tier u during time step h  (NEW)
	 OMperUnitSize::AxisArray # c^{om}_{t}: Operation and maintenance cost of technology t per unit of system size [$/kW]
     OMcostPerUnitProd::AxisArray
	 OMcostPerUnitHourPerSize::AxisArray

	 GridExportRates::AxisArray  # c^{e}_{uh}: Export rate for energy in energy pricing tier u in time step h   (NEW)
	 CapCostSlope::AxisArray   # c^{cm}_{ts}: Slope of capital cost curve for technology t in segment s
     CapCostYInt::AxisArray  # c^{cb}_{ts}: Y-Intercept of capital cost curve for technology t in segment s
     CapCostX::AxisArray    # X-value of inflection point (will be changed)
	 #For the replacement of CapCostX, see new parameters SegmentLB and SegmentUB in section "System size and fuel limit parameters"
	 DemandRates::Array{Float64, 2}  # c^{r}_{re}: Cost per unit peak demand in tier e during ratchet r
	 DemandRatesMonth::Array{Float64, 2}   # c^{rm}_{mn}: Cost per unit peak demand in tier n during month m
     CoincidentPeakRates::AxisArray   # c^{cp}_p: Cost per unit peak demand during coincident peak hours of CP period p
     
	 ###  Demand Parameters ###
	 ElecLoad::Array{Float64,1}  # \delta^{d}_{h}: Electrical load in time step h   [kW]
     DemandLookbackPercent::Float64    # \delta^{lp}: Demand Lookback proportion [fraction]
     MaxDemandInTier::Array{Float64,1}  # \delta^{t}_{e}: Maximum power demand in ratchet e
     MaxDemandMonthsInTier::Array{Float64,1}   # \delta^{mt}_{n}: Maximum monthly power demand in tier n
     MaxUsageInTier::Array{Float64,1}   # \delta^{tu}_{u}: Maximum monthly energy demand in tier u
	 
	 ###  Incentive Parameters ###
	 NMILLimits::AxisArray   # i^{n}_{v}: Net metering and interconnect limits in net metering regime v [kW]
     MaxProdIncent::AxisArray      # \bar{i}_t: Upper incentive limit for technology t [$]
	 ProductionIncentiveRate::AxisArray  # i^{r}_{t}: Incentive rate for technology t [$/kWh] (NEW)
	 MaxSizeForProdIncent::AxisArray  # \bar{i}^{\sigma}_t: Maximum system size to obtain production incentive for technology t [kW]

	 ###  Technology-specific Time-series Factor Parameters ###
	 ProductionFactor::AxisArray    #f^{p}_{th}  Production factor of technology t and time step h  [unitless]  (NEW)

	 ###  Technology-specific Factor Parameters ###
	 TurbineDerate::AxisArray  # f^{d}_{t}: Derate factor for turbine technologyt [unitless]
     MinTurndown::AxisArray    # f^{td}_{t}:  Minimum turn down for technology t [unitless]
     pwf_prod_incent::AxisArray   # f^{pi}_t: Present worth factor for incentives for technology t [unitless]
	 LevelizationFactor::AxisArray    # f^{l}_{t}: Levelization factor of technology t [unitless]

	 ###  Generic Factor Parameters ###
	 pwf_om::Float64  # f^{om}: Operations and maintenance present worth factor [unitless]
     pwf_e::Float64   # f^{e}: Energy present worth factor [unitless]
	 pwf_fuel::AxisArray
	 r_tax_owner::Float64      # f^{tow}: Tax rate factor for owner [fraction]
     r_tax_offtaker::Float64   # f^{tot}: Tax rate factor for offtaker [fraction]
     pwf_owner::Float64    # Annuity with zero escalation and owner's discount rate
     pwf_offtaker::Float64 # Annuity with zero escalation and offtaker's discount rate
     pwfs_emissions_cost::Dict{String, Any} # Cost of emissions present worth factors for grid and onsite fuelburn emissions [unitless]
     pwfs_grid_emissions_lbs::Dict{String, Any} # Emissions [lbs] present worth factors for grid emissions [unitless]

	 ###  System Size and Fuel Limit Parameters ###
	 TechClassMinSize::AxisArray   #  \ubar{b}^{\sigma}_{c}: Minimum system size for technology class c [kW]
	 MaxSize::AxisArray    #  \bar{b}^{\sigma}_{t}: Maximum system size for technology t [kW]
	 SegmentMinSize::AxisArray # \ubar{b}^{\sigma s}_{tks}: Minimum system size for technology t, subdivision k, segments
	 SegmentMaxSize::AxisArray  # \bar{b}^{\sigma s}_{tks}: Maximum system size for technology t, subdivision k, segments
	 FuelLimit::AxisArray # b^{fa}_{f}: Amount of available fuel for type f [kWh]   (NEW)

	 ###  Efficiency Parameters ###
	 ChargeEfficiency::AxisArray  # \eta^{esi}_{bt}: Efficiency of charging storage system b using technology t  [fraction] (NEW)
	 GridChargeEfficiency::Float64   # \eta^{esig}: Efficiency of charging electrical storage using grid power [fraction] (NEW)
     DischargeEfficiency::AxisArray  # \eta^{eso}_{b}: Efficiency of discharging storage system b [fraction] (NEW)

	 ###  Storage Parameters ###   # \ubar{w}^{bkW}_{b}: Minimum power capacity of storage system b (needs to be indexed on b )
     StorageMinChargePcent::Float64     #  \ubar{w}^{mcp}_{b}: Minimum state of charge of storage system b
     InitSOC::Float64    # w^{i}_{b} Initial percent state of charge for storage system b
     StorageMinSizeEnergy::AxisArray     # \bar{w}^{bkWh}_{b}: Maximum energy capacity of storage system b [kWh]
     StorageMaxSizeEnergy::AxisArray     # \ubar{w}^{bkWh}_{b}: Minimum energy capacity of storage system b [kWh]
     StorageMinSizePower::AxisArray     # \bar{w}^{bkW}_{b}: Maximum power capacity of storage system b [kW]
     StorageMaxSizePower::AxisArray     # \ubar{w}^{bkW}_{b}: Minimum power capacity of storage system b [kW]
     StorageMinSOC::AxisArray     #  \ubar{w}^{mcp}_{b}: Minimum state of charge of storage system b [fraction]
     StorageInitSOC::AxisArray  #Initial state of charge of storage system b [fraction]
     StorageCanGridCharge::Bool  # Boolean for storage system [fraction]

	 ###  Fuel Burn Parameters ###
	 FuelBurnSlope::AxisArray # m^\text{fm}_{t}: Fuel burn rate slope parameter for technology t
	 FuelBurnYInt::AxisArray # m^\text{fb}_{t}: Fuel burn rate slope parameter for technology t

	 ### Not used or used for calculation of other parameters ###
	 two_party_factor::Float64
     analysis_years::Int64     # Used to calculate present worth factors maybe?
     AnnualElecLoadkWh::Float64
     CapCostSegCount::Int64    # Size of set S 
     FuelBinCount::Int64       # Size of set F  
     DemandBinCount ::Int64    # Size of set E
     DemandMonthsBinCount::Int64   # Size of set N
     TimeStepCount::Int64          # Size of set H
     Points::UnitRange{Int64}      # CapCostSegCount+1; this is going to be the size of set S^{c} now
     PricingTierCount::Int64    # Size of set U

     # new parameters for reformulation
     StorageCostPerKW::AxisArray
     StorageCostPerKWH::AxisArray
	 ElectricDerate::AxisArray

     # New Sets
     ExportTiers::Array{String,1}
	 ExportTiersByTech::AxisArray
	 TechsByExportTier::AxisArray
     ExportTiersBeyondSiteLoad::Array{String, 1}
     TechsCannotCurtail::Array{String, 1}

    # Feature Additions
     TechToLocation::AxisArray
     MaxSizesLocation::Array{Float64, 1}
     Location::UnitRange
	 AddSOCIncentive::Int64

    # Annual RE parameters
     TechPercentRE::AxisArray
     MinAnnualPercentREElec::Union{Float64,Nothing}
     MaxAnnualPercentREElec::Union{Float64,Nothing}
     IncludeExportedREElecinTotal::Bool

    # Emissions parameters
     IncludeExportedElecEmissionsInTotal::Bool
     MinPercentCO2EmissionsReduction::Union{Float64,Nothing}
     MaxPercentCO2EmissionsReduction::Union{Float64,Nothing}
     BAUYr1Emissions_CO2::Float64
     BAUYr1Emissions_NOx::Float64
     BAUYr1Emissions_SO2::Float64
     BAUYr1Emissions_PM25::Float64
     BAUYr1Emissions_grid_CO2::Float64
     BAUYr1Emissions_grid_NOx::Float64
     BAUYr1Emissions_grid_SO2::Float64
     BAUYr1Emissions_grid_PM25::Float64
     GridEmissionsFactor_CO2::Array{Float64,1}
     GridEmissionsFactor_NOx::Array{Float64,1}
     GridEmissionsFactor_SO2::Array{Float64,1}
     GridEmissionsFactor_PM25::Array{Float64,1}
     TechEmissionsFactors_CO2::AxisArray
     TechEmissionsFactors_NOx::AxisArray
     TechEmissionsFactors_SO2::AxisArray
     TechEmissionsFactors_PM25::AxisArray
     CO2_dollars_tonne::Float64
     NOx_dollars_tonne_grid::Float64
     SO2_dollars_tonne_grid::Float64
     PM25_dollars_tonne_grid::Float64
     NOx_dollars_tonne_onsite_fuelburn::Float64
     SO2_dollars_tonne_onsite_fuelburn::Float64
     PM25_dollars_tonne_onsite_fuelburn::Float64
     Include_climate_in_objective::Bool
     Include_health_in_objective::Bool
     Lbs_per_tonne::Float64

	# Added for CHP
	HotTES::Array{String,1}
	ColdTES::Array{String,1}
	ThermalStorage::Array{String,1}
	CHPTechs::Array{String,1}
	ElectricChillers::Array{String,1}
	AbsorptionChillers::Array{String,1}
	CoolingTechs::Array{String,1}
	HeatingTechs::Array{String,1}
	BoilerTechs::Array{String,1}
	HeatingLoad::Array{Float64,1}
	CoolingLoad::Array{Float64,1}
	BoilerEfficiency::AxisArray
	ElectricChillerCOP::Float64
    AbsorptionChillerCOP::Float64
    AbsorptionChillerElecCOP::Float64
	CHPThermalProdSlope::AxisArray
	CHPThermalProdIntercept::AxisArray
	FuelBurnYIntRate::AxisArray
	CHPThermalProdFactor::AxisArray
	CHPStandbyCharge::Float64
	CHPDoesNotReduceDemandCharges::Int64
	StorageDecayRate::AxisArray
    AllBoilerTechs::Array{String,1}
    AllTechsForSteamTurbine::Array{String,1}
    SteamTurbineTechs::Array{String,1}
    TechCanSupplySteamTurbine::Array{String,1}
    STElecOutToThermInRatio::Float64
    STThermOutToThermInRatio::Float64
    # GHP Arrays of different GHP options with index 1 being NO GHP
    GHPOptions::UnitRange{Int64}
    RequireGHPPurchase::Int64
    GHPHeatingThermalServed::Array{Float64,2}  # Array of heating load (thermal!) profiles served by GHP
    GHPCoolingThermalServed::Array{Float64,2}  # Array of cooling load profiles served by GHP
    HeatingThermalReductionWithGHP::Array{Float64,2}  # Array of heating load reduction (thermal!) profile from GHP retrofit
    CoolingThermalReductionWithGHP::Array{Float64,2}  # Array of cooling load reduction (thermal!) profile from GHP retrofit
    GHPElectricConsumed::Array{Float64,2}  # Array of electric load profiles consumed by GHP
    GHPInstalledCost::Array{Float64,1}  # Array of installed cost for GHP options
    GHPOMCost::Array{Float64,1}  # Array of O&M cost for GHP options
    CHPSupplementaryFireMaxRatio::Float64
    CHPSupplementaryFireEfficiency::Float64
    CapCostSupplementaryFiring::AxisArray # Array of capital cost for supplementary firing for CHP
	#Offgrid systems
	OffGridFlag::Bool
	TechsRequiringSR::Array{String,1}
	TechsProvidingSR::Array{String,1}
	MinLoadMetPct::Float64
	SRrequiredPctLoad::Float64
	SRrequiredPctTechs::AxisArray
    OtherCapitalCosts::Float64
    OtherAnnualCosts::Float64
end


function Parameter(d::Dict)
    can_be_empty = (
        "MaxSize",
        "OMperUnitSize",
        "OMcostPerUnitProd",
		"OMcostPerUnitHourPerSize",
        "MaxProdIncent",
        "MaxSizeForProdIncent",
        "TurbineDerate",
        "MinTurndown",
        "pwf_prod_incent",
        "LevelizationFactor",
        "NMILLimits",
        "TechClassMinSize",
		"TechsByExportTier",
		"ExportTiersByTech",
		"NMILRegime",
		"TechsByNMILRegime",
		"TechsByFuelType",
		"FuelCost"
     )
	for x in ["Tech","FuelType","CHPTechs"]
		if typeof(d[x]) === Array{Any, 1}  # came from Python as empty array
			d[x] = convert(Array{String, 1}, d[x])
		end
	end
    for x in can_be_empty
        if typeof(x) === Array{Any, 1}  # came from Python as empty array
            d[x] = convert(Array{Float64, 1}, d[x])
        end
    end
    d = convert(Dict{Union{String, Symbol}, Any}, d)

    d[:Seg] = 1:d["CapCostSegCount"]
    d[:Points] = 0:d["CapCostSegCount"]
    d[:Month] = 1:12
    d[:Ratchets] = 1:d["NumRatchets"]
    d[:FuelBin] = 1:d["FuelBinCount"]
	d[:PricingTier] = 1:d["PricingTierCount"]
    d[:DemandBin] = 1:d["DemandBinCount"]
    d[:DemandMonthsBin] = 1:d["DemandMonthsBinCount"]
    d[:TimeStep] = 1:d["TimeStepCount"]
    d[:TimeStepBat] = 0:d["TimeStepCount"]
    n_location = length(d["MaxSizesLocation"])
    d[:Location] = 1:n_location
    d[:CPPeriod] = 1:d["CoincidentPeakPeriodCount"]
    d[:GHPOptions] = 1:length(d["GHPInstalledCost"])

    # the following array manipulation may have to adapt once length(d["Subdivision"]) > 1
    seg_min_size_array = reshape(transpose(reshape(d["SegmentMinSize"], length(d[:Seg]), length(d["Tech"]))),
                                 length(d["Tech"]), length(d["Subdivision"]), length(d[:Seg]))
    seg_max_size_array = reshape(transpose(reshape(d["SegmentMaxSize"], length(d[:Seg]), length(d["Tech"]))),
                                length(d["Tech"]), length(d["Subdivision"]), length(d[:Seg]))

    # convert vectors to AxisArray's with axes for REopt JuMP model
    d["TurbineDerate"] = AxisArray(d["TurbineDerate"], d["Tech"])
    d["TechToLocation"] = vector_to_axisarray(d["TechToLocation"], d["Tech"], d[:Location])
    d["pwf_prod_incent"] = AxisArray(d["pwf_prod_incent"], d["Tech"])
    d["LevelizationFactor"] = AxisArray(d["LevelizationFactor"], d["Tech"])
    d["OMperUnitSize"] = AxisArray(d["OMperUnitSize"], d["Tech"])
    d["CapCostSlope"] = vector_to_axisarray(d["CapCostSlope"], d["Tech"], d[:Seg])
    d["CapCostYInt"] = vector_to_axisarray(d["CapCostYInt"], d["Tech"], d[:Seg])
    d["CapCostX"] = vector_to_axisarray(d["CapCostX"], d["Tech"], d[:Points])
    d["MaxProdIncent"] = AxisArray(d["MaxProdIncent"], d["Tech"])
    d["MaxSizeForProdIncent"] = AxisArray(d["MaxSizeForProdIncent"], d["Tech"])
    d["MaxSize"] = AxisArray(d["MaxSize"], d["Tech"])
    d["TechClassMinSize"] = AxisArray(d["TechClassMinSize"], d["TechClass"])
    d["MinTurndown"] = AxisArray(d["MinTurndown"], d["Tech"])
    d["DemandRates"] = transpose(reshape(d["DemandRates"], d["DemandBinCount"], d["NumRatchets"]))
    d["DemandRatesMonth"] = transpose(reshape(d["DemandRatesMonth"], d["DemandMonthsBinCount"], 12))
    d["NMILLimits"] = AxisArray(d["NMILLimits"], d["NMILRegime"])
    d["TechToNMILMapping"] = vector_to_axisarray(d["TechToNMILMapping"], d["Tech"], d["NMILRegime"])
    d["OMcostPerUnitProd"] = AxisArray(d["OMcostPerUnitProd"], d["Tech"])
    d["OMcostPerUnitHourPerSize"] = AxisArray(d["OMcostPerUnitHourPerSize"], d["Tech"])

    d["TechEmissionsFactors_CO2"] = AxisArray(d["TechEmissionsFactors_CO2"], d["Tech"])
    d["TechEmissionsFactors_NOx"] = AxisArray(d["TechEmissionsFactors_NOx"], d["Tech"])
    d["TechEmissionsFactors_SO2"] = AxisArray(d["TechEmissionsFactors_SO2"], d["Tech"])
    d["TechEmissionsFactors_PM25"] = AxisArray(d["TechEmissionsFactors_PM25"], d["Tech"])
    d["TechPercentRE"] = AxisArray(d["TechPercentRE"], d["Tech"])

    if !isempty(d["CoincidentPeakLoadTimeSteps"])
        d["CoincidentPeakRates"] = AxisArray(d["CoincidentPeakRates"], d[:CPPeriod])
        d["CoincidentPeakLoadTimeSteps"] = permutedims(hcat(d["CoincidentPeakLoadTimeSteps"]...), (2,1))
        d["CoincidentPeakLoadTimeSteps"] = AxisArray(d["CoincidentPeakLoadTimeSteps"], d[:CPPeriod], 1:size(d["CoincidentPeakLoadTimeSteps"],2))
    else
        d["CoincidentPeakRates"] = AxisArray([])
        d["CoincidentPeakLoadTimeSteps"] = AxisArray([])
    end

    # Reformulation additions
    d["StorageCostPerKW"] = AxisArray(d["StorageCostPerKW"], d["Storage"])
    d["StorageCostPerKWH"] = AxisArray(d["StorageCostPerKWH"], d["Storage"])
	d["FuelCost"] = vector_to_axisarray(d["FuelCost"], d["FuelType"], d[:TimeStep])
    d["ElecRate"] = transpose(reshape(d["ElecRate"], d["TimeStepCount"], d["PricingTierCount"]))

    if !isempty(d["GridExportRates"])
        d["GridExportRates"] = AxisArray(array_of_array_to_2D_array(d["GridExportRates"]), 
                                         d["ExportTiers"], d[:TimeStep])
    else
        d["GridExportRates"] = AxisArray([])
    end
    d["FuelBurnSlope"] = AxisArray(d["FuelBurnSlope"], d["FuelBurningTechs"])
    d["FuelBurnYInt"] = AxisArray(d["FuelBurnYInt"], d["FuelBurningTechs"])
    d["ProductionFactor"] = vector_to_axisarray(d["ProductionFactor"], d["Tech"], d[:TimeStep])
    d["ProductionIncentiveRate"] = AxisArray(d["ProductionIncentiveRate"], d["Tech"])
    d["FuelLimit"] = AxisArray(d["FuelLimit"], d["FuelType"])
    d["ChargeEfficiency"] = vector_to_axisarray(d["ChargeEfficiency"], d["Tech"], d["Storage"])
    d["DischargeEfficiency"] = AxisArray(d["DischargeEfficiency"], d["Storage"])
    d["StorageMinSizeEnergy"] = AxisArray(d["StorageMinSizeEnergy"], d["Storage"])
    d["StorageMaxSizeEnergy"] = AxisArray(d["StorageMaxSizeEnergy"], d["Storage"])
    d["StorageMinSizePower"] = AxisArray(d["StorageMinSizePower"], d["Storage"])
    d["StorageMaxSizePower"] = AxisArray(d["StorageMaxSizePower"], d["Storage"])
    d["StorageMinSOC"] = AxisArray(d["StorageMinSOC"], d["Storage"])
    d["StorageInitSOC"] = AxisArray(d["StorageInitSOC"], d["Storage"])

    d["SegmentMinSize"] = AxisArray(seg_min_size_array, d["Tech"], d["Subdivision"], d[:Seg])
    d["SegmentMaxSize"] = AxisArray(seg_max_size_array, d["Tech"], d["Subdivision"], d[:Seg])
	d["ElectricDerate"] = vector_to_axisarray(d["ElectricDerate"], d["Tech"], d[:TimeStep])

	# CHP Additions
	d["CHPThermalProdSlope"] = AxisArray(d["CHPThermalProdSlope"],d["CHPTechs"])
	d["CHPThermalProdIntercept"] = AxisArray(d["CHPThermalProdIntercept"],d["CHPTechs"])
	d["FuelBurnYIntRate"] = AxisArray(d["FuelBurnYIntRate"],d["CHPTechs"])
	d["CHPThermalProdFactor"] = vector_to_axisarray(d["CHPThermalProdFactor"],d["CHPTechs"],d[:TimeStep])
	d["pwf_fuel"] = AxisArray(d["pwf_fuel"], d["Tech"])
	d["StorageDecayRate"] = AxisArray(d["StorageDecayRate"], d["Storage"])
    d["BoilerEfficiency"] = AxisArray(d["BoilerEfficiency"], d["AllBoilerTechs"])  # Always passes both values, even if partial/none
    d["CapCostSupplementaryFiring"] = AxisArray(d["CapCostSupplementaryFiring"],d["CHPTechs"])

	# Off-grid Modeling
	d["SRrequiredPctTechs"] = AxisArray(d["SRrequiredPctTechs"], d["TechsProvidingSR"])

    # Indexed Sets
    if isempty(d["FuelType"])
        d["TechsByFuelType"] = []  # array of arrays is not empty, but needs to be for AxisArray conversion
    end
    d["SegByTechSubdivision"] = vector_to_axisarray(d["SegByTechSubdivision"], d["Subdivision"], d["Tech"])
    d["TechsByFuelType"] = AxisArray(d["TechsByFuelType"], d["FuelType"])
    d["TechsInClass"] = AxisArray(d["TechsInClass"], d["TechClass"])
    d["ExportTiersByTech"] = AxisArray(d["ExportTiersByTech"], d["Tech"])
	d["TechsByExportTier"] = AxisArray(d["TechsByExportTier"], d["ExportTiers"])
    d["TechsByNMILRegime"] = AxisArray(d["TechsByNMILRegime"], d["NMILRegime"])

    d["GHPHeatingThermalServed"] = array_of_array_to_2D_array(d["GHPHeatingThermalServed"])
    d["GHPCoolingThermalServed"] = array_of_array_to_2D_array(d["GHPCoolingThermalServed"])
    d["HeatingThermalReductionWithGHP"] = array_of_array_to_2D_array(d["HeatingThermalReductionWithGHP"])
    d["CoolingThermalReductionWithGHP"] = array_of_array_to_2D_array(d["CoolingThermalReductionWithGHP"])
    d["GHPElectricConsumed"] = array_of_array_to_2D_array(d["GHPElectricConsumed"])

    d = string_dictkeys_tosymbols(d)
    d = filter_dict_to_match_struct_field_names(d, Parameter)

    param = Parameter(;d...)
end

# Additional dispatches to make things easier
function length(::Symbol)
    return 1
end


JuMP.value(::Val{false}) = 0


JuMP.value(x::Number) = x  # for @expression(REopt, ExportBenefitYr1, 0.0) and similar


JuMP.value(::MutableArithmetics.Zero) = 0


function vector_to_axisarray(v::Array{<:Any, 1}, ax1::Array{<:Any, 1}, ax2::Union{UnitRange, Array{<:Any, 1}})
    l1 = length(ax1)
    l2 = length(ax2)
    a = transpose(reshape(v, l2, l1))
    return AxisArray(a, ax1, ax2)
end
