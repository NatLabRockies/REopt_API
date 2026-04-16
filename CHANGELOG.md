# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Guidelines
- When making a Pull Request into `develop` start a new double-hash header for "Develop - YYYY-MM-DD"
- When making a Pull Request into `master` change "Develop" to the next version number

### Formatting
- Use **bold** markup for field and model names (i.e. **outage_start_time_step**)
- Use `code` markup for  REopt-specific file names, classes and endpoints (i.e `reo/validators.py`)
- Use _italic_ for code terms (i.e. _list_)
- Prepend change with tag(s) directing where it is in the repository:  
`reo`,`proforma`,`resilience_stats`,`*.jl`,`REopt_Lite_API`

Classify the change according to the following categories:
    
    ### Major Updates
    ### Minor Updates
    ##### Added
    ##### Changed
    ##### Fixed
    ##### Deprecated
    ##### Removed
    ### Patches

## v3.18.0
### Minor Updates
##### Changed
- refactor docker-compose files so that base-api-image isn't built twice (in celery and django sections), fixing error "image "docker.io/library/base-api-image:latest": already exists"
- use REopt@0.57.0 (updates to federal sector defaults based on the 2025 NIST Handbook and Annual Supplement; include boiler emissions in emissions calculations)

## v3.17.5
### Minor Updates
##### Added
- Tests in `test_http_endpoints.py` to test expected `/simulated_load` POST request functionality
##### Changed
- Makes `load_type` optional for both GET and POST requests to `/simulated_load`, with a default `load_type=electric`, consistent with the `simulated_load()` function in REopt.jl
- Makes the `year` input not required for inputs with `doe_reference_name` for POST request to `/simulated_load`, consistent with GET request and `simulated_load()` function in REopt.jl
##### Fixed
- POST requests to `/simulated_load` with `doe_reference_name` input to pass along the lat/long inputs (was not passing those inputs through)


## v3.17.4
### Minor Updates
##### Fixed
- `/schedule_stats` endpoint by updating syntax for Pandas date_range based on Python 3.12 upgrade
- Enabled campus/blended building types for a POST request to `/simulated_load` endpoint by adding `percent_share`
##### Changed
- Reduced the minimum energy input for heating and cooling loads to zero, from 1.0
- Increased the max value for `annual_tonhour` cooling input by an order of magnitude

## v3.17.3
### Minor Updates
##### Added
- Input for `Wind`: `acres_per_kw` which has a default of 0.03; Wind is only constrained by this for sizes greater than 1500 kW.

## v3.17.2
### Minor Updates
##### Added
- Added `/job/get_timeseries_table` endpoint which takes a list of run_uuid's and creates a timeseries results table spreadsheet to download in response
- New custom table option `custom_timeseries_energy_demand` for endpoint `/job/get_timeseries_table`.
##### Changed
- Increased `monthly_totals_kwh` maximum value to 1.0e9.

## v3.17.1
### Minor Updates
##### Changed
- For the `/get_load_metrics` endpoint, update response field names to be consistent with `/simulated_load` for `load_type=electric`: `annual_kwh`, `max_kw` (annual peak load), `monthly_totals_kwh`, and `monthly_peaks_kw`. In a future update, this endpoint will take `load_type` as an input and return the load metrics with consistent units as `/simulated_load` for heating and cooling `load_type`s, such as `monthly_mmbtu` for the heating load types.

## v3.17.0
### Minor Updates
##### Added
- `ElectricLoad` input `monthly_peaks_kw`. Can be used to scale loads_kw or doe_reference loads to monthly peaks while maintaining monthly energy.
- `ElectricTariff` outputs: `demand_rate_average_series`, `energy_cost_series_before_tax`, `energy_cost_series_before_tax_bau`, `energy_rate_average_series`, `energy_rate_series`, `energy_rate_tier_limits`, `facility_demand_monthly_rate_series`, `facility_demand_monthly_rate_tier_limits`, `monthly_demand_cost_series_before_tax`, `monthly_demand_cost_series_before_tax_bau`, `monthly_energy_cost_series_before_tax`, `monthly_energy_cost_series_before_tax_bau`, `monthly_facility_demand_cost_series_before_tax`, `monthly_facility_demand_cost_series_before_tax_bau`, `monthly_fixed_cost_series_before_tax`, `monthly_fixed_cost_series_before_tax_bau`, `monthly_tou_demand_cost_series_before_tax`, `monthly_tou_demand_cost_series_before_tax_bau`, `tou_demand_metrics`, `tou_demand_rate_series`, `tou_demand_rate_tier_limits`.
- New endpoint `/get_load_metrics` for sending a timeseries `load_profile` and getting monthly and annual energy and peak loads.
- New custom table option `custom_table_rates` for endpoint `/job/generate_results_table`.
##### Fixed
- Avoid `CST` bypassing non-servable heating loads by going through the `HighTempThermalStorage`.


## v3.16.2
### Patches
- Added `CST` and `HighTempThermalStorage` to all/superset inputs test.
- Update REopt.jl to v0.55.1 for fix to NSRDB API call for CST
- Add CapEx to initial capex output (should have been included before)

## v3.16.1
### Patches
##### Changed
- `load_builder`: EnSite grid efficiency `grid.eff` was changed from 99% --> 100%

## v3.16.0
### Minor Updates
#### Added
- Added **Site** inputs **sector**, **federal_sector_state**, and **federal_procurement_type**
- Alternative defaults used when **sector** is "federal"
- **GHPOutputs** field **hybrid_solution_type**

## v3.15.1
### Minor Updates
##### Added
- `load_builder`: Optional debug echo for `/ensite` via `includeDebugPayload`; includes `debug.payloadEcho` showing resolved vehicle charge powers (W) and derived EMS capacity to aid troubleshooting.
##### Changed
- `load_builder`: Streamlined EnSite input schema using clear, single-purpose fields (`pChgMax_kW` for vehicles, `pChgCap_kW` for EMS override). All power normalized to Watts internally at ingress.
- `load_builder`: Deterministic EMS/site capacity derivation when no override supplied: sum of (charger count * charger power_kW) across all configured charger categories; remains zero if no chargers defined.
- `load_builder`: Cleaner validation and docstrings; removed extraneous guardrails so UI governs any numeric bounds. `schemaVersion` set to 3 for the stabilized semantics (debug flag renamed).
- `load_builder`: Enrichment still provides annualized statistics; clarified comments around unit conversions (kW <-> W, kWh <-> Wh).

## v3.15.0
### Minor Updates
##### Added
- `/ensite` view in the load_builder app directory
- `load_builder` EnSite EV charging simulation endpoint (EnLitePy) accepting either a UI-friendly schema (`chargers`, `vehicles`, `arrival`, `ems`, `maxChargeDurationHr`) or a direct EnLitePy payload; auto-derives EMS capacity from charger definitions if not overridden.
##### Changed
- Update python to v3.12, from v3.8, along with all dependencies; in particular, Django updated to 4.2.8 LTS.
- `load_builder` EnSite response enrichment (version 2): adds annualized outputs (`power_in_grid_annual` in kW, `equipment_statistics_annual`, `ev_statistics_annual`) and grid capacity utilization metrics (Min/Average/Max capacity utilization [kW]); normalizes statistics and scales 1-week simulation to annual values.

## v3.14.0
### Minor Updates
#### Added
- `CST` (concentrating solar thermal) Intputs and Outputs models; see /help endpoint for model fields
- `HighTempThermalStorage` Inputs and Outputs models; see /help endpoint for model fields
#### Changed
Update the following inputs from the previous --> new values:
- `Financial.offtaker_discount_rate_fraction`: 0.0638 --> 0.0624
- `Financial.owner_discount_rate_fraction`: 0.0638 --> 0.0624
- `Financial.elec_cost_escalation_rate_fraction`: 0.017 --> 0.0166
- `Financial.existing_boiler_fuel_cost_escalation_rate_fraction `: 0.015 --> 0.0348
- `Financial.boiler_fuel_cost_escalation_rate_fraction `: 0.015 --> 0.0348
- `Financial.chp_fuel_cost_escalation_rate_fraction `: 0.015 --> 0.0348
- `Financial.generator_fuel_cost_escalation_rate_fraction `: 0.012 --> 0.0197
- `Generator.fuel_cost_per_gallon`: 3.61 --> 2.25
- `ColdThermalStorage`, `HotThermalStorage`, `ElectricStorage` `macrs_option_years`: 7 --> 5
-  `CHP`, `ColdThermalStorage`, `HotThermalStorage`, `ElectricStorage`, `PV`, `Wind` `macrs_bonus_fraction` 0.6 --> 1.0
- `GHP.macrs_bonus_fraction`: 0.4 --> 0.0
- `GHP.macrs_option_years`: 5 --> 0
- `SteamTurbine.macrs_bonus_fraction`: 0 --> 1.0 
- `SteamTurbine.macrs_option_years`: 0 --> 5 (in order for 100% bonus depr to apply)
- `CHP.federal_itc_fraction`: 0.3 --> 0.0
- `Wind.om_cost_per_kw`: 36.0 --> 42.0 
- `Wind.size_class_to_installed_cost` = Dict(
        "residential"=> 6339.0, --> 7692.0
        "commercial"=> 4760.0, --> 5776.0
        "medium"=> 3137.0, --> 3807.0
        "large"=> 2386.0 --> 2896.0)

## v3.13.0
### Minor Updates
#### Added
- Added **Financial** inputs **min_initial_capital_costs_before_incentives** and **max_initial_capital_costs_before_incentives**
- Added **CHP** output **initial_capital_costs**
- Added new **GHPInputs** fields for advanced ground heat exchanger sizing and configuration.
- Added **hybrid_ghx_sizing_method** input to allow user selection of GHX sizing approach.
- Added new outputs to **GHPOutputs** for reporting system sizes and borehole count.
- Added tests for new GHP input and output fields.
#### Changed
- Updated **PV.installed_cost_per_kw** and **PV.om_cost_per_kw** default values to reflect latest cost data.
- Updated **ElectricStorage.installed_cost_per_kw**, **ElectricStorage.installed_cost_per_kwh**, **ElectricStorage.replace_cost_per_kw**, and **ElectricStorage.replace_cost_per_kwh** default values to reflect latest cost data.
- Updated **ElectricStorage** cost defaults in `reoptjl/models.py`
- Updated GHP input validation and defaults in `reoptjl/models.py` and `validators.py`.
- Updated `/ghpghx` endpoint to support new GHP input fields.

