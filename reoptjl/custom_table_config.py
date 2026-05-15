# custom_table_config.py
from reoptjl.custom_table_helpers import safe_get

"""
1. Naming Convention for Tables:
-------------------------------
To prevent namespace pollution and keep table configurations well-organized, use the following naming convention when adding new tables:

Structure:
    custom_table_<feature>

- `custom_table_`: A prefix to indicate that this variable represents a custom table configuration.
- `<feature>`: A descriptive word representing the feature, tool, or module the table is associated with the table configuration.

Examples:
- custom_table_webtool: A table configuration for the webtool feature.
- custom_table_simple: A table configuration for the simple results.
- custom_table_iedo: A table configuration for the IEDO.

Guidelines:
- Use lowercase letters and underscores to separate words.
- Avoid numbering unless necessary to differentiate versions.
- Ensure each table configuration is descriptive enough to understand its context or feature.
----------------------------------
"""
# Example table configuration
custom_table_example = [
    {
        "label": "Site Name",
        "key": "site",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.Meta.description", "None provided")
    },
    {
        "label": "Site Address",
        "key": "site_address",
        "bau_value": lambda df: safe_get(df, "inputs.Meta.address", "None provided"),
        "scenario_value": lambda df: safe_get(df, "inputs.Meta.address", "None provided")
    },
    # Example 2: Concatenating Strings
    {
        "label": "Site Location",
        "key": "site_lat_long",
        "bau_value": lambda df: f"({safe_get(df, 'inputs.Site.latitude')}, {safe_get(df, 'inputs.Site.longitude')})",
        "scenario_value": lambda df: f"({safe_get(df, 'inputs.Site.latitude')}, {safe_get(df, 'inputs.Site.longitude')})"
    },
    {
        "label": "Technology Sizing",  # This is your separator label
        "key": "tech_separator", #MUST HAVE "separator" somewhere in the name
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    # Example 3: Calculated Value (Sum of Two Fields), this does not show up in formulas
    {
        "label": "Combined Renewable Size (kW)",
        "key": "combined_renewable_size",
        "bau_value": lambda df: 0,
        "scenario_value": lambda df: safe_get(df, "outputs.PV.size_kw") + safe_get(df, "outputs.Wind.size_kw")     #NOTE: These calculations will not show up as in the excel calculations
    },

    # Example 4: Hardcoded Values
    {
        "label": "Hardcoded Values (kWh)",
        "key": "hardcoded_value",
        "bau_value": lambda df: 500,  # BAU scenario
        "scenario_value": lambda df: 1000  # other scenarios
    },

    # Example 5: Conditional Formatting
    {
        "label": "PV Size Status",
        "key": "pv_size_status",
        "bau_value": lambda df: 0,
        "scenario_value": lambda df: "Above Threshold" if safe_get(df, "outputs.PV.size_kw") > 2500 else "Below Threshold"
    },
    #Example 6 and 7: First define any data that might need to be referenced, Here I've defined two placeholders
    # Define Placeholder1
    {
        "label": "Placeholder1",
        "key": "placeholder1",
        "bau_value": lambda df: 100,  # BAU value
        "scenario_value": lambda df: 200  # Scenario value
    },
    # Define Placeholder2
    {
        "label": "Placeholder2",
        "key": "placeholder2",
        "bau_value": lambda df: 50,  # BAU value
        "scenario_value": lambda df: 100  # Scenario value
    },
    # Example 6: Calculation Without Reference to BAU
    {
        "label": "Placeholder Calculation Without BAU Reference",
        "key": "placeholder_calculation_without_bau",
        "bau_value": lambda df: 0,  # Placeholder, replaced by formula in Excel
        "scenario_value": lambda df: 0  # Placeholder, replaced by formula in Excel
    },
    # Example 7: Calculation With Reference to BAU
    {
        "label": "Placeholder Calculation With BAU Reference",
        "key": "placeholder_calculation_with_bau",
        "bau_value": lambda df: 0,  # Placeholder, replaced by formula in Excel
        "scenario_value": lambda df: 0  # Placeholder, replaced by formula in Excel
    },
    {
        "label": "Results URL",
        "key": "url",
        "bau_value": lambda df: f"https://custom-table-download-reopt-stage.its.nrel.gov/tool/results/"+safe_get(df, "webtool_uuid"),
        "scenario_value": lambda df: f"https://custom-table-download-reopt-stage.its.nrel.gov/tool/results/"+safe_get(df, "webtool_uuid")
    }
    ]

# Webtool table configuration
custom_table_webtool = [
    #####################################################################################################
    ################################ General Information  ################################
    #####################################################################################################

    {
        "label"         : "Evaluation Name",
        "key"           : "evaluation_name",
        "bau_value"     : lambda df: safe_get(df, "inputs.Meta.description", "None provided"),
        "scenario_value": lambda df: safe_get(df, "inputs.Meta.description", "None provided")
    },
    {
        "label"         : "BAU or Optimal Case?",
        "key"           : "bau_or_optimal_case",
        "bau_value"     : lambda df: "BAU",
        "scenario_value": lambda df: "Optimal"
    },
    {
        "label"         : "Site Location",
        "key"           : "site_location",
        "bau_value"     : lambda df: f"({safe_get(df, 'inputs.Site.latitude')}, {safe_get(df, 'inputs.Site.longitude')})",
        "scenario_value": lambda df: f"({safe_get(df, 'inputs.Site.latitude')}, {safe_get(df, 'inputs.Site.longitude')})"
    },
    {
        "label"         : "Results URL",
        "key"           : "url",
        "bau_value"     : lambda df: f'=HYPERLINK("https://reopt.nrel.gov/tool/results/{safe_get(df, "webtool_uuid")}", "Results Link")',
        "scenario_value": lambda df: f'=HYPERLINK("https://reopt.nrel.gov/tool/results/{safe_get(df, "webtool_uuid")}", "Results Link")'
    },
    #####################################################################################################
    ######################### System Capacities #############################
    #####################################################################################################
    {
        "label"         : "System Capacities",
        "key"           : "system_capacities_separator",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "PV capacity, new (kW)",
        "key"           : "pv_capacity_new",
        "bau_value"     : lambda df: safe_get(df, "outputs.PV.size_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.PV.size_kw") - safe_get(df, "inputs.PV.existing_kw")
    },
    {
        "label"         : "PV capacity, existing (kW)",
        "key"           : "pv_size_purchased",
        "bau_value"     : lambda df: safe_get(df, "inputs.PV.existing_kw"),
        "scenario_value": lambda df: safe_get(df, "inputs.PV.existing_kw")
    },
    {
        "label"         : "Wind Capacity (kW)",
        "key"           : "wind_capacity",
        "bau_value"     : lambda df: safe_get(df, "outputs.Wind.size_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Wind.size_kw")
    },
    # Moved Battery up in front of generator
    {
        "label"         : "Battery Power Capacity (kW)",
        "key"           : "battery_power_capacity",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricStorage.size_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricStorage.size_kw")
    },
    {
        "label"         : "Battery Energy Capacity (kWh)",
        "key"           : "battery_energy_capacity",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricStorage.size_kwh_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricStorage.size_kwh")
    },
    {
        "label"         : "Backup Generator Capacity, New (kW)",
        "key"           : "backup_generator_new",
        "bau_value"     : lambda df: safe_get(df, "outputs.Generator.size_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Generator.size_kw") - safe_get(df, "inputs.Generator.existing_kw")
    },
    {
        "label"         : "Backup Generator Capacity, Existing (kW)",
        "key"           : "backup_generator_existing",
        "bau_value"     : lambda df: safe_get(df, "inputs.Generator.existing_kw"),
        "scenario_value": lambda df: safe_get(df, "inputs.Generator.existing_kw")
    },
    {
        "label"         : "CHP Capacity (kW)",
        "key"           : "chp_capacity",
        "bau_value"     : lambda df          : safe_get(df, "outputs.CHP.size_kw_bau"),
        "scenario_value": lambda df          : safe_get(df, "outputs.CHP.size_kw")
    },
    {
        "label"         : "Steam Turbine Capacity (kW)",
        "key"           : "steam_turbine_capacity",
        "bau_value"     : lambda df: safe_get(df, "outputs.SteamTurbine.size_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.SteamTurbine.size_kw")
    },
    {
        "label"         : "Hot Water TES Capacity (gallons)",
        "key"           : "hot_water_tes_capacity",
        "bau_value"     : lambda df: safe_get(df, "outputs.HotThermalStorage.size_gal_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.HotThermalStorage.size_gal")
    },
    {
        "label"         : "Absorption Chiller Capacity (ton)",
        "key"           : "absorption_chiller_capacity",
        "bau_value"     : lambda df: safe_get(df, "outputs.AbsorptionChiller.size_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.AbsorptionChiller.size_ton")
    },
    {
        "label"         : "Chilled Water TES Capacity (gallons)",
        "key"           : "chilled_water_tes_capacity",
        "bau_value"     : lambda df: safe_get(df, "outputs.ColdThermalStorage.size_gal_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ColdThermalStorage.size_gal")
    },
    {
        "label"         : "GHP Heat Pump Capacity (ton)",
        "key"           : "ghp_heat_pump_capacity",
        "bau_value"     : lambda df: safe_get(df, "outputs.GHP.size_heat_pump_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.GHP.size_heat_pump_ton")
    },
    {
        "label"         : "GHP Ground Heat Exchanger Size (ft)",
        "key"           : "ghp_ground_heat_exchanger_size",
        "bau_value"     : lambda df: safe_get(df, "outputs.GHP.ghpghx_chosen_outputs.length_boreholes_ft_bau")*safe_get(df, "outputs.GHP.ghpghx_chosen_outputs.number_of_boreholes_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.GHP.ghpghx_chosen_outputs.length_boreholes_ft")*safe_get(df, "outputs.GHP.ghpghx_chosen_outputs.number_of_boreholes")
    },
    {
        "label"         : "Concentrating Solar Thermal Capacity (kW)",
        "key"           : "cst_capacity",
        "bau_value"     : lambda df: safe_get(df, "outputs.CST.size_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CST.size_kw")
    },
    {
        "label"         : "High Temperature Thermal Storage Capacity (kWh)",
        "key"           : "high_temp_tes_capacity",
        "bau_value"     : lambda df: safe_get(df, "outputs.HighTempThermalStorage.size_kwh_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.HighTempThermalStorage.size_kwh")
    },
    # New ASHP entries
    {
        "label"         : "ASHP Space Heating and Cooling Capacity (ton)",
        "key"           : "ashp_space_heating_cap",
        "bau_value"     : lambda df: safe_get(df, "outputs.ASHPSpaceHeater.size_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ASHPSpaceHeater.size_ton")
    },
    {
        "label"         : "ASHP Water Heating Capacity (ton)",
        "key"           : "ashp_water_heating_cap",
        "bau_value"     : lambda df: safe_get(df, "outputs.ASHPWaterHeater.size_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ASHPWaterHeater.size_ton")
    },
    #####################################################################################################
    ########################### Summary Financial Metrics ###########################
    #####################################################################################################
    {
        "label"         : "Summary Financial Metrics",
        "key"           : "summary_financial_metrics_separator",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Gross Upfront Capital Costs, Before Incentives ($)",
        "key"           : "gross_capital_costs_before_incentives",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.initial_capital_costs_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.initial_capital_costs")
    },
    {
        "label"         : "Net Upfront Capital Cost, After Incentives ($)",
        "key"           : "net_upfront_capital_cost",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.initial_capital_costs_after_incentives_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.initial_capital_costs_after_incentives")
    },
    #CALCULATED VALUE
    {
        "label"         : "Present Value of Incentives ($)",
        "key"           : "present_value_of_incentives",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Year 1 O&M Cost, Before Tax ($/yr)",
        "key"           : "year_1_om_cost_before_tax",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.year_one_om_costs_before_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.year_one_om_costs_before_tax")
    },
    {
        "label"         : "Year 1 O&M Cost, After Tax ($/yr)",
        "key"           : "year_1_om_cost_after_tax",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.year_one_om_costs_after_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.year_one_om_costs_after_tax")
    },    
    {
        "label"         : "Net Present Value ($)",
        "key"           : "npv",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.npv_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.npv")
    },
    {
        "label"         : "Payback Period, with escalation and inflation (yrs)",
        "key"           : "payback_period",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.simple_payback_years_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.simple_payback_years")
    },
    {
        "label"         : "Internal Rate of Return (%)",
        "key"           : "internal_rate_of_return",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.internal_rate_of_return_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.internal_rate_of_return")
    },
    #####################################################################################################
    ############################ Life Cycle Cost Breakdown ###########################
    #####################################################################################################
    {
        "label"         : "Life Cycle Cost Breakdown",
        "key"           : "lifecycle_cost_breakdown_separator",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Technology Capital Costs + Replacements, After Incentives ($)",
        "key"           : "technology_capital_costs_after_incentives",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.lifecycle_capital_costs_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.lifecycle_capital_costs")
    },
    {
        "label"         : "O&M Costs ($)",
        "key"           : "om_costs",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.lifecycle_om_costs_after_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.lifecycle_om_costs_after_tax")
    },
    {
        "label"         : "Total Electric Costs ($)",
        "key"           : "total_electric_utility_costs",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.lifecycle_elecbill_after_tax_bau") + safe_get(df, "outputs.Financial.lifecycle_chp_standby_cost_after_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.lifecycle_elecbill_after_tax") + safe_get(df, "outputs.Financial.lifecycle_chp_standby_cost_after_tax")
    },
    {
        "label"         : "Total Fuel Costs ($)",
        "key"           : "total_fuel_costs",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.lifecycle_fuel_costs_after_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.lifecycle_fuel_costs_after_tax")
    },
    {
        "label"         : "Total Utility Costs ($)",
        "key"           : "total_utility_costs",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.lifecycle_elecbill_after_tax_bau") + safe_get(df, "outputs.Financial.lifecycle_chp_standby_cost_after_tax_bau") + safe_get(df, "outputs.Financial.lifecycle_fuel_costs_after_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.lifecycle_elecbill_after_tax") + safe_get(df, "outputs.Financial.lifecycle_chp_standby_cost_after_tax") + safe_get(df, "outputs.Financial.lifecycle_fuel_costs_after_tax")
    },
    {
        "label"         : "Total Hypothetical Emissions Costs (not included in LCC) ($)",
        "key"           : "total_emissions_costs",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.lifecycle_emissions_cost_climate_bau") + safe_get(df, "outputs.Financial.lifecycle_emissions_cost_health_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.lifecycle_emissions_cost_climate") + safe_get(df, "outputs.Financial.lifecycle_emissions_cost_health")
    },
    {
        "label"         : "Lifecycle Costs ($)",
        "key"           : "lcc",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.lcc_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.lcc")
    },
    # Calculated NPV as a % of BAU LCC (%)
    {
        "label"         : "NPV as a % of BAU LCC (%)",
        "key"           : "npv_bau_percent",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    #####################################################################################################
    ############################ Year 1 Electric Bill ###########################
    #####################################################################################################
    {
        "label"         : "Year 1 Electric Bill, Before Tax Unless Noted",
        "key"           : "year_1_electric_bill_separator",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Electric Grid Purchases (kWh/yr)",
        "key"           : "electric_grid_purchases",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricUtility.annual_energy_supplied_kwh_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricUtility.annual_energy_supplied_kwh")
    },
    {
        "label"         : "Energy Charges ($/yr)",
        "key"           : "electricity_energy_cost",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricTariff.year_one_energy_cost_before_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_energy_cost_before_tax")
    },
    {
        "label"         : "Demand Charges ($/yr)",
        "key"           : "electricity_demand_cost",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricTariff.year_one_demand_cost_before_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_demand_cost_before_tax")
    },
    {
        "label"         : "Fixed Charges ($/yr)",
        "key"           : "utility_fixed_cost",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricTariff.year_one_fixed_cost_before_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_fixed_cost_before_tax")
    },
    {
        "label"         : "Standby Charges For CHP ($/yr)",
        "key"           : "standby_charges_for_CHP",
        "bau_value"     : lambda df: safe_get(df, "outputs.CHP.year_one_standby_cost_before_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.year_one_standby_cost_before_tax")
    },      
    {
        "label"         : "Export Credits ($/yr)",
        "key"           : "export_credits",
        "bau_value"     : lambda df: -1 * safe_get(df, "outputs.ElectricTariff.year_one_export_benefit_before_tax_bau"),
        "scenario_value": lambda df: -1 * safe_get(df, "outputs.ElectricTariff.year_one_export_benefit_before_tax")
    },    
    {
        "label"         : "Purchased Electricity Cost ($/yr)",
        "key"           : "purchased_electricity_cost",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricTariff.year_one_bill_before_tax_bau") + safe_get(df, "outputs.Financial.year_one_chp_standby_cost_before_tax_bau") - safe_get(df, "outputs.ElectricTariff.year_one_export_benefit_before_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_bill_before_tax") + safe_get(df, "outputs.Financial.year_one_chp_standby_cost_before_tax") - safe_get(df, "outputs.ElectricTariff.year_one_export_benefit_before_tax")
    },
    {
        "label"         : "Purchased Electricity Cost, After Tax ($/yr)",
        "key"           : "purchased_electricity_cost",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricTariff.year_one_bill_after_tax_bau") + safe_get(df, "outputs.Financial.year_one_chp_standby_cost_after_tax_bau") - safe_get(df, "outputs.ElectricTariff.year_one_export_benefit_after_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_bill_after_tax") + safe_get(df, "outputs.Financial.year_one_chp_standby_cost_after_tax") - safe_get(df, "outputs.ElectricTariff.year_one_export_benefit_after_tax")
    },    
    {
        "label"         : "Electricity Cost Savings ($/yr)",
        "key"           : "electricity_cost_savings",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Electricity Cost Savings, After Tax ($/yr)",
        "key"           : "electricity_cost_savings_after_tax",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },    
    #####################################################################################################
    ############################ Year 1 Fuel Cost ###########################
    #####################################################################################################
    {
        "label"         : "Year 1 Fuel Cost, Before Tax Unless Noted",
        "key"           : "year_1_fuel_cost_separator",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Boiler Annual Fuel Consumption (MMBtu/yr)",
        "key"           : "boiler_annual_fuel_consumption",
        "bau_value"     : lambda df: safe_get(df, "outputs.ExistingBoiler.annual_fuel_consumption_mmbtu_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ExistingBoiler.annual_fuel_consumption_mmbtu")
    },
    {
        "label"         : "CHP Annual Fuel Consumption (MMBtu/yr)",
        "key"           : "chp_annual_fuel_consumption",
        "bau_value"     : lambda df: safe_get(df, "outputs.CHP.annual_fuel_consumption_mmbtu_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.annual_fuel_consumption_mmbtu")
    },
    {
        "label"         : "Backup Generator Annual Fuel Consumption (gal/yr)",
        "key"           : "backup_generator_annual_fuel_consumption",
        "bau_value"     : lambda df: safe_get(df, "outputs.Generator.annual_fuel_consumption_gal_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Generator.annual_fuel_consumption_gal")
    },
    {
        "label"         : "Boiler Fuel Cost ($/yr)",
        "key"           : "boiler_fuel_cost",
        "bau_value"     : lambda df: safe_get(df, "outputs.ExistingBoiler.year_one_fuel_cost_before_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ExistingBoiler.year_one_fuel_cost_before_tax")
    },
    {
        "label"         : "CHP Fuel Cost ($/yr)",
        "key"           : "chp_fuel_cost",
        "bau_value"     : lambda df          : safe_get(df, "outputs.CHP.year_one_fuel_cost_before_tax_bau"),
        "scenario_value": lambda df          : safe_get(df, "outputs.CHP.year_one_fuel_cost_before_tax")
    },
    {
        "label"         : "Backup Generator Fuel Cost ($/yr)",
        "key"           : "backup_generator_fuel_cost",
        "bau_value"     : lambda df: safe_get(df, "outputs.Generator.year_one_fuel_cost_before_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Generator.year_one_fuel_cost_before_tax")
    },
    {
        "label"         : "Fuel Cost ($/yr)",
        "key"           : "fuel_cost",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.year_one_fuel_cost_before_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.year_one_fuel_cost_before_tax")
    },
    {
        "label"         : "Fuel Cost, After Tax ($/yr)",
        "key"           : "fuel_cost",
        "bau_value"     : lambda df: safe_get(df, "outputs.Financial.year_one_fuel_cost_after_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.year_one_fuel_cost_after_tax")
    },
    {
        "label"         : "Fuel Cost Savings ($/yr)",
        "key"           : "fuel_cost_savings",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Fuel Cost Savings, After Tax ($/yr)",
        "key"           : "fuel_cost_savings_after_tax",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },    
    #####################################################################################################
    ############################ Renewable Energy & Emissions ###########################
    #####################################################################################################
    {
        "label"         : "Renewable Energy & Emissions",
        "key"           : "renewable_energy_emissions_separator",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Annual % On-Site Renewable Electricity (%)",
        "key"           : "annual_renewable_electricity",
        "bau_value"     : lambda df: safe_get(df, "outputs.Site.onsite_renewable_electricity_fraction_of_elec_load_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Site.onsite_renewable_electricity_fraction_of_elec_load")
    },
    {
        "label"         : "Annual % On-Site Renewable Energy (Elec+Fuel) (%)",
        "key"           : "annual_renewable_energy",
        "bau_value"     : lambda df: safe_get(df, "outputs.Site.onsite_renewable_energy_fraction_of_total_load_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Site.onsite_renewable_energy_fraction_of_total_load")
    },    
    {
        "label"         : "Annual CO2e Emissions (tonnes/yr)",
        "key"           : "annual_co2_emissions",
        "bau_value"     : lambda df: safe_get(df, "outputs.Site.annual_emissions_tonnes_CO2_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Site.annual_emissions_tonnes_CO2")
    },
    # Added emissions from electricity and fuels
    {
        "label"         : "Annual CO2e Emissions from Electricity (tonnes/yr)",
        "key"           : "annual_co2_emissions_electricity",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricUtility.annual_emissions_tonnes_CO2_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricUtility.annual_emissions_tonnes_CO2")
    },
    {
        "label"         : "Annual CO2e Emissions from Fuel (tonnes/yr)",
        "key"           : "annual_co2_emissions_fuel",
        "bau_value"     : lambda df: safe_get(df, "outputs.Site.annual_emissions_from_fuelburn_tonnes_CO2_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Site.annual_emissions_from_fuelburn_tonnes_CO2")
    },
    {
        "label"         : "Total CO2e Emissions (tonnes)",
        "key"           : "co2_emissions",
        "bau_value"     : lambda df: safe_get(df, "outputs.Site.lifecycle_emissions_tonnes_CO2_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Site.lifecycle_emissions_tonnes_CO2")
    },
    # CO2e savings (%) calculation
    {
        "label"         : "CO2e savings (%)",
        "key"           : "co2_savings_percentage",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    ####################################################################################################################################
    ##################### Playground - Consider Unaddressable Fuel Consumption in Emissions Reduction % Calculation ####################
    #####################################################################################################################################
    {
        "label": "Playground - Consider Unaddressable Fuel Consumption in Emissions Reduction % Calculation",
        "key": "playground_emissions_reduction_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Unaddressable Heating Fuel from REopt Input (MMBtu/yr)",
        "key": "unaddressable_heating_fuel_reopt",
        "bau_value": lambda df: safe_get(df, "outputs.HeatingLoad.annual_total_unaddressable_heating_load_mmbtu"),
        "scenario_value": lambda df: safe_get(df, "outputs.HeatingLoad.annual_total_unaddressable_heating_load_mmbtu")
    },
    {
        "label": "Unaddressable Heating Fuel CO2e Emissions from REopt Input (tonnes/yr)",
        "key": "unaddressable_heating_fuel_co2_emissions_reopt",
        "bau_value": lambda df: safe_get(df, "outputs.HeatingLoad.annual_emissions_from_unaddressable_heating_load_tonnes_CO2"),
        "scenario_value": lambda df: safe_get(df, "outputs.HeatingLoad.annual_emissions_from_unaddressable_heating_load_tonnes_CO2")
    },    
    {
        "label": "Additional Unaddressable Fuel Consumption (MMBtu/yr)",
        "key": "additional_unaddressable_fuel_input",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Additional Unaddressable Fuel Emissions Factor (lb-CO2e/MMBtu)",
        "key": "additional_unaddressable_fuel_emissions_factor_input",
        "bau_value": lambda df: safe_get(df, "inputs.ExistingBoiler.emissions_factor_lb_CO2_per_mmbtu"),
        "scenario_value": lambda df: safe_get(df, "inputs.ExistingBoiler.emissions_factor_lb_CO2_per_mmbtu")
    },
    {
        "label": "Additional Unaddressable Fuel CO2e Emissions (tonnes/yr)",
        "key": "additional_unaddressable_fuel_emissions",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },    
    {
        "label": "Total Unaddressable Fuel CO2e Emissions (tonnes/yr)",
        "key": "total_unaddressable_co2_emissions",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "CO2e Savings Including Unaddressable Fuel (%)",
        "key": "co2_savings_including_unaddressable",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },    
    ####################################################################################################################################
    ##################### Playground - Explore Effect of Additional Incentives or Costs, outside of REopt ##############################
    #####################################################################################################
    {
        "label": "Playground - Explore Effect of Additional Incentives or Costs, Outside of REopt",
        "key": "playground_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    }, 
    {
        "label": "Total Capital Cost Before Incentives ($)",
        "key": "total_capital_cost_before_incentives",
        "bau_value": lambda df: safe_get(df, "outputs.Financial.initial_capital_costs_bau") + safe_get(df, "outputs.Financial.replacements_present_cost_after_tax_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.initial_capital_costs") + safe_get(df, "outputs.Financial.replacements_present_cost_after_tax")
    },
    {
        "label": "Total Capital Cost After Incentives Without MACRS ($)",
        "key": "total_capital_cost_after_incentives_without_macrs",
        "bau_value": lambda df: safe_get(df, "outputs.Financial.capital_costs_after_non_discounted_incentives_without_macrs_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.capital_costs_after_non_discounted_incentives_without_macrs")
    },
    {
        "label": "Total Capital Cost After Non-Discounted Incentives ($)",
        "key": "total_capital_cost_after_non_discounted_incentives",
        "bau_value": lambda df: safe_get(df, "outputs.Financial.capital_costs_after_non_discounted_incentives_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Financial.capital_costs_after_non_discounted_incentives")
    },    
    {
        "label": "Tax Rate, For Reference (%)",
        "key": "tax_rate",
        "bau_value": lambda df: safe_get(df, "inputs.Financial.offtaker_tax_rate_fraction"),
        "scenario_value": lambda df: safe_get(df, "inputs.Financial.offtaker_tax_rate_fraction")
    },    
    {
        "label": "Total Year One Savings, After Tax ($/yr)",
        "key": "total_year_one_savings_after_tax",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Additional Upfront Incentive ($)",
        "key": "additional_upfront_incentive_input",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Additional Upfront Cost ($)",
        "key": "additional_upfront_cost_input",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Additional Yearly Cost Savings ($/yr)",
        "key": "additional_yearly_cost_savings_input",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Additional Yearly Cost ($/yr)",
        "key": "additional_yearly_cost_input",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Unaddressable Fuel Cost ($/MMBtu)",
        "key": "unaddressable_fuel_cost_input",
        "bau_value": lambda df: safe_get(df, "inputs.ExistingBoiler.fuel_cost_per_mmbtu") / 8760,
        "scenario_value": lambda df: safe_get(df, "inputs.ExistingBoiler.fuel_cost_per_mmbtu") / 8760
    },
    {
        "label": "Unaddressable Fuel Yearly Cost ($/yr)",
        "key": "unaddressable_fuel_yearly_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },    
    {
        "label": "Modified Total Year One Savings, After Tax ($/yr)",
        "key": "modified_total_year_one_savings_after_tax",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },    
    {
        "label": "Modified Total Capital Cost ($)",
        "key": "modified_net_upfront_capital_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Modified Simple Payback Period Without Incentives (yrs)",
        "key": "modified_simple_payback_period_without_incentives",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },    
    {
        "label": "Modified Simple Payback Period (yrs)",
        "key": "modified_simple_payback_period",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    #####################################################################################################
    ############################# Annual Electric Production #############################
    #####################################################################################################
    {
        "label"         : "Annual Electric Production",
        "key"           : "annual_electric_production_separator",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: "",
        "comments"      : "Split into Electric, Heating, and Cooling Sections"
    },
    {
        "label"         : "Grid Serving Load (kWh/yr)",
        "key"           : "grid_serving_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricUtility.electric_to_load_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricUtility.electric_to_load_series_kw")
    },
    {
        "label"         : "Grid Charging Battery (kWh/yr)",
        "key"           : "grid_charging_battery",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricUtility.electric_to_storage_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricUtility.electric_to_storage_series_kw")
    },
    {
        "label"         : "PV Serving Load (kWh/yr)",
        "key"           : "pv_serving_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.PV.electric_to_load_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.PV.electric_to_load_series_kw")
    },
    {
        "label"         : "PV Charging Battery (kWh/yr)",
        "key"           : "pv_charging_battery",
        "bau_value"     : lambda df: safe_get(df, "outputs.PV.electric_to_storage_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.PV.electric_to_storage_series_kw")
    },
    {
        "label"         : "PV Exported to Grid (kWh/yr)",
        "key"           : "pv_exported_to_grid",
        "bau_value"     : lambda df: safe_get(df, "outputs.PV.electric_to_grid_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.PV.electric_to_grid_series_kw")
    },
    {
        "label"         : "PV Curtailment (kWh/yr)",
        "key"           : "pv_curtailment",
        "bau_value"     : lambda df: safe_get(df, "outputs.PV.electric_curtailed_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.PV.electric_curtailed_series_kw")
    },
    {
        "label"         : "PV Total Electricity Produced (kWh/yr)",
        "key"           : "pv_total_electricity_produced",
        "bau_value"     : lambda df: safe_get(df, "outputs.PV.year_one_energy_produced_kwh_bau"),
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Wind Serving Load (kWh/yr)",
        "key"           : "wind_serving_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.Wind.electric_to_load_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Wind.electric_to_load_series_kw")
    },
    {
        "label"         : "Wind Charging Battery (kWh/yr)",
        "key"           : "wind_charging_battery",
        "bau_value"     : lambda df: safe_get(df, "outputs.Wind.electric_to_storage_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Wind.electric_to_storage_series_kw")
    },
    {
        "label"         : "Wind Exported to Grid (kWh/yr)",
        "key"           : "wind_exported_to_grid",
        "bau_value"     : lambda df: safe_get(df, "outputs.Wind.electric_to_grid_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Wind.electric_to_grid_series_kw")
    },
    {
        "label"         : "Wind Curtailment (kWh/yr)",
        "key"           : "wind_curtailment",
        "bau_value"     : lambda df: safe_get(df, "outputs.Wind.electric_curtailed_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Wind.electric_curtailed_series_kw")
    },
    {
        "label"         : "Wind Total Electricity Produced (kWh/yr)",
        "key"           : "wind_total_electricity_produced",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Battery Serving Load (kWh/yr)",
        "key"           : "battery_serving_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricStorage.storage_to_load_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricStorage.storage_to_load_series_kw")
    },
    {
        "label"         : "Generator Serving Load (kWh/yr)",
        "key"           : "generator_serving_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.Generator.electric_to_load_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Generator.electric_to_load_series_kw")
    },
    {
        "label"         : "Generator Charging Battery (kWh/yr)",
        "key"           : "generator_charging_battery",
        "bau_value"     : lambda df: safe_get(df, "outputs.Generator.electric_to_storage_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Generator.electric_to_storage_series_kw")
    },
    {
        "label"         : "Generator Exported to Grid (kWh/yr)",
        "key"           : "generator_exported_to_grid",
        "bau_value"     : lambda df: safe_get(df, "outputs.Generator.electric_to_grid_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.Generator.electric_to_grid_series_kw")
    },
    {
        "label"         : "Generator Total Electricity Produced (kWh/yr)",
        "key"           : "generator_total_electricity_produced",
        "bau_value"     : lambda df: safe_get(df, "outputs.Generator.annual_fuel_consumption_gal_bau") * safe_get(df, "inputs.Generator.fuel_higher_heating_value_kwh_per_gal") * safe_get(df, "inputs.Generator.electric_efficiency_full_load"),
        "scenario_value": lambda df: safe_get(df, "outputs.Generator.annual_energy_produced_kwh")
    },
    {
        "label"         : "CHP Serving Load (kWh/yr)",
        "key"           : "chp_serving_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.CHP.electric_to_load_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.electric_to_load_series_kw")
    },
    {
        "label"         : "CHP Charging Battery (kWh/yr)",
        "key"           : "chp_charging_battery",
        "bau_value"     : lambda df: safe_get(df, "outputs.CHP.electric_to_storage_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.electric_to_storage_series_kw")
    },
    {
        "label"         : "CHP Exported to Grid (kWh/yr)",
        "key"           : "chp_exported_to_grid",
        "bau_value"     : lambda df: safe_get(df, "outputs.CHP.electric_to_grid_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.electric_to_grid_series_kw")
    },
    {
        "label"         : "CHP Total Electricity Produced (kWh/yr)",
        "key"           : "chp_total_electricity_produced",
        "bau_value"     : lambda df: safe_get(df, "outputs.CHP.annual_electric_production_kwh_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.annual_electric_production_kwh")
    },
    {
        "label"         : "Steam Turbine Serving Load (kWh/yr)",
        "key"           : "steam_turbine_serving_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.SteamTurbine.electric_to_load_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.SteamTurbine.electric_to_load_series_kw")
    },
    {
        "label"         : "Steam Turbine Charging Battery (kWh/yr)",
        "key"           : "steam_turbine_charging_battery",
        "bau_value"     : lambda df: safe_get(df, "outputs.SteamTurbine.electric_to_storage_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.SteamTurbine.electric_to_storage_series_kw")
    },
    {
        "label"         : "Steam Turbine Exported to Grid (kWh/yr)",
        "key"           : "steam_turbine_exported_to_grid",
        "bau_value"     : lambda df: safe_get(df, "outputs.SteamTurbine.electric_to_grid_series_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.SteamTurbine.electric_to_grid_series_kw")
    },
    {
        "label"         : "Steam Turbine Total Electricity Produced (kWh/yr)",
        "key"           : "steam_turbine_total_electricity_produced",
        "bau_value"     : lambda df: safe_get(df, "outputs.SteamTurbine.annual_electric_production_kwh_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.SteamTurbine.annual_electric_production_kwh")
    },
    #####################################################################################################
    ##############################  Annual Heating Thermal Production #############################
    ##################################################################################################### 
    {
        "label"         : "Annual Heating Thermal Production",
        "key"           : "annual_heating_thermal_production_separator",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Existing Heating System Serving Thermal Load (MMBtu/yr)",
        "key"           : "existing_heating_system_serving_thermal_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.ExistingBoiler.annual_thermal_production_mmbtu_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ExistingBoiler.thermal_to_load_series_mmbtu_per_hour")
    },
    {
        "label"         : "Existing Heating System Thermal to Steam Turbine (MMBtu/yr)",
        "key"           : "existing_heating_system_thermal_to_steam_turbine",
        "bau_value"     : lambda df: safe_get(df, "outputs.ExistingBoiler.thermal_to_steamturbine_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ExistingBoiler.thermal_to_steamturbine_series_mmbtu_per_hour")
    },
    {
        "label"         : "Existing Heating System Thermal to Absorption Chiller (MMBtu/yr)",
        "key"           : "existing_heating_system_thermal_to_absorption_chiller",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ExistingBoiler.thermal_to_absorption_chiller_series_mmbtu_per_hour")
    },
    {
        "label"         : "Existing Heating System Charging Hot Water Storage (MMBtu/yr)",
        "key"           : "existing_heating_system_charging_hot_water_storage",
        "bau_value"     : lambda df: safe_get(df, "outputs.ExistingBoiler.thermal_to_storage_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ExistingBoiler.thermal_to_storage_series_mmbtu_per_hour")
    },
    {
        "label"         : "Existing Heating System Total Thermal Produced (MMBtu/yr)",
        "key"           : "existing_heating_system_total_thermal_produced",
        "bau_value"     : lambda df                                               : safe_get(df, "outputs.ExistingBoiler.annual_thermal_production_mmbtu_bau"),
        "scenario_value": lambda df                                               : safe_get(df, "outputs.ExistingBoiler.annual_thermal_production_mmbtu")
    },
    {
        "label"         : "CHP Serving Thermal Load (MMBtu/yr)",
        "key"           : "chp_serving_thermal_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.CHP.thermal_to_load_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.thermal_to_load_series_mmbtu_per_hour")
    },
    {
        "label"         : "CHP Charging Hot Water Storage (MMBtu/yr)",
        "key"           : "chp_charging_hot_water_storage",
        "bau_value"     : lambda df: safe_get(df, "outputs.CHP.thermal_to_storage_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.thermal_to_storage_series_mmbtu_per_hour")
    },
    {
        "label"         : "CHP Thermal to Steam Turbine (MMBtu/yr)",
        "key"           : "chp_thermal_to_steam_turbine",
        "bau_value"     : lambda df: safe_get(df, "outputs.CHP.thermal_to_steamturbine_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.thermal_to_steamturbine_series_mmbtu_per_hour")
    },
    {
        "label"         : "CHP Thermal to Absorption Chiller (MMBtu/yr)",
        "key"           : "chp_thermal_to_absorption_chiller",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.thermal_to_absorption_chiller_series_mmbtu_per_hour")
    },
    {
        "label"         : "CHP Thermal Vented (MMBtu/yr)",
        "key"           : "chp_thermal_vented",
        "bau_value"     : lambda df: safe_get(df, "outputs.CHP.thermal_curtailed_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.thermal_curtailed_series_mmbtu_per_hour")
    },
    {
        "label"         : "CHP Total Thermal Produced (MMBtu/yr)",
        "key"           : "chp_total_thermal_produced",
        "bau_value"     : lambda df: safe_get(df, "outputs.CHP.annual_thermal_production_mmbtu_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CHP.annual_thermal_production_mmbtu")
    },
    {
        "label"         : "Steam Turbine Serving Thermal Load (MMBtu/yr)",
        "key"           : "steam_turbine_serving_thermal_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.SteamTurbine.thermal_to_load_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.SteamTurbine.thermal_to_load_series_mmbtu_per_hour")
    },
    {
        "label"         : "Steam Turbine Charging High Temp Thermal Storage (MMBtu/yr)",
        "key"           : "steam_turbine_charging_high_temp_thermal_storage",
        "bau_value"     : lambda df: safe_get(df, "outputs.SteamTurbine.thermal_to_high_temp_thermal_storage_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.SteamTurbine.thermal_to_high_temp_thermal_storage_series_mmbtu_per_hour")
    },
    {
        "label"         : "Steam Turbine Charging Hot Water Storage (MMBtu/yr)",
        "key"           : "steam_turbine_charging_hot_water_storage",
        "bau_value"     : lambda df: safe_get(df, "outputs.SteamTurbine.thermal_to_storage_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.SteamTurbine.thermal_to_storage_series_mmbtu_per_hour")
    },
    {
        "label"         : "Steam Turbine Total Thermal Produced (MMBtu/yr)",
        "key"           : "steam_turbine_total_thermal_produced",
        "bau_value"     : lambda df                                     : safe_get(df, "outputs.SteamTurbine.annual_thermal_production_mmbtu_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.SteamTurbine.annual_thermal_production_mmbtu")
    },
    {
        "label"         : "Steam Turbine Thermal to Absorption Chiller (MMBtu/yr)",
        "key"           : "steam_turbine_thermal_to_absorption_chiller",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.SteamTurbine.thermal_to_absorption_chiller_series_mmbtu_per_hour")
    },
    {
        "label"         : "GHP Reduction of Thermal Load (MMBtu/yr)",
        "key"           : "ghp_reduction_of_thermal_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.GHP.space_heating_thermal_load_reduction_with_ghp_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.GHP.space_heating_thermal_load_reduction_with_ghp_mmbtu_per_hour")
    },
    {
        "label"         : "GHP Serving Thermal Load (MMBtu/yr)",
        "key"           : "ghp_serving_thermal_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.GHP.thermal_to_space_heating_load_series_mmbtu_per_hour_bau") + safe_get(df, "outputs.GHP.thermal_to_dhw_load_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.GHP.thermal_to_space_heating_load_series_mmbtu_per_hour") + safe_get(df, "outputs.GHP.thermal_to_dhw_load_series_mmbtu_per_hour")
    },
    {
        "label"         : "ASHP Serving Thermal Load (MMBtu/yr)",
        "key"           : "ashp_serving_thermal_load",
        "bau_value"     : lambda df                          : safe_get(df, "outputs.ASHPSpaceHeater.thermal_to_load_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df                          : safe_get(df, "outputs.ASHPSpaceHeater.thermal_to_load_series_mmbtu_per_hour")
    },
    {
        "label"         : "ASHP Charging Hot Water Storage (MMBtu/yr)",
        "key"           : "ashp_charging_hot_water_storage",
        "bau_value"     : lambda df: safe_get(df, "outputs.ASHPSpaceHeater.thermal_to_storage_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ASHPSpaceHeater.thermal_to_storage_series_mmbtu_per_hour")
    },
    {
        "label"         : "ASHP Water Heater Serving Thermal Load (MMBtu/yr)",
        "key"           : "ashp_water_heater_serving_thermal_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.ASHPWaterHeater.thermal_to_load_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ASHPWaterHeater.thermal_to_load_series_mmbtu_per_hour")
    },
    {
        "label"         : "ASHP Water Heater Charging Hot Water Storage (MMBtu/yr)",
        "key"           : "ashp_water_heater_charging_hot_water_storage",
        "bau_value"     : lambda df: safe_get(df, "outputs.ASHPWaterHeater.thermal_to_storage_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ASHPWaterHeater.thermal_to_storage_series_mmbtu_per_hour")
    },
    {
        "label"         : "CST Charging High Temp Thermal Storage (MMBtu/yr)",
        "key"           : "cst_charging_high_temp_thermal_storage",
        "bau_value"     : lambda df: safe_get(df, "outputs.CST.thermal_to_high_temp_thermal_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CST.thermal_to_high_temp_thermal_series_mmbtu_per_hour")
    },
    {
        "label"         : "CST Charging Hot Water Storage (MMBtu/yr)",
        "key"           : "cst_charging_hot_water_storage",
        "bau_value"     : lambda df: safe_get(df, "outputs.CST.thermal_to_storage_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CST.thermal_to_storage_series_mmbtu_per_hour")
    },
    {
        "label"         : "CST Thermal to Steam Turbine (MMBtu/yr)",
        "key"           : "cst_thermal_to_steam_turbine",
        "bau_value"     : lambda df: safe_get(df, "outputs.CST.thermal_to_steamturbine_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CST.thermal_to_steamturbine_series_mmbtu_per_hour")
    },
    {
        "label"         : "CST Thermal to Absorption Chiller (MMBtu/yr)",
        "key"           : "cst_thermal_to_absorption_chiller",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.CST.thermal_to_absorption_chiller_series_mmbtu_per_hour")
    },
    {
        "label"         : "CST Thermal Vented (MMBtu/yr)",
        "key"           : "cst_thermal_vented",
        "bau_value"     : lambda df: safe_get(df, "outputs.CST.thermal_curtailed_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CST.thermal_curtailed_series_mmbtu_per_hour")
    },
    {
        "label"         : "CST Total Thermal Produced (MMBtu/yr)",
        "key"           : "cst_total_thermal_produced",
        "bau_value"     : lambda df: safe_get(df, "outputs.CST.annual_thermal_production_mmbtu_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.CST.annual_thermal_production_mmbtu")
    },
    {
        "label"         : "High Temp Thermal Storage Serving Thermal Load (MMBtu/yr)",
        "key"           : "high_temp_thermal_storage_serving_thermal_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.HighTempThermalStorage.storage_to_load_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.HighTempThermalStorage.storage_to_load_series_mmbtu_per_hour")
    },
    {
        "label"         : "High Temp Thermal Storage to Absorption Chiller (MMBtu/yr)",
        "key"           : "high_temp_thermal_storage_to_absorption_chiller",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.HighTempThermalStorage.storage_to_absorption_chiller_series_mmbtu_per_hour")
    },
    {
        "label"         : "Hot Water Storage Serving Thermal Load (MMBtu/yr)",
        "key"           : "hot_water_storage_serving_thermal_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.HotThermalStorage.storage_to_load_series_mmbtu_per_hour_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.HotThermalStorage.storage_to_load_series_mmbtu_per_hour")
    },
    {
        "label"         : "Hot Water Storage to Absorption Chiller (MMBtu/yr)",
        "key"           : "hot_water_storage_to_absorption_chiller",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.HotThermalStorage.storage_to_absorption_chiller_series_mmbtu_per_hour")
    },
    #####################################################################################################
    ############################ Annual Cooling Thermal Production ############################
    #####################################################################################################

    {
        "label"         : "Annual Cooling Thermal Production",
        "key"           : "annual_cooling_thermal_production_separator",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Existing Cooling Plant Serving Thermal Load (ton-hr/yr)",
        "key"           : "existing_cooling_plant_serving_thermal_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.ExistingChiller.thermal_to_load_series_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ExistingChiller.thermal_to_load_series_ton")
    },
    {
        "label"         : "Existing Cooling Plant Charging Chilled Water Storage (ton-hr/yr)",
        "key"           : "existing_cooling_plant_charging_chilled_water_storage",
        "bau_value"     : lambda df: safe_get(df, "outputs.ExistingChiller.thermal_to_storage_series_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ExistingChiller.thermal_to_storage_series_ton")
    },
    {
        "label"         : "GHP Reduction of Thermal Load (ton-hr/yr)",
        "key"           : "ghp_reduction_of_thermal_load_cooling",
        "bau_value"     : lambda df: safe_get(df, "outputs.GHP.cooling_thermal_load_reduction_with_ghp_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.GHP.cooling_thermal_load_reduction_with_ghp_ton")
    },
    {
        "label"         : "GHP Serving Thermal Load (ton-hr/yr)",
        "key"           : "ghp_serving_thermal_load_cooling",
        "bau_value"     : lambda df: safe_get(df, "outputs.GHP.thermal_to_load_series_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.GHP.thermal_to_load_series_ton")
    },
    {
        "label"         : "ASHP Serving Thermal Load (ton-hr/yr)",
        "key"           : "ashp_serving_thermal_load_cooling",
        "bau_value"     : lambda df: safe_get(df, "outputs.ASHPSpaceHeater.thermal_to_load_series_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ASHPSpaceHeater.thermal_to_load_series_ton")
    },
    {
        "label"         : "ASHP Charging Chilled Water Storage (ton-hr/yr)",
        "key"           : "ashp_charging_chilled_water_storage",
        "bau_value"     : lambda df: safe_get(df, "outputs.ASHPSpaceHeater.thermal_to_storage_series_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ASHPSpaceHeater.thermal_to_storage_series_ton")
    },
    {
        "label"         : "Absorption Chiller Serving Thermal Load (ton-hr/yr)",
        "key"           : "absorption_chiller_serving_thermal_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.AbsorptionChiller.thermal_to_load_series_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.AbsorptionChiller.thermal_to_load_series_ton")
    },
    {
        "label"         : "Absorption Chiller Charging Chilled Water Storage (ton-hr/yr)",
        "key"           : "absorption_chiller_charging_chilled_water_storage",
        "bau_value"     : lambda df: safe_get(df, "outputs.AbsorptionChiller.thermal_to_storage_series_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.AbsorptionChiller.thermal_to_storage_series_ton")
    },
    {
        "label"         : "Chilled Water Storage Serving Thermal Load (ton-hr/yr)",
        "key"           : "chilled_water_storage_serving_thermal_load",
        "bau_value"     : lambda df: safe_get(df, "outputs.ColdThermalStorage.storage_to_load_series_ton_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ColdThermalStorage.storage_to_load_series_ton")
    },
    #####################################################################################################
    ############################ Other Metrics ############################
    #####################################################################################################

    {
        "label"         : "Other Metrics",
        "key"           : "other_metrics_separator",
        "bau_value"     : lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label"         : "Peak Grid Demand (kW)",
        "key"           : "peak_grid_demand_max",
        "bau_value"     : lambda df: safe_get(df, "outputs.ElectricUtility.peak_grid_demand_kw_bau"),
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricUtility.peak_grid_demand_kw")
    },
]

