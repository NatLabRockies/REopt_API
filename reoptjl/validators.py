# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import logging
import pandas as pd
from reoptjl.models import MAX_BIG_NUMBER, APIMeta, ExistingBoilerInputs, UserProvidedMeta, SiteInputs, Settings, ElectricLoadInputs, ElectricTariffInputs, \
    FinancialInputs, BaseModel, Message, ElectricUtilityInputs, PVInputs, CSTInputs, ElectricStorageInputs, GeneratorInputs, WindInputs, SpaceHeatingLoadInputs, \
    DomesticHotWaterLoadInputs, CHPInputs, CoolingLoadInputs, ExistingChillerInputs, HotThermalStorageInputs, ColdThermalStorageInputs, \
    AbsorptionChillerInputs, BoilerInputs, SteamTurbineInputs, GHPInputs, ProcessHeatLoadInputs, ElectricHeaterInputs, ASHPSpaceHeaterInputs, \
    ASHPWaterHeaterInputs, HighTempThermalStorageInputs
from django.core.exceptions import ValidationError
from pyproj import Proj
from typing import Tuple

log = logging.getLogger(__name__)


def scrub_fields(obj: BaseModel, raw_fields: dict):
    """
    Remove invalid inputs (by only keeping the inputs with names matching the Django Model fields).
    Also converts non-list values to lists when the Django field is an ArrayField.
    :param obj:
    :param raw_fields:
    :return:
    """
    valid_fields = [f.name for f in obj._meta.fields[1:]]
    types = [str(type(f)) for f in obj._meta.fields[1:]]
    types_dict = {k: v for k, v in zip(valid_fields, types)}

    scrubbed_dict = dict()
    for k, v in raw_fields.items():
        if k in valid_fields:
            scrubbed_dict[k] = v
            if "ArrayField" in types_dict[k] and not isinstance(v, list):
                # this if block allows inputs to be Array or Real values (converted to Array for database)
                scrubbed_dict[k] = [v]
    return scrubbed_dict