## v3.13.2
### Patches
- `PV` `size_class` and cost defaults not updating correctly when both `max_kw` and the site's land or roof space are input

## v3.13.1
### Patches
- Issue with `CHP` and `PV` cost curves when with-incentives segments is greater than no-incentives segments

## v3.12.3
### Minor Updates
### Added
- Add inputs: **PV.acres_per_kw** and **PV.kw_per_square_foot**

## v3.12.2
### Patches
- Enable the downloadable results spreadsheet (`job/generate_results_table` endpoint) to work with previous runs by avoiding errors when trying to do math with values of type None - handle None as zero/0

## v3.12.1
### Minor Updates
### Added
- Added the following output fields: `year_one_fuel_cost_after_tax` for `ExistingBoiler`, `CHP`, `Generator`, and `Boiler`; `ElectricTariff`: `year_one_bill_after_tax` and `year_one_export_benefit_after_tax`, `Financial`: `capital_costs_after_non_discounted_incentives`, `year_one_total_operating_cost_savings_before_tax`, `year_one_total_operating_cost_savings_after_tax`, `year_one_total_operating_cost_before_tax`, `year_one_total_operating_cost_after_tax`, `year_one_fuel_cost_before_tax`, `year_one_fuel_cost_after_tax`, `year_one_chp_standby_cost_after_tax`, `year_one_chp_standby_cost_after_tax`, `GHP.avoided_capex_by_ghp_present_value`, and `ElectricUtility.peak_grid_demand_kw`
- Added a lot of the output fields above to the custom_table_config.py file for the `job/generate_results_table` endpoint for the results table downloadable spreadsheet.
### Changed
- Using latest registered REopt.jl version 0.51.1
- For the results table downloadable spreadsheet, changed some labels to include units and made other improvements, in addition to mostly adding a bunch of the after-tax outputs described above
### Fixed
- Fixed a GHP test with the corrected `lifecycle_capital_cost` calculation to include the avoided HVAC cost and GHX residual value
- Fixed a type issue with the `/simulated_load` endpoing for cooling load with `monthly_fraction` input

## v3.12.0
### Major Updates
#### Added 
- Add inputs: 
  - **ElectricUtility.cambium_cef_metric** to utilize clean energy data from NREL's Cambium database
  - **ElectricUtility.renewable_energy_fraction_series** to supply a custom grid clean or renewable energy scalar or series
  - **Site.include_grid_renewable_fraction_in_RE_constraints** - to allow user to choose whether to include grid RE in min max constraints
  - **ElectricStorage.optimize_soc_init_fraction** (defaults to false), which makes the optimization choose the inital SOC (equal to final SOC) instead of using soc_init_fraction. The initial SOC is also constrained to equal the final SOC, which eliminates the "free energy" issue. We currently do not fix SOC when soc_init_fraction is used because this has caused infeasibility.
  - **ElectricStorage.min_duration_hours** and **ElectricStorage.max_duration_hours** for limitting electric storage's energy capacity relative to its power capacity
- Add the following outputs: 
  - **ElectricUtility.annual_renewable_electricity_supplied_kwh**
  - **Site.onsite_and_grid_renewable_electricity_fraction_of_elec_load**
  - **Site.onsite_and_grid_renewable_energy_fraction_of_total_load**
  - **ElectricLoad.annual_electric_load_with_thermal_conversions_kwh**
### Changed
- Change name of the following inputs: 
  -  **ElectricUtility.cambium_metric_col** changed to **ElectricUtility.cambium_co2_metric**, to distinguish between the CO2 and clean energy fraction metrics
- Change name of the following outputs:
  - **ElectricUtility.cambium_emissions_region** changed to **ElectricUtility.cambium_region**
  - **Site.annual_renewable_electricity_kwh** changed to **Site.annual_onsite_renewable_electricity_kwh**
  - **Site.renewable_electricity_fraction** changed to **Site.onsite_renewable_electricity_fraction_of_elec_load** 
  - **Site.total_renewable_energy_fraction** changed to **Site.onsite_renewable_energy_fraction_of_total_load**
- Change v3 endpoint `cambium_emissions_profile` to `cambium_profile`
- Change to using REopt.jl v0.51.0, which includes updates to the Cambium, AVERT, and eGRID data used


## v3.11.0
### Minor Updates
##### Changed
- Require `year` for all custom 8760/35040 load profile inputs
- Truncate the last day of the year instead of the leap day for leap years
##### Added
- Option for ASHP to `force_dispatch` (default = true) which maximizes ASHP thermal output

## v3.10.2
### Minor Updates
##### Changed
- Summary focus can now be a string with multiple types of focus such as `A,B,C`
##### Fixed
- Issue with `CHP.installed_cost_per_kw` not being an array when updating the inputs model object (which expects an array) in process_results.py, from Julia

## v3.10.1
### Minor Updates
##### Fixed
- ASHP min allowable sizing
- Prevent battery simultaneous charge/discharge
##### Changed
- Updated GHP to allow costs to be calculated for GHP and GHX separately and without running GhpGhx.jl, for district energy applications

## v3.10.0
### Minor Updates
#### Added
- Added new model **ElectricHeaterInputs**
- Added new model **ElectricHeaterOutputs**
- Added new model **ASHPWaterHeaterInputs**
- Added new model **ASHPWaterHeaterOutputs**
- Added new model **ASHPSpaceHeaterInputs**
- Added new model **ASHPSpaceHeaterOutputs**
- Added /job/generate_results_table endpoint which takes a list of run_uuid's and creates a results table spreadsheet to download in response

## v3.9.4
### Minor Updates
#### Added
- **portfolio_uuid** is now a field that can be added to API objects
- **PortfolioUnlinkedRuns** tracks which run_uuids were separated from their portfolios
- `/user/<user_uuid>/unlink_from_portfolio/` endpoint (calls `views.unlink_from_portfolio`)
- `/summary_by_runuuids/` endpoint (calls `views.summary_by_runuuids`)
- `/link_run_to_portfolios/` endpoint (calls `views.link_run_to_portfolios`)

#### Changed
- `UnexpectedError`, added portfolio_uuid as a field that can be returned in case of errors

## v3.9.3
### Minor Updates
#### Added
- `/erp/inputs` endpoint (calls `erp_help()`, same as `/erp/help`)
- `/erp/outputs` endpoint that GETs the ERP output field info (calls `erp_outputs()`)
#### Changed
- Set **reopt_version** in **APIMeta** and **ERPMeta** programatically based on actual REopt.jl package version in Julia environment instead of hardcoded so doesn't need to be updated by hand

## v3.9.2
#### Added
- Added attribute `thermal_efficiency` to the arguments of http endpoint `chp_defaults`
#### Fixed
- See fixes and changes here: https://github.com/NREL/REopt.jl/releases/tag/v0.47.2

## v3.9.1
### Minor Updates
#### Added
- Added `ProcessHeatLoadInputs` for new ways to input `ProcessHeatLoad`, similar to other loads
#### Fixed
- See fixes and changes here: https://github.com/NREL/REopt.jl/releases/tag/v0.47.0

## v3.9.0
### Minor Updates
#### Added
- In `reoptjl/models.py`, added the following fields:
  - booleans **can_serve_dhw**, **can_serve_space_heating**, and **can_serve_process_heat** to models **CHPInputs**, **ExistingBoilerInputs**, **BoilerInputs**, **SteamTurbineInputs**, and **HotThermalStorageInputs**
  - booleans **can_serve_space_heating** and **can_serve_process_heat** to model **GHPInputs**
  - arrays **storage_to_dhw_load_series_mmbtu_per_hour**, **storage_to_space_heating_load_series_mmbtu_per_hour** and **storage_to_process_heat_load_series_mmbtu_per_hour** to model **HotThermalStorageOutputs**
  - **heating_load_input** to model **AbsorptionChillerInputs**
  - arrays **thermal_to_dhw_load_series_mmbtu_per_hour**, **thermal_to_space_heating_load_series_mmbtu_per_hour**, and **thermal_to_process_heat_load_series_mmbtu_per_hour** to models **CHPOutputs**, **ExistingBoilerOutputs**, **BoilerOutputs**, **SteamTurbineOutputs**, and **HotThermalStorageOutputs**
  - boolean **retire_in_optimal** to **ExistingBoilerInputs**
- In `reopt.jl/models.py`, added new model **ProcessHeatLoadInputs** with references in `reoptjl/validators.py` and `reoptjl/views.py`
- Added process heat load to test scenario `reoptjl/test/posts/test_thermal_in_results.json`
- Added tests for the presence of process heat load and heat-load-specfic outputs to `test_thermal_in_results` within `reoptjl/test/test_job_endpoint.py`
#### Changed
- Point to REopt.jl v0.46.1 which includes bug fixes in net metering and updated PV resource data calls
#### Fixed
- Fix bug in setting default ElectricUtility.emissions_factor_CO2_decrease_fraction. Previously, user-input values were getting overwritten. 

## v3.8.0
### Minor Updates
#### Changed
- In `core/pv.jl` a change was made to make sure we are using the same assumptions as PVWatts guidelines, the default `tilt` angle for a fixed array should be 20 degrees, irrespective of it being a rooftop `(0)` or ground-mounted (open-rack)`(1)` system. By default the `tilt` will be set to 20 degrees for fixed ground-mount and rooftop, and 0 degrees for axis-tracking (`array_type = (2), (3), or (4)`)
- Added **soc_min_applies_during_outages** boolean field to **ElectricStorageInputs** (defaults to _false_)

## v3.7.0
### Minor Updates
#### Changed
- Default `Settings.solver_name` = `HiGHS`
- See updates from REopt.jl v0.44.0: https://github.com/NREL/REopt.jl/releases/tag/v0.44.0
- HiGHS, Cbc, and SCIP solvers use Big M notation constraints only in REopt.jl
#### Deprecated
- End-of-Life for v1 and v2 of the API for external/public interfacing from NREL servers. See https://github.com/NREL/REopt-Analysis-Scripts/discussions/148 for more details.

## v3.6.1
### Minor Updates
#### Fixed
- See updates from REopt.jl v0.43.0: https://github.com/NREL/REopt.jl/pull/364

## v3.6.0
### Minor Updates
#### Changed 
- Updated default fuel emissions factors from CO2 to CO2-equivalent (CO2e) values. In `reoptjl/models.py`, updated **GeneratorInputs : emissions_factor_lb_CO2_per_gal** from 22.51 to 22.58. And **FUEL_DEFAULTS: emissions_factor_lb_CO2_per_mmbtu** => Dict(
        "natural_gas"=>116.9 to 117.03,
        "landfill_bio_gas"=>114,8 to 115.38,
        "propane"=>138.6 to 139.16,
        "diesel_oil"=>163.1 to 163.61
    )