'''
 2. Defining BAU Columns:
------------------------
- If your calculation involves BAU (Business As Usual) columns, ensure that the relevant BAU columns are included in the `bau_cells_config` dictionary. Each key in this dictionary represents a BAU variable used in calculations, and the value is the corresponding table label.

- Example `bau_cells_config` for BAU references:
  bau_cells_config = {
      "grid_value": "Grid Purchased Electricity (kWh)",
      "elec_cost_value": "Purchased Electricity Cost ($)",
  }
  
- When defining calculations that use BAU columns, reference the BAU values using the `bau` dictionary. For example, to calculate the optimal reduction in grid electricity purchases compared to BAU:
  "formula": lambda col, bau, headers: f'=({bau["grid_value"]} - {col}{headers["Grid Purchased Electricity (kWh)"] + 2}) / {bau["grid_value"]}'

- Note: the bau cell has to be associated with a variable name in the custom table
- Note: It is safe to define bau cells that are not being used. If they are not associated with an entry in the custom table, they will be safely ignored
'''

# Define bau_cells configuration for calculations that reference bau cells, call these bau values within calculations
bau_cells_config = {
    "grid_value"                : "Grid Purchased Electricity (kWh)",
    "elec_cost_value"           : "Purchased Electricity Cost ($/yr)",
    "elec_cost_after_tax"       : "Purchased Electricity Cost, After Tax ($/yr)",
    "ng_reduction_value"        : "Total Fuel (MMBtu)",
    "total_elec_costs"          : "Total Electric Costs ($)",
    "fuel_costs"                : "Fuel Cost ($/yr)",
    "fuel_costs_after_tax"      : "Fuel Cost, After Tax ($/yr)",
    "om_costs_after_tax"        : "Year 1 O&M Cost, After Tax ($/yr)",
    "total_co2_emission_value"  : "Total CO2e Emissions (tonnes)",
    "placeholder1_value"        : "Placeholder1",
    "lcc_value"                 : "Lifecycle Costs ($)",
    "annual_co2_emissions_value": "Annual CO2e Emissions (tonnes/yr)"
}