class InputValidator(object):

    def __init__(self, raw_inputs: dict, ghpghx_inputs_validation_errors=None):
        """
        Validate user inputs
        Used in reoptjl/api.py to:
        1. Clean each Model's individual fields, which checks:
            - required inputs provided
            - inputs have correct types
            - inputs within min/max limits
            - fills in default values
        2. Check requirements across each Model's fields
            - eg. if user provides outage_start_time_step then must also provide outage_end_time_step
        3. Check requirements across Model fields
            - eg. the time_steps_per_hour must align with the length of loads_kw
        """
        # TODO figure out how to align with MessagesModel from v1 with validation errors, resampling messages, etc.
        self.validation_errors = dict()
        self.resampling_messages = dict()
        self.ghpghx_inputs_errors = ghpghx_inputs_validation_errors
        self.models = dict()
        self.objects = (
            APIMeta,
            Settings, #needs to be next in this list so that off-grid checks in loop below work
            UserProvidedMeta,
            SiteInputs,
            ElectricLoadInputs,
            ElectricTariffInputs,
            FinancialInputs,
            ElectricUtilityInputs,
            PVInputs,
            ElectricStorageInputs,
            GeneratorInputs,
            WindInputs,
            CoolingLoadInputs,
            ExistingChillerInputs,
            ExistingBoilerInputs,
            SpaceHeatingLoadInputs,
            DomesticHotWaterLoadInputs,
            CHPInputs,
            BoilerInputs,
            HotThermalStorageInputs,
            HighTempThermalStorageInputs,
            ColdThermalStorageInputs,
            AbsorptionChillerInputs,
            SteamTurbineInputs,
            GHPInputs,
            ProcessHeatLoadInputs,
            ElectricHeaterInputs,
            ASHPSpaceHeaterInputs,
            ASHPWaterHeaterInputs,
            CSTInputs
        )
        self.pvnames = []
        on_grid_required_object_names = [
            "Site", "ElectricLoad", "ElectricTariff"
        ]
        off_grid_required_object_names = [
            "Site", "ElectricLoad"
        ]
        
        filtered_user_post = dict()
        filtered_user_post[APIMeta.key] = scrub_fields(APIMeta, raw_inputs[APIMeta.key])
        meta = APIMeta.create(**filtered_user_post[APIMeta.key])
        self.models[APIMeta.key] = meta
        meta.save()  # must save the APIMeta first to use it as a OneToOneField/ForeignKey in other models

        for obj in self.objects:
            if obj == APIMeta: continue  # already created and saved
            if obj.key in raw_inputs.keys():
                if isinstance(raw_inputs[obj.key], list) and obj.key == "PV":  # only handle array of PV
                    for (i, user_pv) in enumerate(raw_inputs["PV"]):
                        name = user_pv.get("name", "")
                        self.pvnames.append(name if not name == "" else "PV" + str(i))
                        filtered_user_post[self.pvnames[-1]] = scrub_fields(obj, user_pv)
                        self.models[self.pvnames[-1]] = obj.create(meta=meta, **filtered_user_post[self.pvnames[-1]])
                else:
                    filtered_user_post[obj.key] = scrub_fields(obj, raw_inputs[obj.key])
                    self.models[obj.key] = obj.create(meta=meta, **filtered_user_post[obj.key])
            elif obj.key in ["Settings", "Financial"]:
                self.models[obj.key] = obj.create(meta=meta)  # create default values
            elif obj.key == "ElectricUtility" and not self.models["Settings"].off_grid_flag:
                self.models[obj.key] = obj.create(meta=meta)  # create default values
            elif (obj.key in off_grid_required_object_names if self.models["Settings"].off_grid_flag else obj.key in on_grid_required_object_names):
                self.validation_errors[obj.key] = "Missing required inputs."

        self.scrubbed_inputs = filtered_user_post

    @property
    def messages(self):
        """
        Warnings to be passed to the user from the results endpoint (in the "messages").
        NOTE: no need for including errors here since we do not create a APIMeta when there are errors.
            The errors are returned to the user in reoptjl/api.py
        :return: dict with str keys and values, which are saved in the Message model for each APIMeta
        """
        msg_dict = dict()

        if self.resampling_messages:
            msg_dict["resampled inputs"] = self.resampling_messages

        if self.models["ElectricLoad"].doe_reference_name != "" or \
                len(self.models["ElectricLoad"].blended_doe_reference_names) > 0:
            msg_dict["info"] = ("When using doe_reference_name or blended_doe_reference_names for ElectricLoad the "
                                "year is set to 2017 because the DoE load profiles start on a Sunday.")
        if self.models["ElectricLoad"].doe_reference_name != "" and \
                len(self.models["ElectricLoad"].blended_doe_reference_names) > 0:
            msg_dict["ignored inputs"] = ("Both doe_reference_name and blended_doe_reference_names were provided for "
                                "ElectricLoad. This is redundant, so only doe_reference_name is being used.")
        if self.models["Settings"].off_grid_flag==True:
            if "ElectricTariff" in self.models.keys():
                msg_dict["ignored inputs"] = ("ElectricTariff inputs are not applicable when off_grid_flag is true, and will be ignored. "
                                "Provided ElectricTariff can be removed from inputs")
            if "ElectricUtility" in self.models.keys():
                msg_dict["ignored inputs"] = ("ElectricUtility inputs are not applicable when off_grid_flag is true, and will be ignored. "
                                "Provided ElectricUtility can be removed from inputs")
            msg_dict["info"] = ("When off_grid_flag is true, only PV, Wind, ElectricStorage, Generator technologies can be modeled.")
        return msg_dict

    @property
    def validated_input_dict(self):
        """
        Passed to the Julia package, which can handle unused top level keys (such as messages) but will error if
        there are incorrect keys in the next level. For example, if Site.address is passed to
        the Julia package then a method error will be raised in Julia because the Site struct has no address field.
        :return:
        """
        d = dict()
        for model in self.models.values():
            if model.key == "PV" and self.pvnames:
                if "PV" not in d.keys():
                    d["PV"] = [{k: v for (k, v) in model.dict.items() if v not in [None, []]}]
                else:
                    d["PV"].append({k: v for (k, v) in model.dict.items() if v not in [None, []]})
            else:
                d[model.key] = {k: v for (k, v) in model.dict.items() if v not in [None, []]}
                # cleaning out model attribute
        return d

    def clean_fields(self):
        """
        Run all models' clean_fields methods
        :return: None
        """
        for model in self.models.values():
            try:
                model.clean_fields(exclude=["coincident_peak_load_active_time_steps"])
                # coincident_peak_load_active_time_steps can have unequal inner lengths (it's an array of array),
                # which is not allowed in the database. We fix the lengths with repeated last values by overriding the
                # Django Model save method on ElectricTariffInputs. We then remove the repeated values before
                # passing coincident_peak_load_active_time_steps to Julia (b/c o.w. JuMP.constraint will raise an error
                # for duplicate constraints)
            except ValidationError as ve:
                self.validation_errors[model.key] = ve.message_dict

    def clean(self):
        """
        Run all models' clean methods
        :return: None
        """
        for model in self.models.values():
            try:
                model.clean()
            except ValidationError as ve:
                self.validation_errors[model.key] = ve.message_dict

    def cross_clean(self):
        """
        Validation that requires comparing fields from more than one model
        :return: None
        """

        """
        PV validation
        """
        def cross_clean_pv(pvmodel):     
            if pvmodel.__getattribute__("tilt") is None:
                if pvmodel.__getattribute__("array_type") in (pvmodel.ARRAY_TYPE_CHOICES.GROUND_MOUNT_FIXED_OPEN_RACK, 
                                                            pvmodel.ARRAY_TYPE_CHOICES.ROOFTOP_FIXED):
                    pvmodel.__setattr__("tilt", 20)
                else:
                    pvmodel.__setattr__("tilt", 0)
                
            
            if pvmodel.__getattribute__("azimuth") == None:
                if self.models["Site"].__getattribute__("latitude") >= 0:
                    pvmodel.__setattr__("azimuth", 180)
                else:
                    pvmodel.__setattr__("azimuth", 0.0)
            
            if pvmodel.__getattribute__("max_kw") > 0:
                if len(pvmodel.__getattribute__("production_factor_series")) > 0:
                    self.clean_time_series("PV", "production_factor_series")
            
            if self.models["Settings"].off_grid_flag==True:
                pvmodel.__setattr__("can_net_meter", False)
                pvmodel.__setattr__("can_wholesale", False)
                pvmodel.__setattr__("can_export_beyond_nem_limit", False)
                if pvmodel.__getattribute__("operating_reserve_required_fraction") == None: # user provided no value
                    pvmodel.__setattr__("operating_reserve_required_fraction", 0.25)
            else:
                pvmodel.__setattr__("operating_reserve_required_fraction", 0.0) # override any user provided values

        def update_pv_defaults_offgrid(self, pvmodel):
            if pvmodel.__getattribute__("can_net_meter") == None:
                if self.models["Settings"].off_grid_flag==False:
                    pvmodel.__setattr__("can_net_meter", True)
                else:
                    pvmodel.__setattr__("can_net_meter", False)
            
            if pvmodel.__getattribute__("can_wholesale") == None:
                if self.models["Settings"].off_grid_flag==False:
                    pvmodel.__setattr__("can_wholesale", True)
                else:
                    pvmodel.__setattr__("can_wholesale", False)
            
            if pvmodel.__getattribute__("can_export_beyond_nem_limit") == None:
                if self.models["Settings"].off_grid_flag==False:
                    pvmodel.__setattr__("can_export_beyond_nem_limit", True)
                else:
                    pvmodel.__setattr__("can_export_beyond_nem_limit", False)

            if pvmodel.__getattribute__("operating_reserve_required_fraction") == None:
                if self.models["Settings"].off_grid_flag==False:
                    pvmodel.__setattr__("operating_reserve_required_fraction", 0.0)
                else:
                    pvmodel.__setattr__("operating_reserve_required_fraction", 0.25)

        if "PV" in self.models.keys():  # single PV
            cross_clean_pv(self.models["PV"])
            update_pv_defaults_offgrid(self, self.models["PV"])

        if len(self.pvnames) > 0:  # multiple PV
            for pvname in self.pvnames:
                cross_clean_pv(self.models[pvname])
                update_pv_defaults_offgrid(self, self.models[pvname])

        """
        Time series values are up or down sampled to align with Settings.time_steps_per_hour
        """
        for key, time_series in zip(
            ["ElectricLoad", "ElectricLoad"],
            ["loads_kw",     "critical_loads_kw"]
        ):
            self.clean_time_series(key, time_series)
                        
        """
        Wind model validation
        1. If wind resource not provided, add a validation error if lat/lon not within WindToolkit data set
        2. If prod factor or resource data provided, validate_time_series for each
        NOTE: if size_class is not provided: size_class is determined in the Julia package based off of average load and wind installed_cost_per_kw is determined based on size_class.
        """
        if "Wind" in self.models.keys():
            if self.models["Wind"].__getattribute__("max_kw") > 0:
                wind_resource_inputs = [
                    "wind_meters_per_sec", "wind_direction_degrees",
                    "temperature_celsius", "pressure_atmospheres"
                ]

                for time_series in ["production_factor_series"] + wind_resource_inputs:
                    self.clean_time_series("Wind", time_series)

                if not all([self.models["Wind"].__getattribute__(wr) for wr in wind_resource_inputs]) and not self.models["Wind"].__getattribute__("production_factor_series"):
                    # then no wind_resource_inputs provided, so we need to get the resource from WindToolkit
                    if not lat_lon_in_windtoolkit(self.models["Site"].__getattribute__("latitude"),
                                                  self.models["Site"].__getattribute__("longitude")):
                        self.add_validation_error("Wind", "Site",
                              "latitude/longitude not in the WindToolkit database. Cannot retrieve wind resource data.")
            
            if self.models["Settings"].off_grid_flag==True:
                if self.models["Wind"].__getattribute__("operating_reserve_required_fraction") == None: # user provided no value
                    self.models["Wind"].operating_reserve_required_fraction = 0.50
                self.models["Wind"].can_net_meter = False
                self.models["Wind"].can_wholesale = False
                self.models["Wind"].can_export_beyond_nem_limit = False
            else:
                self.models["Wind"].operating_reserve_required_fraction = 0.0 # override any user input

        """
        ElectricTariff
        Key can be absent when running off-grid scenarios
        """
        if "ElectricTariff" in self.models.keys():

            for key, time_series in zip(
                ["ElectricTariff",              "ElectricTariff",   "ElectricTariff"],
                ["tou_energy_rates_per_kwh",    "wholesale_rate",   "export_rate_beyond_net_metering_limit"]
            ):
                self.clean_time_series(key, time_series)

            cp_ts_arrays = self.models["ElectricTariff"].__getattribute__("coincident_peak_load_active_time_steps")
            max_ts = 8760 * self.models["Settings"].time_steps_per_hour
            if len(cp_ts_arrays) > 0:
                if len(cp_ts_arrays[0]) > 0:
                    if any(ts > max_ts for a in cp_ts_arrays for ts in a):
                        self.add_validation_error("ElectricTariff", "coincident_peak_load_active_time_steps",
                                                f"At least one time step is greater than the max allowable ({max_ts})")

            if self.models["ElectricTariff"].urdb_response:
                if "energyweekdayschedule" in self.models["ElectricTariff"].urdb_response.keys():
                    urdb_rate_time_steps_per_hour = int(len(self.models["ElectricTariff"].urdb_response[
                                                            "energyweekdayschedule"][1]) / 24)
                    if urdb_rate_time_steps_per_hour > self.models["Settings"].time_steps_per_hour:
                        # do not support down-sampling tariff
                        self.add_validation_error("ElectricTariff", "urdb_response",
                                                ("The time steps per hour in the energyweekdayschedule must be no greater "
                                                "than the Settings.time_steps_per_hour."))

        """
        Financial
        """
        if "Financial" in self.models.keys():
            if self.models["Financial"].__getattribute__("microgrid_upgrade_cost_fraction") == None:
                if self.models["Settings"].off_grid_flag==False:
                    self.models["Financial"].microgrid_upgrade_cost_fraction = 0.3
                else:
                    self.models["Financial"].microgrid_upgrade_cost_fraction = 0.0
        
        """
        ElectricStorage
        """
        if "ElectricStorage" in self.models.keys():
            if self.models["ElectricStorage"].__getattribute__("soc_init_fraction") == None:
                if self.models["Settings"].off_grid_flag==False:
                    self.models["ElectricStorage"].soc_init_fraction = 0.5
                else:
                    self.models["ElectricStorage"].soc_init_fraction = 1.0
            
            if self.models["ElectricStorage"].__getattribute__("can_grid_charge") == None:
                if self.models["Settings"].off_grid_flag==False:
                    self.models["ElectricStorage"].can_grid_charge = True
                else:
                    self.models["ElectricStorage"].can_grid_charge = False

        
        """
        ElectricUtility
        """
        if "ElectricUtility" in self.models.keys():
            for emissions_factor_input in ["emissions_factor_series_lb_CO2_per_kwh", 
                                            "emissions_factor_series_lb_NOx_per_kwh", 
                                            "emissions_factor_series_lb_SO2_per_kwh", 
                                            "emissions_factor_series_lb_PM25_per_kwh"]:
                if len(self.models["ElectricUtility"].__getattribute__(emissions_factor_input)) > 1:
                    self.clean_time_series("ElectricUtility", emissions_factor_input)

            if self.models["ElectricUtility"].outage_start_time_step:
                if self.models["ElectricUtility"].outage_start_time_step > max_ts:
                    self.add_validation_error("ElectricUtility", "outage_start_time_step",
                                              f"Value is greater than the max allowable ({max_ts})")
            if self.models["ElectricUtility"].outage_end_time_step:
                if self.models["ElectricUtility"].outage_end_time_step > max_ts:
                    self.add_validation_error("ElectricUtility", "outage_end_time_step",
                                              f"Value is greater than the max allowable ({max_ts})")
            if self.models["ElectricUtility"].outage_start_time_steps:
                max_start_time_step_input = max(self.models["ElectricUtility"].outage_start_time_steps)
                if max_start_time_step_input > max_ts:
                    self.add_validation_error("ElectricUtility", "outage_start_time_steps",
                                                f"Value is greater than the max allowable ({max_ts})")

                if self.models["ElectricUtility"].outage_durations:
                    if max_start_time_step_input + max(self.models["ElectricUtility"].outage_durations) - 1 > max_ts:
                        self.add_validation_error("ElectricUtility", "outage_durations",
                                                f"Value is greater than the max allowable ({max_ts} - {max_start_time_step_input})")
                    if not self.models["Site"].min_resil_time_steps:
                        self.models["Site"].min_resil_time_steps = max(self.models["ElectricUtility"].outage_durations)
                if self.models["ElectricUtility"].__getattribute__("cambium_levelization_years") == None:
                    self.models["ElectricUtility"].cambium_levelization_years = self.models["Financial"].analysis_years
        
        """
        CoolingLoad
        """
        if "CoolingLoad" in self.models.keys():

            if len(self.models["CoolingLoad"].thermal_loads_ton) > 0:
                self.clean_time_series("CoolingLoad", "thermal_loads_ton")
            elif len(self.models["CoolingLoad"].per_time_step_fractions_of_electric_load) > 0:
                self.clean_time_series("CoolingLoad", "per_time_step_fractions_of_electric_load")
            else:  # Using DOE commercial reference buildings
                if self.models["CoolingLoad"].doe_reference_name == None and not self.models["CoolingLoad"].blended_doe_reference_names:
                    assign_ref_buildings_from_electric_load(self, "CoolingLoad")                
            
        """
        ExistingBoiler
        """
        if "ExistingBoiler" in self.models.keys():

            self.clean_time_series("ExistingBoiler", "fuel_cost_per_mmbtu")

            if self.models["ExistingBoiler"].efficiency is None:
                if self.models["ExistingBoiler"].production_type == 'hot_water':
                    self.models["ExistingBoiler"].efficiency = 0.8
                else:
                    self.models["ExistingBoiler"].efficiency = 0.75
        
        """
        Boiler
        """
        if "Boiler" in self.models.keys():

            self.clean_time_series("Boiler", "fuel_cost_per_mmbtu")
        
        """
        ElectricLoad
        If user does not provide values, set defaults conditional on off-grid flag
        """
        '''
        If off-grid scenario, then always set critical load pct to 1.0, overriding any other value the user might have provided.
        If !off-grid scenario, if critical load pct is not specified in inputs, set it to 0.5. Otherwise, allow user specified pct.
        '''
        if self.models["Settings"].off_grid_flag==True:
            if self.models["ElectricLoad"].__getattribute__("operating_reserve_required_fraction") == None: # user provided no value
                self.models["ElectricLoad"].operating_reserve_required_fraction = 0.1
            
            if self.models["ElectricLoad"].__getattribute__("min_load_met_annual_fraction") == None: # user provided no value
                self.models["ElectricLoad"].min_load_met_annual_fraction = 0.99999

            self.models["ElectricLoad"].critical_load_fraction = 1.0
        else:
            self.models["ElectricLoad"].operating_reserve_required_fraction = 0.0
            self.models["ElectricLoad"].min_load_met_annual_fraction = 1.0

        """
        Generator
        If user does not provide values, set defaults conditional on off-grid flag
        """
        if "Generator" in self.models.keys():

            if self.models["Generator"].__getattribute__("om_cost_per_kw") == None:
                if self.models["Settings"].off_grid_flag==False:
                    self.models["Generator"].om_cost_per_kw = 20.0
                else:
                    self.models["Generator"].om_cost_per_kw = 10.0

            if self.models["Generator"].__getattribute__("installed_cost_per_kw") == None:
                if self.models["Settings"].off_grid_flag==False:
                    if self.models["Generator"].only_runs_during_grid_outage:
                        self.models["Generator"].installed_cost_per_kw = 650.0
                    else: 
                        self.models["Generator"].installed_cost_per_kw = 800.0
                else: 
                    self.models["Generator"].installed_cost_per_kw = 880.0

            if self.models["Generator"].__getattribute__("min_turn_down_fraction") == None:
                if self.models["Settings"].off_grid_flag==False:
                    self.models["Generator"].min_turn_down_fraction = 0.0
                else:
                    self.models["Generator"].min_turn_down_fraction = 0.15

            if self.models["Generator"].__getattribute__("replacement_year") == None:
                if self.models["Settings"].off_grid_flag==False:
                    self.models["Generator"].replacement_year = self.models["Financial"].analysis_years
                else:
                    self.models["Generator"].replacement_year = 10

            if self.models["Generator"].__getattribute__("replace_cost_per_kw") == None:
                if self.models["Settings"].off_grid_flag==False:
                    self.models["Generator"].replace_cost_per_kw = 0.0
                else:
                    self.models["Generator"].replace_cost_per_kw = self.models["Generator"].installed_cost_per_kw
        
        """
        DomesticHotWaterLoad
        """
        if "DomesticHotWaterLoad" in self.models.keys():
            self.clean_time_series("DomesticHotWaterLoad", "fuel_loads_mmbtu_per_hour")

            # If using DOE reference building input(s) (not fuel_load_mmbtu_per_hour), and no reference building(s) provided, assign to electric load building(s)
            if not self.models["DomesticHotWaterLoad"].fuel_loads_mmbtu_per_hour:
                if self.models["DomesticHotWaterLoad"].doe_reference_name == None and not self.models["DomesticHotWaterLoad"].blended_doe_reference_names:
                    assign_ref_buildings_from_electric_load(self, "DomesticHotWaterLoad")
        
        """
        SpaceHeatingLoad
        """
        if "SpaceHeatingLoad" in self.models.keys():
            self.clean_time_series("SpaceHeatingLoad", "fuel_loads_mmbtu_per_hour")

            # If using DOE reference building input(s) (not fuel_load_mmbtu_per_hour), and no reference building(s) provided, assign to electric load building(s)
            if not self.models["SpaceHeatingLoad"].fuel_loads_mmbtu_per_hour:
                if self.models["SpaceHeatingLoad"].doe_reference_name == None and not self.models["SpaceHeatingLoad"].blended_doe_reference_names:
                    assign_ref_buildings_from_electric_load(self, "SpaceHeatingLoad")
        
        def assign_ref_buildings_from_electric_load(self, load_to_assign):
            if self.models["ElectricLoad"].doe_reference_name != "":
                self.models[load_to_assign].__setattr__("doe_reference_name", self.models["ElectricLoad"].__getattribute__("doe_reference_name"))
            elif len(self.models["ElectricLoad"].blended_doe_reference_names) > 0:
                self.models[load_to_assign].__setattr__("blended_doe_reference_names", self.models["ElectricLoad"].__getattribute__("blended_doe_reference_names"))
                self.models[load_to_assign].__setattr__("blended_doe_reference_percents", self.models["ElectricLoad"].__getattribute__("blended_doe_reference_percents"))
            else:
                self.add_validation_error(load_to_assign, "doe_reference_name",
                                        f"Must provide DOE commercial reference building profiles either under {load_to_assign} or ElectricLoad")

        """
        ProcessHeatLaod
        """
        if "ProcessHeatLoad" in self.models.keys():
            self.clean_time_series("ProcessHeatLoad", "fuel_loads_mmbtu_per_hour")

        """
        Off-grid input keys validation
        """
        
        def validate_offgrid_keys(self):
            # From https://github.com/NatLabRockies/REopt.jl/blob/4b0fb7f6556b2b6e9a9a7e8fa65398096fb6610f/src/core/scenario.jl#L88         
            valid_input_keys_offgrid = ["PV", "Wind", "ElectricStorage", "Generator", "Settings", "Site", "Financial", "ElectricLoad", "ElectricTariff", "ElectricUtility", "Meta"]

            invalid_input_keys_offgrid = list(set(list(self.models.keys()))-set(valid_input_keys_offgrid))
            if 'APIMeta' in invalid_input_keys_offgrid:
                invalid_input_keys_offgrid.remove('APIMeta')

            if len(invalid_input_keys_offgrid) != 0:
                self.add_validation_error("Settings", "off_grid_flag",
                                            f"Currently, off-grid functionality doesn't allow modeling for following keys: ({invalid_input_keys_offgrid})")
        
        if self.models["Settings"].off_grid_flag==True:
            validate_offgrid_keys(self)

        """
        ExistingChiller - skip, no checks
        """

        """
        GHP - just check for ghpghx_inputs errors from /ghpghx app
        """
        if "GHP" in self.models.keys():
            if self.models["GHP"].__getattribute__("ghx_useful_life_years") < self.models["Financial"].__getattribute__("analysis_years"):
                self.models["GHP"].ghx_useful_life_years = self.models["Financial"].analysis_years
                
            if self.ghpghx_inputs_errors not in [None, []]:
                self.add_validation_error("GHP", "ghpghx_inputs", str(self.ghpghx_inputs_errors))

    def save(self):
        """
        Save all values to database
        :return: None
        """
        for model in self.models.values():
            model.save()
        for msg_type, msg in self.messages.items():
            Message.create(meta=self.models["APIMeta"], message_type=msg_type, message=msg).save()

    @property
    def is_valid(self):
        if self.validation_errors:
            return False
        return True

    def add_validation_error(self, model_key: str, attribute_name: str, msg: str):
        """
        Update self.validation_errors
        :param model_key: eg. "PV", "Wind", etc.
        :param attribute_name: model field name, eg. "latitude"
        :param msg: message to provide to user
        :return: None
        """
        if model_key not in self.validation_errors.keys():
            self.validation_errors[model_key] = {attribute_name: msg}
        else:
            self.validation_errors[model_key].update({attribute_name: msg})

    def add_resampling_message(self, model_key: str, attribute_name: str, msg: str):
        """
        Update self.resampling_messages
        :param model_key: eg. "PV", "Wind", etc.
        :param attribute_name: model field name, eg. "latitude"
        :param msg: message to provide to user
        :return: None
        """
        if model_key not in self.resampling_messages.keys():
            self.resampling_messages[model_key] = {attribute_name: msg}
        else:
            self.resampling_messages[model_key].update({attribute_name: msg})
    
    def clean_time_series(self, model_key: str, series_name: str):
        if self.models[model_key].__getattribute__(series_name):
            resampled_series, resampling_msg, err_msg = validate_time_series(
                self.models[model_key].__getattribute__(series_name),
                self.models["Settings"].time_steps_per_hour
            )
            if resampling_msg:
                self.models[model_key].__setattr__(series_name, resampled_series)
                self.add_resampling_message(model_key, series_name, resampling_msg)
            if err_msg:
                self.add_validation_error(model_key, series_name, err_msg)