- Changed default source for CO2 grid emissions values to NREL's Cambium 2022 Database (by default: CO2e, long-run marginal emissions rates levelized (averaged) over the analysis period, assuming start year 2024). Added new emissions inputs in `ElectricUtilityInputs` to specify climate emissions rate type from Cambium. Include option for user to use AVERT data for CO2 using **co2_from_avert** boolian. 
- Update `ElectricUtility` inputs and outputs: **emissions_region** to **avert_emissions_region** and **distance_to_emissions_region_meters** to **distance_to_avert_emissions_region_meters**.
- Changed name of endpoint **emissions_profile** to **avert_emissions_profile**
#### Added 
- Added endpoint `v3/cambium_emissions_profile` to `urls.py`, `views.py`, `http.jl` to obtain Cambium emissions profile. Mainly for use in web tool.
- Added **fuel_renewable_energy_fraction** input to `ExistingBoilerInputs`
#### Fixed
- added missing wind outage outputs to list of multi dimentional outputs to transpose in `process_results()`

## v3.5.0
### Minor Updates
#### Changed
- Updated CHP `macrs_option_years` default to MACRS_YEARS_CHOICES.FIVE to align with REopt.jl default
- Changed **macrs_bonus_fraction** to from 0.80 to 0.60 (60%) for CHP, ElectricStorage, ColdThermalStorage, HotThermalStorage GHP, PV, Wind. Aligns with 20% annual decrease per Tax Cuts and Jobs Act of 2017.
- Makes **one Julia environment** to avoid needing to update REopt.jl and other dependencies in multiple locations
- Makes **one http.jl** file with conditional loading for Xpress.jl, if it is installed
- Changes all the GitHub Actions `test_job_endpoint.py` tests to use an open source solver so we can have full V3 **CI testing** again
- In julia_src/Manifest.toml, updated REopt.jl version to v0.40.0  
##### Added
- Adds a **choice of solver** in `Settings.solver_name`, and useful error messages if trying to use Xpress without installation
- Updated the Wiki in this repo with open source solver setup info

## v3.4.1
### Minor Updates
#### Fixed
- Fixed Wind validation code to prevent erroring when user provides `production_factor_series` for location outside of WindToolkit bounds. 
- Fixed divide by zero error when POSTing to the `/erp` endpoint with a `battery_size_kw` of 0
#### Changed
- Updated `reopt_version` in `ERPJob` to 0.39.1
 
## v3.4.0
### Minor Updates
#### Added 
- Added the following BAU outputs:  lifecycle_chp_standby_cost_after_tax, lifecycle_elecbill_after_tax, lifecycle_production_incentive_after_tax, lifecycle_outage_cost, lifecycle_MG_upgrade_and_fuel_cost
### Changed
- Updated REopt.jl version to 0.39.1 along with updates to other dependencies
#### Fixed
- Fixed setting of default Generator `installed_cost_per_kw` so that user inputs are not overridden 
- Avoid /summary endpoint error with off-grid runs where there is no ElectricTariff

## v3.3.0
### Changed
- Updates to REopt.jl for passing API key

## v3.2.3
### Minor Updates
##### Changed
- Ignore `CHP` unavailability during stochastic, multiple outages; this is consistent with deterministic single outage

## v3.2.2
### Minor Updates
##### Changed
- Do NOT enforce `min_turn_down_fraction` for CHP during multiple/stochastic outages

## v3.2.1
### Minor Updates
##### Fixed
- CHP-only for multiple/stochastic outages
- Allow negative fuel_burn and thermal_prod intercepts for CHP
- Correct after_tax CHP results

## v3.2.0
### Minor Updates
##### Changed
- Updates to CHP cost and performance defaults, including prime generator, from updating REopt.jl
- Changed upper limit on `CHPInputs.size_class` to 7 to reflect changes in CHP defaults.

## v3.1.1
### Minor Updates
##### Added
- Add GHP system sizes and borehole count in `queryset_for_summary()` function which is used for user runs summary information.

## v3.1.0
### Major Updates
#### Changed
- ANNUAL UPDATE TO DEFAULT VALUES. Changes outlined below with (old value) --> (new value). See user manual for references. 
  - Owner Discount rate, nominal (%): : **Financial** **owner_discount_rate_fraction** 0.0564	--> 0.0638
  - Offtaker Discount rate, nominal (%): **Financial**  **offtaker_discount_rate_fraction** 0.0564 --> 0.0638
  - Electricity cost escalation rate, nominal (%): **Financial** **elec_cost_escalation_rate_fraction** 0.019	--> 0.017
  - Existing boiler fuel cost escalation rate, nominal (%): **Financial**  **existing_boiler_fuel_cost_escalation_rate_fraction**	0.034	--> 0.015
  - Boiler fuel cost escalation rate, nominal (%): **Financial** **boiler_fuel_cost_escalation_rate_fraction**	0.034	--> 0.015
  - CHP fuel cost escalation rate, nominal (%): **Financial**  **chp_fuel_cost_escalation_rate_fraction**	0.034	--> 0.015
  - Generator fuel cost escalation rate, nominal (%): **Financial**  **generator_fuel_cost_escalation_rate_fraction**	0.027	--> 0.012
  - Array tilt – Ground mount, Fixed: **PV** **tilt** latitude	--> 20
  - O&M cost ($/kW/year): **PV** **om_cost_per_kw**	17	--> 18
  - System capital cost ($/kW): **PV** **installed_cost_per_kw**	1592	--> 1790
  - Energy capacity cost ($/kWh): **ElectricStorage** **installed_cost_per_kwh**	388	--> 455
  - Power capacity cost ($/kW): **ElectricStorage**	**installed_cost_per_kw**	775	--> 910
  - Energy capacity replacement cost ($/kWh): **ElectricStorage** **replace_cost_per_kwh**	220	--> 318
  - Power capacity replacement cost ($/kW): **ElectricStorage**	**replace_cost_per_kw**	440	--> 715
  - Fuel burn rate by generator capacity (gal/kWh): **Generator** **fuel_slope_gal_per_kwh**	0.076	--> removed and replaced with full and half-load efficiencies
  - Electric efficiency at 100% load (% HHV-basis): **Generator** **electric_efficiency_full_load**	N/A - new input	--> 0.322
  - Electric efficiency at 50% load (% HHV-basis): **Generator** **electric_efficiency_half_load**	N/A - new input	--> 0.322
  - Generator fuel higher heating value (HHV): **Generator** **fuel_higher_heating_value_kwh_per_gal**	N/A - new input	--> 40.7
  - System capital cost ($/kW): **Generator**  **installed_cost_per_kw** 500	--> $650 if the generator only runs during outages; $800 if it is allowed to run parallel with the grid; $880 for off-grid
  - Fixed O&M ($/kW/yr): **Generator** **om_cost_per_kw** Grid connected: 10 Off-grid: 20 --> Grid connected: 20 Off-grid: 10
  - System capital cost ($/kW) by Class: **Wind** **size_class_to_installed_cost**	residential - 5675 commercial - 4300 medium - 2766 large - 2239 --> residential - 6339 commercial - 4760 medium - 3137 large - 2386
  - O&M cost ($/kW/year): **Wind** **om_cost_per_kw** 35 --> 36
### Minor Updates
##### Added
- Added ability to run hybrid GHX using REopt API v3.
- Added ability to run centralized GHP scenarios using REopt API.
##### Fixed
- Fixed `test_thermal_in_results` to account for missing required inputs. 
  
## v3.0.0
### Major Updates
##### Changed
- Changed /stable URLs to point to /v3, using the REopt.jl package as the backbone of the API
- License and copyright of the repository
### Minor Updates
##### Added
- Added `OutageOutputs` field **electric_storage_microgrid_upgraded** to `reoptjl/models.py`
##### Fixed
- Fixed a bug in the `get_existing_chiller_default_cop` endpoint not accepting blank/null inputs that are optional
- In `ERPJob`, handle the `/erp` endpoint being hit before the REopt optimization associated with the provided **reopt_run_uuid** has not yet completed
- Catch and handle exceptions thrown in `process_erp_results`
- Throw error if user tries to run ERP without **max_outage_duration** or the **reopt_run_uuid** of a resilience optimization
##### Changed
- Changed `backup_reliability` results key from **fuel_outage_survival_final_time_step** to **fuel_survival_final_time_step** for consistency with other keys

## v2.16.0
### Minor Updates
##### Added
- /v3 endpoints which use the reoptjl app and the REopt.jl Julia package, but /stable still points to /v2 so this is not a breaking change
 - Django model **ERPWindInputs**, used in `ERPJob()`, `erp_help()`, and `erp_results()`
##### Changed
- Modified production k8s server resources to best match v3 resource consumption (v2 will still work fine, but may have less throughput)

## v2.15.0
### Minor Updates
##### Added
- Add `GHP` to `reoptjl` app for v3
- Add `Boiler` to `reoptjl` app for v3 along with appropriate tests
- Add `SteamTurbine` to `reoptjl` app for v3 along with appropriate tests
- Add `/ghp_efficiency_thermal_factors` endpoint to `reoptjl` app for v3
- Add `/get_existing_chiller_default_cop` endpoint to `reoptjl` app for v3
- Add `/get_chp_defaults` endpoint to `reoptjl` app
##### Changed
- Update a couple of GHP functions to use the GhpGhx.jl package instead of previous Julia scripts and data from v2
- Update `julia_src/` TOML files to point to **REopt.jlv0.32.6**
##### Fixed
- Fixed a type mismatch bug in the `simulated_load` function within http.jl

## v2.14.0
### Minor Updates
##### Fixed
- In reoptjl/ app (v3), updated `Generator` **installed_cost_per_kw** from 500 to 650 if **only_runs_during_grid_outage** is _true_ or 800 if _false_
- Added `test_other_conditional_inputs` method in `job/test/test_validator.py` to test inputs with defaults or overrides based on other input values within the same model
#### Changed
- Changed name of "job" app (folder) to "reoptjl". Note that name has been updated throughout the CHANGELOG as well.

## v2.13.0
### Minor Updates
##### Fixed
- Fix array_type enum check in `cross_clean_pv()`(value stored as int not string)
- Calculate `ERPElectricStorageInputs` **num_battery_bins** default based on battery duration to prevent significant discretization error
- Set max on `ERPElectricStorageInputs` **num_battery_bins** to limit memory usage
- Make time step values returned from peak_load_outage_times endpoint 1-indexed
- Don't let peak_load_outage_times endpoint return a time step less than 1
- Fix validation of outage_durations considering that durations include the start time step