'''
3. Defining Calculations:
-------------------------
- Each calculation should be defined using a dictionary with the following structure:
  {
      "name": <calculation_name>,    # The name of the calculation (matches the label in the table)
      "formula": <lambda_function>   # A lambda function that calculates the desired value
  }

- The lambda function receives the following parameters:
  - `col`: The column letter for the scenario data in Excel.
  - `bau`: A dictionary of BAU cell references (if applicable).
  - `headers`: A dictionary containing the row indices for relevant table headers.

  Example Calculation:
  {
      "name": "Net Purchased Electricity Reduction (%)",
      "formula": lambda col, bau, headers: f'=({bau["grid_value"]} - {col}{headers["Grid Purchased Electricity (kWh)"] + 2}) / {bau["grid_value"]}'
  }
  - Note: The calculation name has to be the same as a variable in the custom table
  - Note: It is safe to define calculations that are not being used, if they are not associated with an entry in the custom table, it will be ignored
  '''
  
# Calculation logic
calculations_config = [
    {
        "name": "Present Value of Incentives ($)",
        "formula": lambda col, bau, headers: f'={col}{headers["Gross Upfront Capital Costs, Before Incentives ($)"] + 2} - {col}{headers["Net Upfront Capital Cost, After Incentives ($)"] + 2}'    
    },
    {
        "name": "Electricity Cost Savings ($/yr)",
        "formula": lambda col, bau, headers: f'={bau["elec_cost_value"]}-{col}{headers["Purchased Electricity Cost ($/yr)"] + 2}'
    },
    {
        "name": "Electricity Cost Savings, After Tax ($/yr)",
        "formula": lambda col, bau, headers: f'={bau["elec_cost_after_tax"]}-{col}{headers["Purchased Electricity Cost, After Tax ($/yr)"] + 2}'
    },    
    {
        "name": "NPV as a % of BAU LCC (%)",
        "formula": lambda col, bau, headers: f'=({col}{headers["Net Present Value ($)"] + 2}/{bau["lcc_value"]})'
    },
    {
        "name": "Fuel Cost Savings ($/yr)",
        "formula": lambda col, bau, headers: f'={bau["fuel_costs"]}-{col}{headers["Fuel Cost ($/yr)"] + 2}'
    },
    {
        "name": "Fuel Cost Savings, After Tax ($/yr)",
        "formula": lambda col, bau, headers: f'={bau["fuel_costs_after_tax"]}-{col}{headers["Fuel Cost, After Tax ($/yr)"] + 2}'
    },
    {
        "name": "Unaddressable Fuel Yearly Cost ($/yr)",
        "formula": lambda col, bau, headers: f'={col}{headers["Unaddressable Fuel Cost ($/MMBtu)"] + 2} * ({col}{headers["Unaddressable Heating Fuel from REopt Input (MMBtu/yr)"] + 2} + {col}{headers["Additional Unaddressable Fuel Consumption (MMBtu/yr)"] + 2})'
    },
    {
        "name": "Electricity Cost Savings, After Tax ($/yr)",
        "formula": lambda col, bau, headers: f'={bau["elec_cost_after_tax"]}-{col}{headers["Purchased Electricity Cost, After Tax ($/yr)"] + 2}'
    }, 
    {
        "name": "Total Year One Savings, After Tax ($/yr)",
        "formula": lambda col, bau, headers: f'=({col}{headers["Electricity Cost Savings, After Tax ($/yr)"] + 2}+{col}{headers["Fuel Cost Savings, After Tax ($/yr)"] + 2}+({bau["om_costs_after_tax"]}-{col}{headers["Year 1 O&M Cost, After Tax ($/yr)"] + 2}))'
    },
    {
        "name": "Modified Total Year One Savings, After Tax ($/yr)",
        "formula": lambda col, bau, headers: f'={col}{headers["Total Year One Savings, After Tax ($/yr)"] + 2}+{col}{headers["Additional Yearly Cost Savings ($/yr)"] + 2}-{col}{headers["Additional Yearly Cost ($/yr)"] + 2}'
    },
    {
        "name": "Modified Total Capital Cost ($)",
        "formula": lambda col, bau, headers: f'={col}{headers["Total Capital Cost After Non-Discounted Incentives ($)"] + 2}-{col}{headers["Additional Upfront Incentive ($)"] + 2}+{col}{headers["Additional Upfront Cost ($)"] + 2}'        
    },
    {
        "name": "Modified Simple Payback Period Without Incentives (yrs)",
        "formula": lambda col, bau, headers: f'={col}{headers["Total Capital Cost Before Incentives ($)"] + 2}/{col}{headers["Modified Total Year One Savings, After Tax ($/yr)"] + 2}'
    },    
    {
        "name": "Modified Simple Payback Period (yrs)",
        "formula": lambda col, bau, headers: f'={col}{headers["Modified Total Capital Cost ($)"] + 2}/{col}{headers["Modified Total Year One Savings, After Tax ($/yr)"] + 2}'
    },
    {
        "name": "Additional Unaddressable Fuel CO2e Emissions (tonnes/yr)",
        "formula": lambda col, bau, headers: f'={col}{headers["Additional Unaddressable Fuel Consumption (MMBtu/yr)"] + 2}*{col}{headers["Additional Unaddressable Fuel Emissions Factor (lb-CO2e/MMBtu)"] + 2}/2204.62'
    },    
    {
        "name": "Total Unaddressable Fuel CO2e Emissions (tonnes/yr)",
        "formula": lambda col, bau, headers: f'={col}{headers["Unaddressable Heating Fuel CO2e Emissions from REopt Input (tonnes/yr)"] + 2}+{col}{headers["Additional Unaddressable Fuel CO2e Emissions (tonnes/yr)"] + 2}'
    },
    {
        "name": "CO2e Savings Including Unaddressable Fuel (%)",
        "formula": lambda col, bau, headers: f'=({bau["annual_co2_emissions_value"]}-{col}{headers["Annual CO2e Emissions (tonnes/yr)"] + 2})/({bau["annual_co2_emissions_value"]}+{col}{headers["Total Unaddressable Fuel CO2e Emissions (tonnes/yr)"] + 2})'    
    },
    {
        "name": "PV Total Electricity Produced (kWh/yr)",
        "formula": lambda col, bau, headers: f'={col}{headers["PV Serving Load (kWh/yr)"] + 2}+{col}{headers["PV Charging Battery (kWh/yr)"] + 2}+{col}{headers["PV Exported to Grid (kWh/yr)"] + 2}'
    },
    {
        "name": "Wind Total Electricity Produced (kWh/yr)",
        "formula": lambda col, bau, headers: f'={col}{headers["Wind Serving Load (kWh/yr)"] + 2}+{col}{headers["Wind Charging Battery (kWh/yr)"] + 2}+{col}{headers["Wind Exported to Grid (kWh/yr)"] + 2}'
    },    
    # These below don't seem to be used currently
    {
        "name": "Total Site Electricity Use (kWh)",
        "formula": lambda col, bau, headers: (
            f'={col}{headers["PV Serving Load (kWh)"] + 2}+'
            f'{col}{headers["Wind Serving Load (kWh)"] + 2}+'
            f'{col}{headers["CHP Serving Load (kWh)"] + 2}+'
            f'{col}{headers["Battery Serving Load (kWh)"] + 2}+'
            f'{col}{headers["Backup Generator Serving Load (kWh)"] + 2}+'
            f'{col}{headers["Steam Turbine Serving Load (kWh)"] + 2}+'
            f'{col}{headers["Grid Purchased Electricity (kWh)"] + 2}'
        )
    },
    {
        "name": "Net Purchased Electricity Reduction (%)",
        "formula": lambda col, bau, headers: f'=({bau["grid_value"]}-{col}{headers["Grid Purchased Electricity (kWh)"] + 2})/{bau["grid_value"]}'
    },
    {
        "name": "Net Electricity Cost ($)",
        "formula": lambda col, bau, headers: f'={col}{headers["Purchased Electricity Cost ($)"] + 2}-{col}{headers["Electricity Export Benefit ($)"] + 2}'
    },
    {
        "name": "Total Fuel (MMBtu)",
        "formula": lambda col, bau, headers: f'={col}{headers["Boiler Fuel (MMBtu)"] + 2}+{col}{headers["CHP Fuel (MMBtu)"] + 2}'
    },
    {
        "name": "Natural Gas Reduction (%)",
        "formula": lambda col, bau, headers: f'=({bau["ng_reduction_value"]}-{col}{headers["Total Fuel (MMBtu)"] + 2})/{bau["ng_reduction_value"]}'
    },
    {
        "name": "Total Thermal Production (MMBtu)",
        "formula": lambda col, bau, headers: f'={col}{headers["Boiler Thermal Production (MMBtu)"] + 2}+{col}{headers["CHP Thermal Production (MMBtu)"] + 2}'
    },
    {
        "name": "Annual Cost Savings ($)",
        "formula": lambda col, bau, headers: f'={bau["elec_cost_value"]}+-{col}{headers["Purchased Electricity Cost ($)"] + 2}'
    },
    {
        "name": "Simple Payback (yrs)",
        "formula": lambda col, bau, headers: f'={col}{headers["Net Capital Cost ($)"] + 2}/{col}{headers["Annual Cost Savings ($)"] + 2}'
    },
    {
        "name": "CO2e savings (%)",
        "formula": lambda col, bau, headers: f'=({bau["total_co2_emission_value"]}-{col}{headers["Total CO2e Emissions (tonnes)"] + 2})/{bau["total_co2_emission_value"]}'
    },
    #Example Calculations
    # Calculation Without Reference to bau_cells
    {
        "name": "Placeholder Calculation Without BAU Reference",
        "formula": lambda col, bau, headers: f'={col}{headers["Placeholder1"] + 2}+{col}{headers["Placeholder2"] + 2}'
        # This formula adds Placeholder1 and Placeholder2 values from the scenario.
    },

    # Calculation With Reference to bau_cells
    {
        "name": "Placeholder Calculation With BAU Reference",
        "formula": lambda col, bau, headers: f'=({bau["placeholder1_value"]}-{col}{headers["Placeholder2"] + 2})/{bau["placeholder1_value"]}'
        # This formula calculates the percentage change of Placeholder2 using Placeholder1's BAU value as the reference.
    },

    # custom_table_rates Specific Calculations
    {
        "name": "Change in Year 1 Total Charges ($)",
        "formula": lambda col, bau, headers: f'={col}{headers["Year 1 Total Bill Charges ($)"] + 2}-{"B"}{headers["Year 1 Total Bill Charges ($)"] + 2}'
        # This formula calculates the percentage change of scenario 2 vs. scenario 1.
    },
    {
        "name": "Year 1 Fixed Charges Percent Change (%)",
        "formula": lambda col, bau, headers: f'=({col}{headers["Year 1 Annual Fixed Charges ($)"] + 2}-{"B"}{headers["Year 1 Annual Fixed Charges ($)"] + 2})/{"B"}{headers["Year 1 Annual Fixed Charges ($)"] + 2}'
        # This formula calculates the percentage change of scenario 2 vs. scenario 1.
    },
    {
        "name": "Year 1 Energy Charges Percent Change (%)",
        "formula": lambda col, bau, headers: f'=({col}{headers["Year 1 Annual Energy Charges ($)"] + 2}-{"B"}{headers["Year 1 Annual Energy Charges ($)"] + 2})/{"B"}{headers["Year 1 Annual Energy Charges ($)"] + 2}'
        # This formula calculates the percentage change of scenario 2 vs. scenario 1.
    },
    {
        "name": "Year 1 Demand Charges Percent Change (%)",
        "formula": lambda col, bau, headers: f'=({col}{headers["Year 1 Annual Demand Charges ($)"] + 2}-{"B"}{headers["Year 1 Annual Demand Charges ($)"] + 2})/{"B"}{headers["Year 1 Annual Demand Charges ($)"] + 2}'
        # This formula calculates the percentage change of scenario 2 vs. scenario 1.
    },
    {
        "name": "Year 1 Total Bill Charges Percent Change (%)",
        "formula": lambda col, bau, headers: f'=({col}{headers["Year 1 Annual Total Bill Charges ($)"] + 2}-{"B"}{headers["Year 1 Annual Total Bill Charges ($)"] + 2})/{"B"}{headers["Year 1 Annual Total Bill Charges ($)"] + 2}'
        # This formula calculates the percentage change of scenario 2 vs. scenario 1.
    },
    {
        "name": "Year 1 Fixed Charges Percent of Total Bill (%)",
        "formula": lambda col, bau, headers: f'=({col}{headers["Year 1 Annual Fixed Charges ($)"] + 2})/{col}{headers["Year 1 Annual Total Bill Charges ($)"] + 2}'
        # This formula calculates the percentage change of scenario 2 vs. scenario 1.
    },
    {
        "name": "Year 1 Energy Charges Percent of Total Bill (%)",
        "formula": lambda col, bau, headers: f'=({col}{headers["Year 1 Annual Energy Charges ($)"] + 2})/{col}{headers["Year 1 Annual Total Bill Charges ($)"] + 2}'
        # This formula calculates the percentage change of scenario 2 vs. scenario 1.
    },
    {
        "name": "Year 1 Demand Charges Percent of Total Bill (%)",
        "formula": lambda col, bau, headers: f'=({col}{headers["Year 1 Annual Demand Charges ($)"] + 2})/{col}{headers["Year 1 Annual Total Bill Charges ($)"] + 2}'
        # This formula calculates the percentage change of scenario 2 vs. scenario 1.
    }
]