def validate_time_series(series: list, time_steps_per_hour: int) -> Tuple[list, str, str]:
    """
    Used to check that an input time series has hourly, 30 minute, or 15 minute resolution and if the time series
    resolution matches the time_steps_per_hour (one of [1,2,4]).
    Time series that do not match the time_steps_per_hour are up- or down-sampled to match the time_steps_per_hour.
    Note that this is different from the v1 validate_8760 method, which only down-sampled and left it to each object
    (such as the LoadProfileBoilerFuel) to up-sample.
    This method is used in reoptjl/models.py, in models with time series values when their clean methods are called.
    :param series: list of floats
    :param time_steps_per_hour: int, one of [1,2,4]
    :return: (list, str, str) for the resampled series (if necessary) and the resampling message and exception
        respectively. Either message can be empty, i.e. "". For example, "" if no exception, o.w. an error message to
        append to the InputValidator.validation_errors.
    TODO: add resampling messages to messages returned to user
    TODO: does the resampling here match what is done in each of the time-series objects in v1?
    """
    n = len(series)
    length_list = [8760, 17520, 35040]
    if n not in length_list:
        return (series, "",
            (f"Invalid length. Samples must be hourly (8,760 samples), 30 minute (17,520 samples), "
             "or 15 minute (35,040 samples)"))
    
    time_steps_per_hour_in_series = n / 8760
    if time_steps_per_hour_in_series == time_steps_per_hour:
        return series, "", ""

    if time_steps_per_hour < time_steps_per_hour_in_series:
        resampling_msg = f"Downsampled to match time_steps_per_hour via average."
        index = pd.date_range('1/1/2000', periods=n, freq=f'{int(60/time_steps_per_hour_in_series)}min')
        s = pd.Series(series, index=index)
        s = s.resample(f'{int(60/time_steps_per_hour)}min').mean()
        return s.tolist(), resampling_msg, ""
    
    # time_steps_per_hour > time_steps_per_hour_in_series
    resampling_msg = f"Upsampled to match time_steps_per_hour via forward-fill."
    resampled_val = [x for x in series for _ in range(int(time_steps_per_hour/time_steps_per_hour_in_series))]
    return resampled_val, resampling_msg, ""


def lat_lon_in_windtoolkit(lat, lon):
    """
    Convert latitude, longitude into integer values for wind tool kit database.
    Modified from "indicesForCoord" in https://github.com/NatLabRockies/hsds-examples/blob/master/notebooks/01_introduction.ipynb
    Questions? Perr-Sauer, Jordan <Jordan.Perr-Sauer@nlr.gov>
    """
    projstring = """+proj=lcc +lat_1=30 +lat_2=60 
                    +lat_0=38.47240422490422 +lon_0=-96.0 
                    +x_0=0 +y_0=0 +ellps=sphere 
                    +units=m +no_defs """
    projectLcc = Proj(projstring)
    origin_ll = reversed((19.624062, -123.30661))
    origin = projectLcc(*origin_ll)
    point = projectLcc(lon, lat)
    x = int(round((point[0] - origin[0]) / 2000))
    y = int(round((point[1] - origin[1]) / 2000))
    y_max, x_max = (1602, 2976)
    if (x < 0) or (y < 0) or (x >= x_max) or (y >= y_max):
        return None
    return y, x