## v2.12.0
### Minor Updates
##### Added
- Added `summary` endpoint and `reoptjl/views.summary`
- Added `summary_by_chunk` endpoint and `reoptjl/views.summary_by_chunk`
- Added `unlink` endpoint and `reoptjl/views.unlink` along with **UserUnlinkedRuns**
- Add **GeneratorInputs** field **fuel_higher_heating_value_kwh_per_gal**, which defaults to 40.7 (diesel)
- Add CHP to ERP testing
##### Changed
- Default **FinancialInputs** field **value_of_lost_load_per_kwh** to zero
- Default **SiteInputs** field **min_resil_time_steps** to max value in **ElectricUtilityInputs** **outage_durations**
- Changed the v3/easiur_costs endpoint to call a v3 specific view that uses the REopt julia package's EASIUR functionality instead of calling the v1/v2 easiur_costs view
- `reoptjl/api.py` to save user_uuid and webtool_uuid to **APIMeta** data model for each request
##### Fixed
- A 0-indexing off by one bug in the `peak_load_outage_times` view/endpoint where seasons were defined as starting on 2nd days of months
- If user specifies **ERPGeneratorInputs**/**ERPPrimeGeneratorInputs** **electric_efficiency_full_load** but not **electric_efficiency_half_load** in ERP post, don't use the REopt **GeneratorInputs**/**CHPInputs** **electric_efficiency_half_load**, instead let **ERPGeneratorInputs**/**ERPPrimeGeneratorInputs** **electric_efficiency_half_load** default to **electric_efficiency_full_load**
- In **LoadProfileChillerThermal**, add check that user hasn't supplied monthly energy, in addition to checking annual energy, before using electric load to calculate cooling load
- A couple ERP survival probability calculation fixes by updating to REopt.jl 0.32.1 

## v2.11.0
### Minor Updates
##### Added
- Enabled hybrid GHX sizing within the GHP model through the **hybrid_ghx_sizing_method** variable
	- User is able to select "Automatic" (REopt sizes GHX based on the smaller of the heating or cooling load), "Fractional" (GHX size is a user-defined fraction of the non-hybrid GHX size), or "None" (non-hybrid)
	- Auxiliary heater and cooler are both currently only electric
	- Outputs added to track the thermal production, electrical consumption, and size of the auxiliary unit
##### Changed
- Updated default value **init_sizing_factor_ft_per_peak_ton** from 246.1 to 75 for the `/ghpghx` endpoint

## v2.10.1
### Patches
- Make **ERPOutageInputs** field **max_outage_duration** required
- In ERP inputs processing, check that **ElectricUtility** **outage_durations** is not empty before calculating max
- Respond with validation error if **max_outage_duration** not provided and can't be calculated

## v2.10.0
### Minor Updates
##### Added
- REopt.jl outage outputs not yet integrated into the API: **OutageOutputs** fields **storage_microgrid_upgrade_cost**, **storage_discharge_series_kw**, **pv_microgrid_size_kw**, **pv_microgrid_upgrade_cost**, **pv_to_storage_series_kw**, **pv_curtailed_series_kw**, **pv_to_load_series_kw**, **generator_microgrid_size_kw**, **generator_microgrid_upgrade_cost**, **generator_to_storage_series_kw**, **generator_curtailed_series_kw**, **generator_to_load_series_kw**, **chp_microgrid_size_kw**, **chp_microgrid_upgrade_cost**, **chp_to_storage_series_kw**, **chp_curtailed_series_kw**, **chp_to_load_series_kw**, **chp_fuel_used_per_outage_mmbtu**
##### Changed
- Default **FinancialInputs** field **microgrid_upgrade_cost_fraction** to 0
- Add missing units to **OutageOutputs** field names: **unserved_load_series_kw**, **unserved_load_per_outage_kwh**, **generator_fuel_used_per_outage_gal**
##### Fixed
- Default ERP **OutageInputs** **max_outage_duration** to max value in **ElectricUtility** **outage_durations** if **reopt_run_uuid** provided for ERP job

## v2.9.1
### Patches
##### Added
- In reoptjl app (v3): emissions_profile endpoint and view function that returns the emissions data for a location

## v2.9.0
### Minor Updates
##### Added 
 - Energy Resilience and Performance Tool:
    - Uses functionality added to the REopt Julia package in v0.27.0 to calculate outage survival reliability metrics for a DER scenario, which can be based on the results of a REopt optimization
    - Django models **ERPMeta**, **ERPGeneratorInputs**, **ERPPrimeGeneratorInputs**, **ERPElectricStorageInputs**, **ERPPVInputs**, **ERPOutageInputs**, **ERPOutputs**
    - `/erp` endpoint to which users POST ERP inputs (calls `ERPJob()`)
    - `/erp/<run_uuid>/results` endpoint that GETs the results of an ERP job (calls `erp_results()`) 
    - `/erp/help` endpoint that GETs the ERP input field info (calls `erp_help()`)
    - `/erp/chp_defaults` endpoint that GETs ERP CHP/prime generator input defaults based on parameters `prime_mover`, `is_chp`, and `size_kw` (calls `erp_chp_prime_gen_defaults()`)
    - Tests in `resilience_stats/tests/test_erp.py`
 - In reoptjl app (v3), added Financial **year_one_om_costs_before_tax_bau**, **lifecycle_om_costs_after_tax_bau** 
 - Added field **production_factor_series** to Django models **WindOutputs** and **PVOutputs**
 - In **REoptjlMessageOutputs** added a **has_stacktrace** field to denote if response has a stacktrace error or not. Default is False.
 - Added access to the multiple outage stochastic/robust modeling capabilities in REopt.jl. Not all inputs and outputs are exposed, but the following are:
   - **SiteInputs**: **min_resil_time_steps**
   - **ElectricUtilityInputs**: **outage_start_time_steps**, **outage_durations**, **outage_probabilities**
   - **OutageOutputs**: **expected_outage_cost**, **max_outage_cost_per_outage_duration**, **unserved_load_series**, **unserved_load_per_outage**, **microgrid_upgrade_capital_cost**, **generator_fuel_used_per_outage**
 - Added test using multiple outage modeling
 - Add /dev/schedule_stats endpoint
 - In reoptjl app (v3): added **AbsorptionChillerInputs** model
- In reoptjl app (v3): added **AbsorptionChillerOutputs** model
- In `reoptjl/views.py`:
    - add new input/output models to properly save the inputs/outputs
    - add `/absorption_chiller_defaults` endpoint which calls the http.jl absorption_chiller_defaults endpoint
##### Changed
- Update REopt.jl to v0.28.0 for reoptjl app (/dev -> v3)
- `/reoptjl/chp_defaults` endpoint updated to take optional electric load metrics for non-heating CHP (Prime Generator in UI)
  - Changed `/chp_defaults` input of `existing_boiler_production_type` to `hot_water_or_steam`
  - `CHP.size_class` starting at 0 for average of other size_classes
  - `CHP.max_size` calculated based on heating load or electric load
- In reoptjl app (v3), changed Financial **breakeven_cost_of_emissions_reduction_per_tonnes_CO2** to **breakeven_cost_of_emissions_reduction_per_tonne_CO2**
- In reoptjl app (v3), changed default ElectricLoad **year** to 2022 if user provides load data and 2017 if using CRBD
 - Changed `scalar_to_vector` helper function to `scalar_or_monthly_to_8760`
 - Changed **GeneratorInputs** fields **fuel_slope_gal_per_kwh** and **fuel_intercept_gal_per_hr** to **electric_efficiency_full_load** and **electric_efficiency_half_load** to represent the same fuel burn curve in a different way consistent with **CHPInputs**
- Updated the following default values to reoptjl app (v3):
  - **federal_itc_fraction** to 0.3 (30%) in models **PVInputs**, **WindInputs**, and **CHPInputs** 
  - **total_itc_fraction** to 0.3 (30%) in models **HotWaterStorageInputs**, **ColdWaterStorageInputs**, and **ElectricStorageInputs**
  - ***macrs_bonus_fraction** to 0.8 (80%) in models **PVInputs**, **WindInputs**, **CHPInputs**, PV, **HotWaterStorageInputs**, **ColdWaterStorageInputs**, and **ElectricStorageInputs**
  - **macrs_option_years** to 7 years in models **HotWaterStorageInputs** and **ColdWaterStorageInputs**
- In `reo/nested_inputs.py` v2 inputs (`defaults_dict[2]`), updated the following default values in models **ColdThermalStorageInputs**, **HotThermalStorageInputs**
  - **macrs_option_years** to 7 (years)
  - **macrs_bonus_pct** to 0.8 (80%)
- In `reo/nested_inputs.py` v2 inputs (`defaults_dict[2]`), updated the following default values:
  - ColdTES, HotTES: **macrs_option_years** to 7 (years)
  - ColdTES, HotTES: ***macrs_bonus_pct** to 0.8 (80%)
- Updated the following default values to reoptjl app (v3):
  - PV, Wind, Storage, CHP, Hot Water Storage, Cold Water Storage, Electric Storage: **federal_itc_fraction(PV,Wind,CHP)** and **total_itc_fraction(Hot Water Storage, Cold Water Storage, Electric Storage)** to 0.3 (30%)
  - PV, Wind, Storage, CHP, Hot Water Storage, Cold Water Storage, Electric Storage: ***macrs_bonus_fraction** to 0.8 (80%)
  - Hot Water Storage and Cold Water Storage: **macrs_option_years** to 7 years
  Use TransactionTestCase instead of TestCase (this avoids whole test being wrapped in a transaction which leads to a TransactionManagementError when doing a database query in the middle)
- Updated ubuntu-18.04 to ubuntu-latest in GitHub push/pull tests because 18.04 was deprecated in GitHub Actions    
##### Fixed
- In reo (v2), calculation of `net_capital_costs_plus_om` was previously missing addition sign for fuel charges. Corrected this equation.

## v2.8.0
### Minor Updates
##### Changed
- In `reo/nested_inputs.py` v2 inputs (`defaults_dict[2]`), updated the following default values:
##### Changed
- In `reo/nested_inputs.py` v2 inputs (`defaults_dict[2]`), updated the following default values:
   - PV, Wind, Storage, CHP, GHP: **federal_itc_pct** to 0.30 (30%)
   - PV, Wind, Storage, CHP, GHP: ***macrs_bonus_pct** to 0.8 (80%)
- The `ghpghx` app and Julia endpoint in `http.jl` uses the [GhpGhx.jl](https://github.com/NREL/GhpGhx.jl) Julia package instead of internal Julia scripts with git submodule for the `tess.so` file
##### Removed 
- From v3 (models.py), removed duplicate output Financial **lifecycle_om_costs_after_tax** and un-used output Financial **replacement_costs**

## v2.7.1
### Minor Updates
##### Added 
- In reoptjl app (v3): Added **addressable_load_fraction** to SpaceHeatingLoad and DomesticHotWaterLoad inputs. 
##### Changed
- Changed redis service memory settings to mitigate "out of memory" OOM issue we've been getting on production
 
## v2.7.0
### Minor Updates
##### Changed
- In reoptjl app (v3): Name changes for many outputs/results. Generally, changes are for energy outputs (not costs) that include "year_one", and are changed to annual_ for scalars and to production_to_, thermal_to_ etc. for time series.
- In reoptjl app (v3): Changed some _bau outputs to align with REopt.jl outputs
##### Added 
 - In reoptjl app (v3): Added **thermal_production_series_mmbtu_per_hour** to CHP results.
##### Removed
- In reoptjl app (v3): Removed outputs not reported by REopt.jl
##### Fixed
- In reoptjl/views for `/simulated_load` endpoint: Fixed the data type conversion issues between JSON and Julia
  
## v2.6.0
### Minor Updates
##### Added
1. **REoptjlMessageOutputs** model to capture errors and warnings returned by REoptjl during input processing and post optimization
2. Missing output fields for **ExistingBoilerOutputs** model
3. API test `reoptjl/test\posts\all_inputs_test.json` to include all input models in a single API test
- added **HotThermalStorageInputs** model
- added **HotThermalStorageOutputs** model
- added **ColdThermalStorageInputs** model
- added **ColdThermalStorageOutputs** model
- add **HotThermalStorageOutputs**
- add **ColdThermalStorageOutputs**
- `0012_coldthermalstorageinputs....` file used to add new models to the db
##### Changed
1. Default values for the following fields were changed to align them with REopt API v2 (i.e. stable, and REopt.jl) defaults. As-is, these values are aligned with REopt v1 defaults. Units were unchanged.
- **FinancialInputs.elec_cost_escalation_rate_fraction** from 0.023 to 0.019
- **FinancialInputs.offtaker_discount_rate_fraction** from 0.083 to 0.0564
- **FinancialInputs.owner_discount_rate_fraction** from 0.083 to 0.0564
- **PVInputs.installed_cost_per_kw** from 1600 to 1592
- **PVInputs.om_cost_per_kw** from 16 to 17
- **WindInputs.om_cost_per_kw** from 16 to 35
- **ElectricStorageInputs.installed_cost_per_kw** from 840 to 775
- **ElectricStorageInputs.installed_cost_per_kwh** from 420 to 388
- **ElectricStorageInputs.replace_cost_per_kw** from 410 to 440
- **ElectricStorageInputs.replace_cost_per_kwh** from 200 to 220
2. Modified `julia_src\http.jl` and `julia_src\cbc\http.jl` to return status 400 when REopt responds with an error
3. Updated `r["Messages"]` in `views.py` to include **REoptjlMessageOutputs** errors and warnings

## v2.5.0
### Minor Updates
##### Added
- `0011_coolingloadinputs....` file used to add new models to the db
In `reoptjl/models.py`:
- added **ExistingChillerInputs** model
- added **ExistingChillerOutputs** model
- added **CoolingLoadInputs** model
- added **CoolingLoadOutputs** model
- added **HeatingLoadOutputs** model
In `reoptjl/process_results.py`: 
- add **ExistingChillerOutputs** 
- add **CoolingLoadOutputs**
- add **HeatingLoadOutputs**
In `reoptjl/validators.py:
- add time series length validation on **CoolingLoadInputs->thermal_loads_ton** and **CoolingLoadInputs->per_time_step_fractions_of_electric_load**
In `reoptjl/views.py`:
- add new input/output models to properly save the inputs/outputs

## v2.4.0
### Minor Updates
##### Added 
- In `reoptjl/models.py`:
  - add **CHPInputs** model
  - add **CHPOutputs** model
- In `reoptjl/process_results.py` add **CHPOutputs**
- In `reoptjl/validators.py` add new input models
- In `reoptjl/views.py`:
  - add new input/output models to properly save the inputs/outputs
  - add `/chp_defaults` endpoint which calls the http.jl chp_defaults endpoint
  - add `/simulated_load` endpoint which calls the http.jl simulated_load endpoint    
    
## v2.3.1
### Minor Updates
##### Fixed
Lookback charge parameters expected from the URDB API call were changed to the non-caplitalized format, so they are now used properly.

## v2.3.0
### Minor Updates
##### Changed
The following name changes were made in the `reoptjl/` endpoint and `julia_src/http.jl`: 
 - Change "_pct" to "_rate_fraction" for input and output names containing "discount", "escalation", and "tax_pct" (financial terms)
 - Change "_pct" to "_fraction" for all other input and output names (e.g., "min_soc_", "min_turndown_")
 - Change **prod_factor_series** to **production_factor_series**
 - Updated the version of REopt.jl in /julia_src to v0.20.0 which includes the addition of:
   - Boiler tech from the REopt_API (known as NewBoiler in API)
   - SteamTurbine tech from the REopt_API 

## v2.2.0
### Minor Updates 
##### Fixed
- Require ElectricTariff key in inputs when **Settings.off_grid_flag** is false
- Create and save **ElectricUtilityInputs** model if ElectricUtility key not provided in inputs when **Settings.off_grid_flag** is false, in order to use the default inputs in `reoptjl/models.py`
- Added message to `messages()` to alert user if valid ElectricUtility input is provided when **Settings.off_grid_flag** is true
- Register 
- Make all urls available from stable/ also available from v2/. Includes registering `OutageSimJob()` and `GHPGHXJob()` to the 'v2' API and adding missing paths to urlpatterns in `urls.py`.
##### Changed
- `reoptjl/models.py`: 
    - remove Generator `fuel_slope_gal_per_kwh` and `fuel_intercept_gal_per_hr` defaults based on size, keep defaults independent of size 
	- changed `get_input_dict_from_run_uuid` to accomodate new models
	- changed **ElectricLoadInputs.wholesale_rate** to use `scalar_to_vector` function
- `reoptjl/validators.py`: Align PV tilt and aziumth defaults with API v2 behavior, based on location and PV type
##### Added 
- `0005_boilerinputs....` file used to add new models to the db
- `reoptjl/` endpoint: Add inputs and validation to model off-grid wind 
- added **ExistingBoilerInputs** model
- added **ExistingBoilerOutputs** model
- added **SpaceHeatingLoadInputs** model
- added `scalar_to_vector` to convert scalars of vector of 12 elements to 8760 elements
- **GeneratorInputs** (must add to CHP and Boiler when implemented in v3)
    - added `emissions_factor_lb_<pollutant>_per_gal` for CO2, NOx, SO2, and PM25
    - add `fuel_renewable_energy_pct`
- **ElectricUtilityInputs**
    - add `emissions_factor_series_lb_<pollutant>_per_kwh` for CO2, NOx, SO2, and PM25
- **Settings**
    - add `include_climate_in_objective` and `include_health_in_objective`
- **SiteInputs**
    - add `renewable_electricity_min_pct`, `renewable_electricity_max_pct`, and `include_exported_renewable_electricity_in_total`
    - add `CO2_emissions_reduction_min_pct`, `CO2_emissions_reduction_max_pct`, and `include_exported_elec_emissions_in_total`
- **FinancialInputs**
    - add `CO2_cost_per_tonne`, `CO2_cost_escalation_pct`
    - add `<pollutant>_grid_cost_per_tonne`, `<pollutant>_onsite_fuelburn_cost_per_tonne`, and `<pollutant>_cost_escalation_pct` for NOx, SO2, and PM25
- **FinancialOutputs**
    - add **lifecycle_fuel_costs_after_tax** 
- **SiteOutputs**
    - add `renewable_electricity_pct`, `total_renewable_energy_pct`
    - add `year_one_emissions_tonnes_<pollutant>`, `year_one_emissions_from_fuelburn_tonnes_<pollutant>`, `lifecycle_emissions_tonnes_<pollutant>`, and `lifecycle_emissions_from_fuelburn_tonnes_<pollutant>` for CO2, NOx, SO2, and PM25
- **FinancialOutputs**
    - add `breakeven_cost_of_emissions_reduction_per_tonnes_CO2`
In `reoptjl/process_results.py`: 
- add **HotThermalStorageOutputs**
- add **ExistingBoilerOutputs**
In `reoptjl/test/test_job_endpoint.py`: 
- test that AVERT and EASIUR defaults for emissions inputs not provided by user are passed back from REopt.jl and saved in database
- add a testcase to validate that API is accepting/returning fields related to new models.
In `'reoptjl/validators.py`:
- add new input models
- added `update_pv_defaults_offgrid()` to prevent validation failure when PV is not provided as input
In `reoptjl/views.py`:
- Added **SiteInputs** to `help` endpoint
- Added **SiteOutputs** to `outputs` endpoint
- add new input/output models to properly save the inputs/outputs

## v2.1.0
### Minor Updates 
##### Changed
- The `/stable` URL now correctly calls the `v2` version of the REopt model (`/job` endpoint)
- Don't trigger Built-in Tests workflow on a push that only changes README.md and/or CHANGELOG.md
- Avoid triggering duplicate GitHub workflows. When pushing to a branch that's in a PR, only trigger tests on the push not on the PR sync also.
In `reoptjl/models.py` : 
- **Settings**
    - Added **off_grid_flag**
    - Changed **run_bau** to be nullable
- **FinancialInputs**
    - Added **offgrid_other_capital_costs**
    - Added **offgrid_other_annual_costs**
- **FinancialOutputs**
    - Added **lifecycle_generation_tech_capital_costs**
    - Added **lifecycle_storage_capital_costs**
    - Added **lifecycle_om_costs_after_tax**
    - Added **lifecycle_fuel_costs_after_tax**
    - Added **lifecycle_chp_standby_cost_after_tax**
    - Added **lifecycle_elecbill_after_tax**
    - Added **lifecycle_production_incentive_after_tax**
    - Added **lifecycle_offgrid_other_annual_costs_after_tax**
    - Added **lifecycle_offgrid_other_capital_costs**
    - Added **lifecycle_outage_cost**
    - Added **lifecycle_MG_upgrade_and_fuel_cost**
    - Added **replacements_future_cost_after_tax**
    - Added **replacements_present_cost_after_tax**
    - Added **offgrid_microgrid_lcoe_dollars_per_kwh**
    - Changed **lifecycle_capital_costs_plus_om** field name to **lifecycle_capital_costs_plus_om_after_tax**
    - Changed **lifecycle_om_costs_bau** field name to **lifecycle_om_costs_before_tax_bau**
- **ElectricLoadInputs**
    - Removed default value for **critical_load_met_pct**. If user does not provide this value, it is defaulted depending on **Settings -> off_grid_flag**
    - Added **operating_reserve_required_pct**
    - Added **min_load_met_annual_pct**
- **ElectricLoadOutputs**
    - Added **offgrid_load_met_pct**
    - Added **offgrid_annual_oper_res_required_series_kwh**
    - Added **offgrid_annual_oper_res_provided_series_kwh**
    - Added **offgrid_load_met_series_kw**
- **ElectricTariffInputs**
    - Changed field name **coincident_peak_load_active_timesteps** to **coincident_peak_load_active_time_steps**
- **ElectricTariffOutputs**
    - Changed field name **year_one_energy_cost** to **year_one_energy_cost_before_tax**
    - Changed field name **year_one_demand_cost** to **year_one_demand_cost_before_tax**
    - Changed field name **year_one_fixed_cost** to **year_one_fixed_cost_before_tax**
    - Changed field name **year_one_min_charge_adder** to **year_one_min_charge_adder_before_tax**
    - Changed field name **year_one_energy_cost_bau** to **year_one_energy_cost_before_tax_bau**
    - Changed field name **year_one_demand_cost_bau** to **year_one_demand_cost_before_tax_bau**
    - Changed field name **year_one_fixed_cost_bau** to **year_one_fixed_cost_before_tax_bau**
    - Changed field name **year_one_min_charge_adder_bau** to **year_one_min_charge_adder_before_tax_bau**
    - Changed field name **lifecycle_energy_cost** to **lifecycle_energy_cost_after_tax**
    - Changed field name **lifecycle_demand_cost** to **lifecycle_demand_cost_after_tax**
    - Changed field name **lifecycle_fixed_cost** to **lifecycle_fixed_cost_after_tax**
    - Changed field name **lifecycle_min_charge_adder** to **lifecycle_min_charge_adder_after_tax_bau**
    - Changed field name **lifecycle_energy_cost_bau** to **lifecycle_energy_cost_after_tax_bau**
    - Changed field name **lifecycle_demand_cost_bau** to **lifecycle_demand_cost_after_tax_bau**
    - Changed field name **lifecycle_fixed_cost_bau** to **lifecycle_fixed_cost_after_tax_bau**
    - Changed field name **lifecycle_min_charge_adder_bau** to **lifecycle_min_charge_adder_after_tax_bau**
    - Changed field name **lifecycle_export_benefit** to **lifecycle_export_benefit_after_tax**
    - Changed field name **lifecycle_export_benefit_bau** to **lifecycle_export_benefit_after_tax_bau**
    - Changed field name **year_one_bill** to **year_one_bill_before_tax**
    - Changed field name **year_one_bill_bau** to **year_one_bill_before_tax_bau**
    - Changed field name **year_one_export_benefit** to **year_one_export_benefit_before_tax**
    - Changed field name **year_one_export_benefit_bau** to **year_one_export_benefit_before_tax_bau**
    - Changed field name **year_one_coincident_peak_cost** to **year_one_coincident_peak_cost_before_tax**
    - Changed field name **year_one_coincident_peak_cost_bau** to **year_one_coincident_peak_cost_before_tax_bau**
    - Changed field name **lifecycle_coincident_peak_cost** to **lifecycle_coincident_peak_cost_after_tax**
    - Changed field name **lifecycle_coincident_peak_cost_bau** to **lifecycle_coincident_peak_cost_after_tax_bau**
    - Changed field name **year_one_chp_standby_cost** to **year_one_chp_standby_cost_before_tax**
    - Changed field name **lifecycle_chp_standby_cost** to **lifecycle_chp_standby_cost_after_tax**
- **ElectricTariffInputs**
    - Changed validation of this model to be conditional on **Settings.off_grid_flag** being False
    - Changed **ElectricTariffInputs** `required inputs` error message to alert user that ElectricTariff inputs are not required if **Settings.off_grid_flag** is true.
- **PVInputs**
    - Removed default values for `can_net_meter`, `can_wholesale`, and `can_export_beyond_nem_limit` as defaults for these fields are set depending on **Settings->off_grid_flag**
    - Added field **operating_reserve_required_pct**
- **PVOutputs**
    - Changed name of **lifecycle_om_cost** to **lifecycle_om_cost_after_tax**
- **WindOutputs**
    - Changed name of **lifecycle_om_cost** to **lifecycle_om_cost_after_tax**
    - Changed name of **year_one_om_cost** to **year_one_om_cost_before_tax**
- **ElectricStorageInputs**
    - Removed default values for **soc_init_pct** and **can_grid_charge** as these defaults are set conditional on **Settings->off_grid_flag**
- **GeneratorInputs**
    - Removed default values for **fuel_avail_gal** and **min_turn_down_pct** as these defaults are set conditional on **Settings->off_grid_flag**
    - Added field **replacement_year**
    - Added field **replace_cost_per_kw**
- **GeneratorOutputs**
    - Changed field name **fuel_used_gal** to **average_annual_fuel_used_gal**
    - Changed field name **year_one_variable_om_cost** to **year_one_variable_om_cost_before_tax**
    - Changed field name **year_one_fuel_cost** to **year_one_fuel_cost_before_tax**
    - Changed field name **year_one_fixed_om_cost** to **year_one_fixed_om_cost_before_tax**
    - Changed field name **lifecycle_variable_om_cost** to **lifecycle_variable_om_cost_after_tax**
    - Changed field name **lifecycle_fuel_cost** to **lifecycle_fuel_cost_after_tax**
    - Changed field name **lifecycle_fixed_om_cost** to **lifecycle_fixed_om_cost_after_tax**

`reoptjl/run_jump_model.py` - Remove `run_uuid` key from input dictionary before running REopt to avoid downstream errors from REopt.jl
`reoptjl/validators.py`
    - Changed **ElectricTariffInputs** to validate if **ElectricTariff** key exists in inputs
    - Added message to `messages()` to alert user if valid ElectricTariff input is provided when **Settings.off_grid_flag** is true.
    - Added message to `messages()` to alert user of technologies which can be modeled when **Settings.off_grid_flag** is true.
    - Added validation error to alert user of input keys which can't be modeled when **Settings.off_grid_flag** is true.
`reoptjl/views.py` - Changed validation code to try to save **ElectricTariffInputs**
`reoptjl/test_job_endpoint.py` - Added test to validate API off-grid functionality
- Added migration file `0005_remove_...` which contains the data model for all Added and Changed fields

## v2.0.3
### Minor Updates
##### Fixed
- In `src/pvwatts.py`, Updated lat-long coordinates if-statement used to determine whether the "nsrdb" dataset should be used to determine the PV prod factor. Accounts for recent updates to NSRDB data used by PVWatts (v6) 
- Avoids overwriting user-entered PV azimuth (other than 180) for ground-mount systems in southern hemisphere
- Updates default azimuth to 0 for southern latitudes for all PV types (rather than just for ground-mount)

## v2.0.2
### Patches
- bug fix for 15/30 minute scenarios with URDB TOU demand rates

## v2.0.1
### Minor Updates
##### Changed
Removed override of user inputs for `fuel_slope_gal_per_kwh` and `fuel_intercept_gal_per_hr` in validators.py. User inputs for these values will now be used in analysis. If these inputs are not supplied, the default values in nested_inputs.py will be used.

## v2.0.0 Default cost updates
Changing default costs can result in different results for the same inputs. Hence we are making a major version change.

- the release of v2 will make https://developer.nrel.gov/api/reopt/stable = https://developer.nrel.gov/api/reopt/v2
- if API users do not want results to change / want to use the old default values, then they should use https://developer.nrel.gov/api/reopt/v1

The default values changed are:

- Discount rate from 8.3% to 5.64%
- Electricity cost escalation rate from 2.3% to 1.9%
- PV System capital cost ($/kW) from $1600 to $1592
- PV O&M cost ($/kW/yr) from $16 to $17
- Battery Energy capacity cost ($/kWh) from $420 to $388
- Battery Power capacity cost ($/kW AC) from $840 to $775
- 10 yr Battery Energy capacity replacement cost ($/kWh) from $200 to $220
- 10 yr Battery Power capacity replacement cost ($/kW AC) from $410 to $440
- Wind O&M cost ($/kW/yr) from $40 to $35
- Wind System Capital costs ($/kW)

    - Residential (0-20 kW) from $11950 to $5675
    - Commercial (21-100 kW) from $7390 to $4300
    - Midsize (101-999 kW) from $4440 to $2766
    - Large (>=1000 kW) from $3450 to $2239

### Patches
- `reo`: Fix list_of_list conversion in `validators.py` not capturing inner list type. E.g. a 2D list of floats that was supposed to be a 2D list of integers wasn't getting caught.


## v1.9.1 - 2021-12-16
### Minor Updates
##### Added
- `reo`: **GHP** heating and cooling HVAC efficiency thermal factor inputs and defaults to account for a reduction in heating and/or cooling loads with **GHP** retrofits
- `*.jl`: Reduction in heating and cooling loads due to the thermal factors (described above) if **GHP** is chosen.  

## v1.9.0 - 2021-12-15
### Minor Updates
##### Added
- `reo`: Added capability to estimate year 1 and lifecycle emissions and climate and health costs of CO2, NOx, SO2, and PM2.5 from on-site fuel burn and grid-purchased electricity. Added total renewable energy calculations. User options to include climate and/or health costs in the objective function. User options to set emissions and/or renewable electricity constraints. User options to include or exclude exported electricity in renewable energy and emissions calculations. New emissions and renewable energy inputs (and defaults) in `nested_inputs.py` and outputs in `nested_outputs.py`. Added default emissions data for NOx, PM2.5, and SO2 in `src/data`. Default marginal health costs in `src/data/EASIUR_Data`. In `views.py` and `urls.py` added **easiur_costs** and **fuel_emissions_rates** urls. Default fuel emissions rates for NOx, SO2, and PM2.5 in `validators.py`. Added calculation of breakeven CO2 cost (when NPV is negative).
- `reopt_model.jl`: Included additional optional constraints for emissions reductions (as compared to BAU) and renewable electricity percentage. Added optional inclusion of climate and health costs to the model objective and associated life cycle cost calculation. Added calculations of life cycle emissions and costs for CO2, NOx, SO2, and PM2.5. Added calculation of renewable energy (% and kWh), which includes electric and thermal end uses. Emissions and renewable energy calculations account for all technologies.   
- `utils.jl` added emissions- and renewable energy-specific parameters.
##### Changed 
- `reo`: Changed default value for `generator_fuel_escalation_pct` for on-grid runs; was previously defaulted to `escalation_pct`. In `views.py`, changed `emissions_profile` view to additionally include grid emissions factors for NOx, SO2, and PM2.5 (in addition to CO2). Changed several emissions and renewable energy-related input and output names in `nested_inputs.py` and `nested_outputs.py`.  
- `reopt_model.jl`: Changed calculation of renewable electricity % to be based on consumption rather than generation, accounting for battery storage losses, curtailment, and the option to include or exclude exported renewable electricity. Renewable electricity % additionally accounts for renewable fuels that power electricity generation. Changed year one emissions calculations to optionally include or exclude emissions offsets from exported electricity.  
## v1.8.0 - 2021-11-11
### Minor Updates
##### Added
- `reo`: Added capability to model off-grid systems with `PV`, `Storage`, and/or `Generator`; added off-grid-specific default values in `nested_inputs.py`; added off-grid specific outputs in `nested_outputs.py`. 
- `reopt_model.jl`: Included additional constraints for off-grid runs for minimum load met and load and PV operating reserve constraints; add `p.OtherCapitalCosts` and `p.OtherAnnualCosts` to model objective for off-grid runs. 
- `utils.jl` added off-grid specific parameters 

## v1.7.0 - 2021-09-29
##### Added
- `reo`: The following technologies: `SteamTurbine`, `NewBoiler`, and `GHP`, and added supplmentary firing for `CHP`
- `reopt_model.jl`: Variables and constraints for the new technologies listed above, including supplementary firing sizing and dispatch for `CHP`
- `ghpghx`: New app which serves the `GHPGHX.jl` module using a POST-style endpoint similar to the `/reo Job` endpoint. There is also a `ground_conductivity` endpoint in this app for GETting the default GHX ground conductivity by location.
- `julia_src`: The `GHPGHX.jl` module and supporting `*.jl` scripts, served by an endpoint in `http.jl`
- `input_files`: Reorganized the different load profile data files into folders, and split out space heating and domestic hot water from the `LoadProfileBoilerFuel` data
##### Changed
- `reo`: The default processing of `LoadProfileChillerThermal` with a `doe_reference_name` is now such that the user does not have to specify `annual_tonhour`, and the processing will use the building(s) fraction of total electric load that is consumed for cooling

## v1.6.0 - 2021-06-09
### Minor Updates
##### Added
- `summary`: Added `/summary_by_chunk` endpoint to enable a fraction of a user's total runs and summary metrics to be returned; this prevents excessive wait times when the UI was trying to load all runs
- New `<host>/dev/futurecosts` endpoint 
##### Patches
- was returning -1 for `bau_sustained_time_steps` when no critical load was met in BAU case (now returns zero)
- fixed issue with modeling last time step of the year in outages 
- `NewMaxSize` was sometimes less than the `TechClassMinSize`, creating infeasible problems
- fix `user` URLs

## v1.5.0 - 2021-03-12
### Minor Updates
##### Changed
- `reo`, `*.jl`: Changed the units-basis for heating load, thermal production, and fuel consumption to kW/kWh, from mmbtu/mmbtu_per_hr and gal. This does not affect the units of the inputs or outputs.
##### Removed
- `reo`: The following inputs for `Site.Boiler`: `installed_cost_us_dollars_per_mmbtu_per_hr`, `min_mmbtu_per_hr`, and `max_mmbtu_per_hr`, and for `Site.ElectricChiller`: `installed_cost_us_dollars_per_kw`, `min_kw`, and `max_kw`.
### Patches
- `reo`: Catch issue in `process_results.py` where `renewable_electricity_energy_pct` is not explicitly set to _None_
- `reo`:  Catch case where `CHP` `prime_mover` is not set and not all required fields are filled in
- `reo`:  Catch issues with `itc_unit_basis` when the ITC is 100%
- `validators.py`: Fix bug where length of percent_share != length of doe_reference_name even though no percent_share is provided (in `LoadProfileBoilerFuel`)

## v1.4.4 - 2021-02-25
### Patches
- `reo`: In `validators.py` catches case where invalid percent_share entry was used in check special cases function
- `reo`: In `loadprofile.py` catches where 0 lat/long was resolving to _False_ and leading to _None_ for lat and long
- `reo`: Fix divide by 0 error in results processing
- `reo`: Handle floats as URBD periods
- `reo`: Fix `list_of_float` only types
    
## v1.4.3 - 2021-02-18
### Patches
- `reo`: new output `Financial.developer_om_and_replacement_present_cost_after_tax_us_dollars`
- `reo`: Fix **PVWatts** being called when user provides `PV.prod_factor_series_kw`
- `reopt_api`: new `docker-compose.nginx.yml` for standing up the API on a server with remote access (for example if one wants to host the API on a cloud service)
- `reopt_api`: update `Dockerfile.xpress` to use `nlaws/pyjul:1.5.3` base image (was using Julia 1.3)
- `reopt_api`: update `julia_envs/Xpress` PyCall from 1.91.4 to 1.92.2
    
## v1.4.2 - 2021-02-03
### Patches
- `reo`: Fix **Wind** `size_class` was not being set
- `proforma`: Fix could not handle runs prior to v1.4.0 with no CHP database entries
- `resilience_stats`: Fix could not handle runs prior to v1.4.0 with no CHP database entries
- `resilience_stats`: `outage_simulator` returns 100% survivability when chp_kw >= critical_loads_kw

## v1.4.1 - 2021-02-01
### Patches
- `reo`: Fixes database query error the occurs when getting production runs created prior to v1.4.0    

## v1.4.0 - 2021-01-29
### Minor Updates
##### Added
- `reo`/`reopt.jl`: Coincident peak rates and expected time steps can be specified. There can be a single rate and list of time steps. Or there can be multiple CP periods in a year with different rates, and then a set of time steps is specified for each rate. Peak demand occurring during each set of CP time steps is charged at the corresponding CP rate.

- `reo`: Add a new **ElectricTariff** inputs and outputs: 
 - **coincident_peak_load_active_timesteps**
 - **coincident_peak_load_charge_us_dollars_per_kw**
 - **year_one_coincident_peak_cost_us_dollars**
 - **year_one_coincident_peak_cost_bau_us_dollars**
 - **total_coincident_peak_cost_us_dollars**
 - **total_coincident_peak_cost_bau_us_dollars**

## v1.3.0 - 2021-01-28
### Minor Updates
- `reo`: New output **om_and_replacement_present_cost_after_tax_us_dollars**
- `reo`, `*.jl`: New load **LoadProfileBoilerFuel**
    - Heating load of the site, as defined by boiler fuel consumption
- `reo`, `*.jl`: New Tech **Boiler**
    - BAU Tech which serves heating load. It consumes fuel and produces hot thermal energy.
- `reo`: New **Site**-level input **FuelTariff**
    - Cost structure for fuel consumed by **Boiler** and **CHP** Techs. Currently allows fixed annual or monthly values for fuel cost.
- `reo`, `*.jl`: New load **LoadProfileChillerThermal**
    - Cooling load of the site, as defined by a thermal load produced by the BAU **ElectricChiller** or a fraction of total electric load.
    - This is treated as a subset of the total electric load (**LoadProfile**)
- `reo`, `*.jl`: New Tech **ElectricChiller**
    - BAU Tech which serves cooling load. It consumes electricity and produces chilled water to meet the cooling load or charge **ColdTES**.
- `reo`, `*.jl`: New Tech **CHP**
    - Combined heat and power (CHP) Tech which serves electric and heating loads. Its hot thermal production can also supply **AbsorptionChiller** or charge the **HotTES**.
- `reo`, `*.jl`: New Tech **AbsorptionChiller**
    - Cooling technology which serves cooling load with a hot thermal input. It can also charge **ColdTES**.
- `reo`, `*.jl`: New Storage **HotTES**
    - Storage model representing a hot water thermal energy storage tank. It can store hot thermal energy produced by **CHP** (or **Boiler**, but not typically).
- `reo`, `*.jl`: New Storage **ColdTES**
    - Storage model representing a chilled water thermal energy storage tank. It can store cold thermal energy produced by **ElectricChiller** or **AbsorptionChiller**.
- `reo`: Changed `/simulated_load` endpoint to add optional **load_type** query param for **cooling** and **heating**
    - Use **load_type** = "heating" with **annual_mmbtu** or **monthly_mmbtu** for heating load
    - Use **load_type** = "cooling" with **annual_tonhour** or **monthly_tonhour** for cooling load 
- `reo`: New endpoint `/chp_defaults`
    - Endpoint for the default **prime_mover**, **size_class**, and default cost and performance parameters for **CHP**
- `reo`: New endpoint `/loadprofile_chillerthermal_chiller_cop`
    - Endpoint for the default **LoadProfileChillerThermal.chiller_cop** based on peak cooling load
- `reo`: New endpoint `/absorption_chiller_defaults`
    - Endpoint for the default **AbsorptionChiller** cost and performance parameters based on thermal type ("hot_water" or "steam") and peak cooling load
- `reo`: New endpoint `/schedule_stats`
    - Endpoint for getting default **CHP.chp_unavailability_periods** and summary metrics of the unavailability profile
### Patches
 - `summary`: Address failing cases in user `summary` endpoint due to missing load profile data


## v1.2.0 - 2021-01-04
### Minor Updates
##### Added
- `reo`: new inputs **outage_start_time_step** and **outage_end_time_step** to replace deprecated **outage_start_hour** and **outage_end_hour**. The latter are used as time step indices in the code, so for sub-hourly problems they do not have hourly units. For now **outage_start_hour** and **outage_end_hour** are kept in place to preserve backwards-compatibility. Also note that the new inputs are not zero-indexed.
- `reo`: new output **bau_sustained_time_steps** to replace deprecated **sustain_hours** (also not deprecated yet but warning is now in response).
- `*.jl`: new **dvProductionToCurtail** for all techs in all time steps (was previously construed with dvProductionToGrid for the third sales tier, which is meant for selling energy back to the grid beyond the annual load kWh constraint.)
- `reo`:  new inputs for all Techs: **can_net_meter**, **can_wholesale**, **can_export_beyond_site_load**, **can_curtail**
    - the first three correspond to the previous `SalesTiers`, now called `ExportTiers`
    - reduces the problem size in many cases since the previous model always included all three `SalesTiers` in every scenario and the new model only includes `ExportTiers` with non-zero compensation when there are Technologies that can participate

##### Changed
- `resilience_stats`: Calculate **avoided_outage_costs_us_dollars** from the `outagesimjob` endpoint
##### Fixed
##### Deprecated
- `reo`: **LoadProfile** **outage_start_hour** and **outage_end_hour** in favor of **outage_start_time_step** and **outage_end_time_step**
- `reo`: **LoadProfile** **sustain_hours** in favor of **bau_sustained_time_steps**

##### Removed

### Patches
- `resilience_stats`: Catch BAU cases and do not calculate avoided outage costs
- `summary`: Catch jobs that errored out and do not parse results
- `reo`: Catch `PVWattsDownloadError` when a bad response is received
- `reo`: **fuel_used_gal** output for **Generator** was incorrect for scenarios with **time_steps_per_hour** not equal to 1


## v1.1.0 - 2020-12-08
### Major
### Minor
##### Added
- `reo`: Add new Financial outputs :
     - **developer_annual_free_cashflow_series_us_dollars**
     - **offtaker_annual_free_cashflow_series_bau_us_dollars**
     - **offtaker_annual_free_cashflow_series_us_dollars** 
     - **offtaker_discounted_annual_free_cashflow_series_bau_us_dollars**
     - **offtaker_discounted_annual_free_cashflow_series_us_dollars**
- `reo`: New capability to model a rolling lookback if URDB lookbackRange is non-zero
- `reo`: Add a new third-party financing output: 
     - **net_present_cost_us_dollars**
- `reo`: New Wind curtailment output
     - **year_one_curtailed_production_series_kw**
- `reo`: Emissions factor series added for ElecticTariff (defaults to AVERT regional data) and Generator:
     - **emissions_factor_series_lb_CO2_per_kwh**
     - **emissions_factor_lb_CO2_per_gal**
- `reo`/`proforma`: ElectricTariff, Generator and Site year 1 emissions totals as new outputs from API and in Proform
     - **emissions_region** (Site Only)
     - **year_one_emissions_lb_C02**
     - **year_one_emissions_bau_lb_C02**
     - **year_one_emissions_lb_NOx**
     - **year_one_emissions_bau_lb_NOx**
- `reo`: LCOE API output added for PV and Wind:
     - **lcoe_us_dollars_per_kwh**
- `reo`: Simple Payback/IRR API outputs added for Site:
     - **irr_pct**
     - **simple_payback_years**
- `reo`: New total storage rebates ($/kWh) Storage input:
     - **total_rebate_us_dollars_per_kwh**
- `proforma`: PV LCOE, Wind LCOE,  Host Present Worth Factor, Developer Present Worth Factor, PV Energy Levelization Factor, and Simple Payback added
- `*.jl`Add new constraint that sets `dvGridToStorage` to zero for all grid connected time steps when Storage.canGridCharge is false
- `reo`: Add hybrid load profile option. New LoadProfile inputs:
     - **percent_share**
     - **doe_reference_name** (now a str or lis of str)
- `reo`: Add PV curtailment output:
     - **year_one_curtailed_production_series_kw**
- `proforma`:  Two proforma templates, now with 3 tabs instead of 2. 
     [1] one party: separate optimal and BAU cash flows
     [2] two party: separate developer and host cash flows (showing capital recovery factor and developer IRR ). 
- `reo`: New output for year 1 existing PV production
     - **average_yearly_energy_produced_bau_kwh**
- `reo`: Add inputs to ElectricTariff to handle custom TOU energy rates (1-hr or 15-min resolutions):
	- **add_tou_energy_rates_to_urdb_rate**
	- **tou_energy_rates_us_dollars_per_kwh** 
- `reo`: Handle multiple PV systems by including a list of PV dictionaries instead of a single dictionary. New PV inputs include:
    - **pv_name**
	- **pv_number** 
	- **location**
- `reo`: New custom production factor inputs for PV and Wind: 
     - **prod_factor_series_kw**
- `reo`: Three new **Financial** outputs: 
     - **initial_capital_costs**
     - **initial_capital_costs_after_incentives**
     - **replacement_costs**
- `resilience_stats`: New `financial_check` endpoint

##### Changed
- `reo`: Remove third-party factor from **initial_capital_costs_after_incentives** output
- `reo`/`proforma`: Renames two party to third-party throughout the code
- `reo`: When the wholesale rate is zero, all excess production is forced into curtailment bin by setting the wholesale rate to -1,000 $/kWh
- `resilience_stats`: New post-and-poll process for resilience stats and removal of **avoided_outage_costs_us_dollars** calculation from results endpoint
     \
     **Note in the future this kind of change will be classified as major**
- `*.jl`: reverted export rate inputs to negative values (to match legacy conventions)
- `reo`: Enables existing diesel generator in the financial case outage simulation

##### Fixed
- `reo`: Developer generator OM costs now based on new capacity only in API-side calculations to match Proforma spreadsheet (could results in different API-reported NPV)
- `resilience_stats`: Bug fix **PV** was not contributing to sustaining outage in the BAU case
- `reo`: In non-third party cases the owner tax and discount percents were not saved to the database resulting in inaccurate after-incentive cost calculations in the web UI
- `*.jl`: **Wind** dispatch fixes in julia code - including hooking up missing outputs
- `*.jl`: Load balances constraints fixed in julia code
- `proforma`: Addressed bugs, including: 
    - Removed energy generation values from cash flow sheets
	- Added **Generator** fixed O&M cost outputs (was not accounted for in proforma)
	- Upfront capex was wrong with existing kw and no optimal kw
	- Removed **PV** degradation from other techs' annual production
	- Escalation and discount rates were applied incorrectly (off by one year)
	- O&M costs were double accounted, once with tax benefit, once without
	- Total installed costs was calculated incorrectly
	- **Wind** and **Storage** bonus fraction cell references were switched with each other in proforma_generator
	- Corrected **PV** PBI calcultion using new existing PV production output 

##### Deprecated
##### Removed

### Patches
- `reo`: Catch and flag _NaN_ input parameters
- `*.jl`: Update `Xpress.jl` to v0.12 (should fix the OOM issues with celery workers)
- `reo`: Set new cap on tax rates to avoid a divide by zero in results processing and the proforma
- `*.jl`: fix OutOfMemory error in docker containers when building constraints in models that have more than one time step per hour
- `reo`: Fix divide by 0 error in BAU outage sim job code when no existing PV
- `reo`: Fix **simple_payback_years** and **irr_pct** calcs in `reo/process_results.py`
- `reo`: Fix bug in **upfront_capex_after_incentives**
- `reo`: `Scenario.py` was checking for wrong message in exception and raising `UnexpectedError` instead of `WindDownloadError`
- `*.jl`: Diesel fuel costs were indexed on electric tariff tiers, which was necessary before the reformulation, but now leads to an index error in the JuMP model.
- `reo`: Addresses multiple pvs and a division by 0 case in outage simulator inputs
- `reo`: Report _NaN_ IRR values as _null_
- `reo`: Require **energyratestructure**, **energyweekendschedule** and **energyweekdayschedule** in a URDB rate; added new checking of URDB float fields
- `proforma`: Fix bug when **year_one_export_benefit_bau_us_dollars** or **year_one_export_benefit_us_dollars** is null
- `reo`: Updated handling of cases where outagesim results are not ready
- `*.jl`: DER export to grid (in NEM and wholesale `SalesTiers`) was not set to zero during `TimeStepsWithoutGrid`.
- `reo`: Run scenarios through `reopt.jl` to get the code precompiled in system images
- `reo`: Fixes generator power output bug in resilience check
- `resilience_stats`: Catches case where the same outagesim job is submitted twice
- `resilience_stats`: Replaces _JsonResponse_ with _ImmediateHttpResponse_ for errors in `outagesimjob` workflow
- `reo`: Bug fix to enable battery dispatch results to be returned
- `resilience_stats`: When an outagesimjob has already been returned the status code is now 208 (Already Reported) rather than 500
- `reo`: Enable rerunning of POSTs (clean up **PV** and **Wind** prod factor and all `percent_share` entries in `results` response)
- `reo`: Uses new Wind Toolkit API URL
- `proforma`: Updated storage to read per kW and per kWh incentives
- `proforma`: Updated final cashflow to include non-taxed year 0 incentives (CBI and IBI)
- `*.jl`: `MinChargeAdd` in `reopt.jl` was only accounting for year zero charges (needs to be lifecycle charges)
- `REopt_API`: Use Django version 2.2.13 (had been 2.2.6)
- `reo`: Handling the financial scenario's user uploaded critical load series bug
- `reo`: Fix bug in URDB parsing timestep for TOU rates
- `reo`: Fix bug in error handling for load profiles with negative non-net loads
- `reo`: Handle non `REoptError`s in scenario.py
- `reo`: `results` response will not return empty lists in inputs or outputs
- `reo`: Use default **LoadProfile** `year` of 2017 for all built-in load profiles
- `reo`: Set 2019 default `year` in nested_inputs
- `*.jl`: Fix bug where `pwf_prod_incent` was accounting for the discount rate and `LevelizationFactorProdIncent` was accounting for production degradation
- `reo`: Upgrade to URDB 7, maintain backwards compatibility
- `resilience_stats`: New resilience stats and financial metrics added to user summary endpoint
- `reo`: More informative PVWatts error when site it too far away
- `reo`/`resilience_stats`: Fix bug where `simulated_load` endpoint was not handling `monthly_totals_kwh`
- `reo`: Fix bug where **Wind** was not constrained based on `land_acres`
- `resilience_stats`: Fix resilience stastics bugs including: 
    - mis-scaling the existing **PV** production
    - `resilience_stats` was returning 8759 hours survived when critical load was met for entire year
    - `resilience_stats` battery model was assuming that inverter was DC capacity, but inverter is AC capacity
    - the monthly and hourly survival probabilities were being returned as 1 when there was zero probability
- `*.jl`: Upgrade psutil from 4.3.1 to 5.6.6.

## v1.0.0 - 2020-02-28
### Major
- First release of the REopt API