custom_table_rates = [
#####################################################################################################
################################ Need to get the RATE NAME to appear in header ################
#####################################################################################################

    # {
    #     "label": "Rate Headers",
    #     "key": "site",
    #     "bau_value": lambda df: "",
    #     "scenario_value": lambda df: safe_get(df, "", "")
    # },

#####################################################################################################
################################ General Information  ################################
#####################################################################################################

    {
        "label": "Installation Name",   
        "key": "installation_name",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.Meta.description")
    },
    {
        "label": "Site Location",  
        "key": "site_location",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.Meta.address")
    },
    {
        "label": "Utility Name",  
        "key": "utility_name",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.utility")
    },

#####################################################################################################
################################ Rate Analysis Summary  ################################
#####################################################################################################

    {
        "label": "Rate Analysis Summary",
        "key": "rate_analysis_summary_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Rate Name", 
        "key": "urdb_rate_name",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.rate_name")
    },
    {
        "label": "Voltage Level",  
        "key": "voltage_level",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.voltage_level")
    },
    {
        "label": "Year 1 Fixed Charges ($)",
        "key": "year_1_fixed_charges",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_fixed_cost_before_tax")
    },
    {
        "label": "Year 1 Energy Charges ($)",
        "key": "year_1_energy_charges",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_energy_cost_before_tax")
    },
    {
        "label": "Year 1 Demand Charges ($)",
        "key": "year_1_demand_charges",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_demand_cost_before_tax")
    },
    {
        "label": "Year 1 Total Bill Charges ($)",
        "key": "year_1_total_bill_charges",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_bill_before_tax")
    },
    # this value will need to be calculated compared to the current rate
    {
        "label": "Change in Year 1 Total Charges ($)",    
        "key": "change_in_year_1_total_charges",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },

#####################################################################################################
################################ Year 1 Annual Costs ################################
#####################################################################################################

    {
        "label": "Year 1 Annual Costs",
        "key": "year_1_annual_costs_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Year 1 Annual Fixed Charges ($)",
        "key": "year_1_fixed_charges",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_fixed_cost_before_tax")
    },
    # this value will need to be calculated compared to the current rate
    {
        "label": "Year 1 Fixed Charges Percent Change (%)", 
        "key": "year_1_fixed_charges_percent_change",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Year 1 Annual Energy Charges ($)",
        "key": "year_1_energy_charges",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_energy_cost_before_tax")
    },
    # this value will need to be calculated compared to the current rate
    {
        "label": "Year 1 Energy Charges Percent Change (%)", 
        "key": "year_1_energy_charges_percent_change",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Year 1 Annual Demand Charges ($)",
        "key": "year_1_demand_charges",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_demand_cost_before_tax")
    },
    # this value will need to be calculated compared to the current rate
    {
        "label": "Year 1 Demand Charges Percent Change (%)", 
        "key": "year_1_demand_charges_percent_change",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Year 1 Annual Total Bill Charges ($)",
        "key": "year_1_total_bill_charges",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.year_one_bill_before_tax")
    },
    # this value will need to be calculated compared to the current rate
    {
        "label": "Year 1 Total Bill Charges Percent Change (%)", 
        "key": "year_1_total_bill_charges_percent_change",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },

#####################################################################################################
################################ Year 1 Annual Costs as a Percent of Total Bill ################################
#####################################################################################################

    {
        "label": "Year 1 Annual Costs as a Percent of Total Bill",
        "key": "year_1_annual_costs_percent_of_total_bill_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Year 1 Fixed Charges Percent of Total Bill (%)", # value will be a calculation
        "key": "year_1_fixed_charges_percent_of_total_bill",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Year 1 Energy Charges Percent of Total Bill (%)", # value will be a calculation
        "key": "year_1_energy_charges_percent_of_total_bill",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Year 1 Demand Charges Percent of Total Bill (%)", # value will be a calculation
        "key": "year_1_demand_charges_percent_of_total_bill",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    
#####################################################################################################
################################ Load Metrics ################################
#####################################################################################################
    
    {
        "label": "Load Metrics",
        "key": "year_1_load_metrics_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "Annual Grid Purchases (kWh)",  
        "key": "annual_grid_purchases_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.annual_calculated_kwh")
    },
    {
        "label": "Year 1 Peak Load (kW)",
        "key": "year_1_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.annual_peak_kw")
    },

#####################################################################################################
################################ URDB Rate Information ################################
#####################################################################################################
    {
        "label": "URDB Rate Information",
        "key": "urdb_rate_information_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "URDB Rate Name", 
        "key": "urdb_rate_name",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.rate_name")
    },    
    {
        "label": "URDB Label", 
        "key": "urdb_label",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.label")
    },
    {
        "label": "URDB Rate Effective Date", 
        "key": "urdb_rate_effective_date",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.rate_effective_date")
    },
    {
        "label": "URDB Voltage Level", 
        "key": "urdb_voltage_level",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.voltage_level")
    },
    {
        "label": "URDB Peak kW Capacity Min", 
        "key": "urdb_peak_kw_capacity_min",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.peak_kw_capacity_min")
    },
    {
        "label": "URDB Peak kW Capacity Max", 
        "key": "urdb_peak_kw_capacity_max",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.peak_kw_capacity_max")
    },
    {
        "label": "URDB Rate Description", 
        "key": "urdb_rate_description",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.rate_description")
    },
    {
        "label": "URDB Additional Information", 
        "key": "urdb_additional_information",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.rate_additional_info")
    },
    {
        "label": "URDB Energy Comments",
        "key": "urdb_energy_comments",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.energy_comments")
    },
    {
        "label": "URDB Demand Comments", 
        "key": "urdb_demand_comments",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "inputs.ElectricTariff.urdb_metadata.demand_comments")
    },
    {
        "label": "URDB URL", 
        "key": "urdb_url",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: f'=HYPERLINK("{safe_get(df, "inputs.ElectricTariff.urdb_metadata.url_link")}", "URDB Link")'
    },
    
#####################################################################################################
################################ Year 1 Monthly Energy Costs ################################
#####################################################################################################
    
    {
        "label": "Year 1 Monthly Energy Costs ($)",
        "key": "year_1_monthly_energy_costs_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "January Energy Cost ($)",
        "key": "january_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.0")  # January
    },
    {
        "label": "February Energy Cost ($)",
        "key": "february_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.1")
    },
    {
        "label": "March Energy Cost ($)",
        "key": "march_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.2")
    },
    {
        "label": "April Energy Cost ($)",
        "key": "april_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.3")
    },
    {
        "label": "May Energy Cost ($)",
        "key": "may_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.4")
    },
    {
        "label": "June Energy Cost ($)",
        "key": "june_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.5")
    },
    {
        "label": "July Energy Cost ($)",
        "key": "july_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.6")
    },
    {
        "label": "August Energy Cost ($)",
        "key": "august_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.7")
    },
    {
        "label": "September Energy Cost ($)",
        "key": "september_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.8")
    },
    {
        "label": "October Energy Cost ($)",
        "key": "october_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.9")
    },
    {
        "label": "November Energy Cost ($)",
        "key": "november_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.10")
    },
    {
        "label": "December Energy Cost ($)",
        "key": "december_energy_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.11")
    },

#####################################################################################################
################################ Year 1 Monthly Demand Costs ################################
#####################################################################################################
    
    {
        "label": "Year 1 Monthly Demand Costs ($)",
        "key": "year_1_monthly_demand_costs_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "January Demand Cost ($)",
        "key": "january_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.0")
    },
    {
        "label": "February Demand Cost ($)",
        "key": "february_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.1")
    },
    {
        "label": "March Demand Cost ($)",
        "key": "march_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.2")
    },
    {
        "label": "April Demand Cost ($)",
        "key": "april_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.3")
    },
    {
        "label": "May Demand Cost ($)",
        "key": "may_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.4")
    },
    {
        "label": "June Demand Cost ($)",
        "key": "june_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.5")
    },
    {
        "label": "July Demand Cost ($)",
        "key": "july_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.6")
    },
    {
        "label": "August Demand Cost ($)",
        "key": "august_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.7")
    },
    {
        "label": "September Demand Cost ($)",
        "key": "september_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.8")
    },
    {
        "label": "October Demand Cost ($)",
        "key": "october_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.9")
    },
    {
        "label": "November Demand Cost ($)",
        "key": "november_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.10")
    },
    {
        "label": "December Demand Cost ($)",
        "key": "december_demand_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.11")
    },

#####################################################################################################
################################ Year 1 Monthly Total Bill Costs ################################
#####################################################################################################
    
    {
        "label": "Year 1 Monthly Total Bill Costs ($)",
        "key": "year_1_monthly_total_bill_costs_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "January Total Bill Cost ($)",
        "key": "january_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.0") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.0") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.0")
    },
    {
        "label": "February Total Bill Cost ($)",
        "key": "february_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.1") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.1") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.1")
    },
    {
        "label": "March Total Bill Cost ($)",
        "key": "march_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.2") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.2") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.2")
    },
    {
        "label": "April Total Bill Cost ($)",
        "key": "april_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.3") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.3") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.3")
    },
    {
        "label": "May Total Bill Cost ($)",
        "key": "may_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.4") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.4") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.4")
    },
    {
        "label": "June Total Bill Cost ($)",
        "key": "june_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.5") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.5") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.5")
    },
    {
        "label": "July Total Bill Cost ($)",
        "key": "july_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.6") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.6") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.6")
    },
    {
        "label": "August Total Bill Cost ($)",
        "key": "august_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.7") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.7") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.7")
    },
    {
        "label": "September Total Bill Cost ($)",
        "key": "september_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.8") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.8") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.8")
    },
    {
        "label": "October Total Bill Cost ($)",
        "key": "october_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.9") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.9") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.9")
    },
    {
        "label": "November Total Bill Cost ($)",
        "key": "november_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.10") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.10") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.10")
    },
    {
        "label": "December Total Bill Cost ($)",
        "key": "december_total_bill_cost",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricTariff.monthly_fixed_cost.11") + safe_get(df, "outputs.ElectricTariff.monthly_energy_cost_series_before_tax.11") + safe_get(df, "outputs.ElectricTariff.monthly_demand_cost_series_before_tax.11")
    },

#####################################################################################################
################################ Monthly Energy Consumption (kWh) ################################
#####################################################################################################
    
    {
        "label": "Monthly Energy Consumption (kWh)",
        "key": "monthly_energy_consumption_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "January Energy Consumption (kWh)",
        "key": "january_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.0")
    },
    {
        "label": "February Energy Consumption (kWh)",
        "key": "february_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.1")
    },
    {
        "label": "March Energy Consumption (kWh)",
        "key": "march_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.2")
    },
    {
        "label": "April Energy Consumption (kWh)",
        "key": "april_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.3")
    },
    {
        "label": "May Energy Consumption (kWh)",
        "key": "may_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.4")
    },
    {
        "label": "June Energy Consumption (kWh)",
        "key": "june_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.5")
    },
    {
        "label": "July Energy Consumption (kWh)",
        "key": "july_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.6")
    },
    {
        "label": "August Energy Consumption (kWh)",
        "key": "august_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.7")
    },
    {
        "label": "September Energy Consumption (kWh)",
        "key": "september_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.8")
    },
    {
        "label": "October Energy Consumption (kWh)",
        "key": "october_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.9")
    },
    {
        "label": "November Energy Consumption (kWh)",
        "key": "november_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.10")
    },
    {
        "label": "December Energy Consumption (kWh)",
        "key": "december_energy_consumption_kwh",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_calculated_kwh.11")
    },

#####################################################################################################
################################ Monthly Peak Load (kW) ################################
#####################################################################################################
    
    {
        "label": "Monthly Peak Load (kW)",
        "key": "monthly_peak_load_separator",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: ""
    },
    {
        "label": "January Peak Load (kW)",
        "key": "january_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.0")
    },
    {
        "label": "February Peak Load (kW)",
        "key": "february_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.1")
    },
    {
        "label": "March Peak Load (kW)",
        "key": "march_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.2")
    },
    {
        "label": "April Peak Load (kW)",
        "key": "april_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.3")
    },
    {
        "label": "May Peak Load (kW)",
        "key": "may_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.4")
    },
    {
        "label": "June Peak Load (kW)",
        "key": "june_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.5")
    },
    {
        "label": "July Peak Load (kW)",
        "key": "july_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.6")
    },
    {
        "label": "August Peak Load (kW)",
        "key": "august_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.7")
    },
    {
        "label": "September Peak Load (kW)",
        "key": "september_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.8")
    },
    {
        "label": "October Peak Load (kW)",
        "key": "october_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.9")
    },
    {
        "label": "November Peak Load (kW)",
        "key": "november_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.10")
    },
    {
        "label": "December Peak Load (kW)",
        "key": "december_peak_load_kw",
        "bau_value": lambda df: "",
        "scenario_value": lambda df: safe_get(df, "outputs.ElectricLoad.monthly_peaks_kw.11")
    }
]
