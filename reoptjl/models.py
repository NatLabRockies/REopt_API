# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NREL/REopt_API/blob/master/LICENSE.
import math
from django.db import models
from django.db.models.fields import NOT_PROVIDED
from django.contrib.postgres.fields import *
# TODO rm picklefield from requirements.txt once v1 is retired (replaced with JSONfield)
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from picklefield.fields import PickledObjectField
import numpy
from reoptjl.urdb_rate_validator import URDB_RateValidator,URDB_LabelValidator
import copy
import logging
import os
import json
from ghpghx.models import GHPGHXInputs
from ghpghx.models import ModelManager as ghpModelManager

log = logging.getLogger(__name__)

"""
Guidance:
- start all Model fields with required fields (do not need to include `blank` b/c the default value of blank is False. Set blank=True to allow field to be blank)
- TextField and CharField should not have null=True
- description: use square brackets for units, eg. [dollars per kWh]
- Output models need to have null=True, blank=True for cases when results are not generated 
"""
MAX_BIG_NUMBER = 1.0e8
MAX_INCENTIVE = 1.0e10
MAX_YEARS = 75


class MACRS_YEARS_CHOICES(models.IntegerChoices):
    ZERO = 0
    FIVE = 5
    SEVEN = 7

FUEL_DEFAULTS = {
    "fuel_renewable_energy_fraction" : {
        "natural_gas" : 0.0,
        "landfill_bio_gas" : 1.0,
        "propane" : 0.0,
        "diesel_oil" : 0.0
    },
    "emissions_factor_lb_CO2_per_mmbtu" : {
        "natural_gas" : 117.03,
        "landfill_bio_gas" : 115.38,
        "propane" : 139.16,
        "diesel_oil" : 163.61
    },
    "emissions_factor_lb_NOx_per_mmbtu" : {
        "natural_gas" : 0.09139,
        "landfill_bio_gas": 0.14,
        "propane" : 0.15309,
        "diesel_oil" : 0.56
    },
    "emissions_factor_lb_SO2_per_mmbtu" : {
        "natural_gas" : 0.000578592,
        "landfill_bio_gas" : 0.045,
        "propane" : 0.0,
        "diesel_oil" : 0.28897737
    },
    "emissions_factor_lb_PM25_per_mmbtu" : {
        "natural_gas" : 0.007328833,
        "landfill_bio_gas" : 0.02484,
        "propane" : 0.009906836,
        "diesel_oil" : 0.0
    }
}

EMISSIONS_DECREASE_DEFAULTS = { # year over year decrease in grid emissions rate
    "CO2e" : 0.0459,
    "NOx" : 0.0459,
    "SO2" : 0.0459,
    "PM25" : 0.0459
}

WIND_COST_DEFAULTS = { # size_class_to_installed_cost 
    "residential" : 7692.0,
    "commercial" : 5776.0,
    "medium" : 3807.0,
    "large" : 2896.0
}

def at_least_one_set(model, possible_sets):
    """
    Check if at least one set of possible_sets are defined in the Model.dict
    :param model: BaseModel.dict
    :param possible_sets: list of lists (of str)
    :return: Bool, True if the BaseModel.dict includes non-empty or non-null values for at least one set of keys in
        possible_sets
    """
    case = False
    for list_of_keys in possible_sets:
        if all(model.get(key) not in [None, "", []] for key in list_of_keys):
            case = True
            break
    return case


class BaseModel(object):

    @property
    def dict(self):
        """
        Serialize Django Model.__dict__
        NOTE: to get correct field types you must run self.clean_fields() first (eg. convert int to float)
        :return: dict
        """
        d = copy.deepcopy(self.__dict__)
        d.pop("_state", None)
        d.pop("id", None)
        d.pop("basemodel_ptr_id", None)
        d.pop("meta_id", None)
        return d

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        return obj

    def info_dict(self):
        """
        :return: dict with keys for each model field and sub-dicts for the settings for each key, such as help_text
        """
        d = dict()
        possible_sets = getattr(self, "possible_sets", None)
        if possible_sets is not None:
            d["possible_sets"] = possible_sets

        for field in self._meta.fields:
            if field.attname.endswith("id"): continue
            d[field.attname] = dict()
            if "Outputs" not in getattr(self, "key", ""):
                d[field.attname]["required"] = not field.blank and field.default == NOT_PROVIDED
            if field.choices is not None:
                d[field.attname]["choices"] = [t[0] for t in field.choices]
            if not field.default == NOT_PROVIDED and field.default != list:
                try:
                    d[field.attname]["default"] = field.default.value
                except:
                    d[field.attname]["default"] = field.default
            if len(field.help_text) > 0:
                d[field.attname]["help_text"] = field.help_text
            for val in field.validators:
                if val.limit_value not in (-2147483648, 2147483647):  # integer limits
                    d[field.attname][val.code] = val.limit_value
        return d
    

class APIMeta(BaseModel, models.Model):
    """
    Values created by API for each scenario (no user input values). 
    Returned from job/<run_uuid>/results at the top level.
    """
    key = "APIMeta"

    run_uuid = models.UUIDField(unique=True)
    api_version = models.IntegerField(default=2)
    user_uuid = models.TextField(
        blank=True,
        default="",
        help_text="The assigned unique ID of a signed in REopt user."
    )
    webtool_uuid = models.TextField(
        blank=True,
        default="",
        help_text=("The unique ID of a scenario created by the REopt Lite Webtool. Note that this ID can be shared by "
                   "several REopt Lite API Scenarios (for example when users select a 'Resilience' analysis more than "
                   "one REopt API Scenario is created).")
    )
    job_type = models.TextField(
        default='developer.nrel.gov'
    )
    status = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    reopt_version = models.TextField(
        blank=True,
        null=True,
        default="",
        help_text="Version number of the Julia package for REopt that is used to solve the problem."
    )
    api_key = models.TextField(
        blank=True,
        default="",
        help_text="NREL Developer API key of the user"
    )
    portfolio_uuid = models.TextField(
        blank=True,
        default="",
        help_text=("The unique ID of a portfolio (set of associated runs) created by the REopt Webtool. Note that this ID can be shared by "
                   "several REopt API Scenarios and one user can have one-to-many portfolio_uuid tied to them.")
    )

class UserUnlinkedRuns(models.Model):
    run_uuid = models.UUIDField(unique=True)
    user_uuid = models.UUIDField(unique=False)

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        obj.save()
        return obj

class PortfolioUnlinkedRuns(models.Model):
    portfolio_uuid = models.UUIDField(unique=False)
    user_uuid = models.UUIDField(unique=False)
    run_uuid = models.UUIDField(unique=True)

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        obj.save()
        return obj

class UserProvidedMeta(BaseModel, models.Model):
    """
    User provided values that are not necessary for running REopt
    """
    key = "Meta"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="UserProvidedMeta"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional user defined description."
    )
    address = models.TextField(
        blank=True,
        help_text="Optional user defined address (street address, city, state or zip code)"
    )

class Settings(BaseModel, models.Model):
    key = "Settings"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="Settings"
    )

    class TIME_STEP_CHOICES(models.IntegerChoices):
        ONE = 1
        TWO = 2
        FOUR = 4

    timeout_seconds = models.IntegerField(
        default=600,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(1200)
        ],
        help_text="The number of seconds allowed before the optimization times out."
    )

    time_steps_per_hour = models.IntegerField(
        default=TIME_STEP_CHOICES.ONE,
        choices=TIME_STEP_CHOICES.choices,
        help_text="The number of time steps per hour in the REopt model."
    )

    optimality_tolerance = models.FloatField(
        default=0.001,
        validators=[
            MinValueValidator(5.0e-6),
            MaxValueValidator(0.20)
        ],
        help_text=("The threshold for the difference between the solution's objective value and the best possible "
                   "value at which the solver terminates")
    )

    add_soc_incentive = models.BooleanField(
        default=True,
        blank=True,
        help_text=("If True, then a small incentive to keep the battery's state of charge high is added to the "
                   "objective of the optimization.")
    )

    run_bau = models.BooleanField(
        blank=True,
        null=True,
        default=True,
        help_text=("If True then the Business-As-Usual scenario is also solved to provide additional outputs such as "
                   "the NPV and BAU costs.")
    )
    include_climate_in_objective = models.BooleanField(
        default=False,
        blank=True,
        help_text=("If True, then climate costs of CO2 emissions are included in the model's objective function.")
    )
    include_health_in_objective = models.BooleanField(
        default=False,
        blank=True,
        help_text=("If True, then health costs of NOx, SO2, and PM2.5 emissions are included in the model's objective function.")
    )

    off_grid_flag = models.BooleanField(
        default=False,
        blank=True,
        help_text=("Set to true to enable off-grid analyses, not connected to a bulk power system.")
    )

    class SOLVERS(models.TextChoices):
        HIGHS = "HiGHS"
        CBC = "Cbc"
        SCIP = "SCIP"
        XPRESS = "Xpress"

    solver_name = models.TextField(
        blank=True,
        default=SOLVERS.HIGHS,
        choices=SOLVERS.choices,
        help_text=("Solver used for REopt.jl. Options include HiGHS, Cbc, SCIP, and Xpress")
    )

    def clean(self):
        if self.off_grid_flag:
            self.run_bau = False

class SiteInputs(BaseModel, models.Model):
    key = "Site"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="SiteInputs",
        primary_key=True
    )

    class SECTORS(models.TextChoices):
        COMMERCIAL = 'commercial/industrial'
        FEDERAL = 'federal'

    class FEDERAL_PROCUREMENT_TYPES(models.TextChoices):
        FEDOWNED_DIRPURCH = 'fedowned_dirpurch'
        FEDOWNED_THIRD_PARTY = 'fedowned_thirdparty'
        PRIVATEOWNED_THIRD_PARTY = 'privateowned_thirdparty'

    latitude = models.FloatField(
        validators=[
            MinValueValidator(-90),
            MaxValueValidator(90)
        ],
        help_text="The latitude of the site in decimal degrees."
    )
    longitude = models.FloatField(
        validators=[
            MinValueValidator(-180),
            MaxValueValidator(180)
        ],
        help_text="The longitude of the site in decimal degrees."
    )
    land_acres = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1000000)
        ],
        null=True, blank=True,
        help_text="Land area in acres available for PV panel siting"
    )
    roof_squarefeet = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1000000000)
        ],
        null=True, blank=True,
        help_text="Area of roof in square feet available for PV siting"
    )
    min_resil_time_steps = models.IntegerField(
        validators=[
            MinValueValidator(0)
        ],
        null=True, 
        blank=True,
        help_text="The minimum number consecutive timesteps that load must be fully met once an outage begins. "
                    "Only applies to multiple outage modeling using inputs outage_start_time_steps and outage_durations."
                    "If no value is provided, will default to max([ElectricUtility].outage_durations)."
    )
    # don't provide mg_tech_sizes_equal_grid_sizes in the API, effectively force it to true (the REopt.jl default)

    sector = models.TextField(
        choices=SECTORS.choices,
        blank=True,
        null=False,
        default=SECTORS.COMMERCIAL,
        help_text=("The sector of the site. Options: ['federal', 'commercial/industrial']")
    )
    federal_sector_state = models.TextField(
        # not creating choices b/c hoping to get rid of this input ASAP and use lat/long instead
        blank=True,
        null=False,
        default="",
        help_text=("The state where the site is located, if the site's sector is 'federal'. State can be written out or abbreviated.")
    )
    federal_procurement_type = models.TextField(
        choices=FEDERAL_PROCUREMENT_TYPES.choices,
        blank=True,
        null=False,
        default="",
        help_text=("The capital procurement type if the site's sector is 'federal'. Options: ['fedowned_dirpurch', 'fedowned_thirdparty', 'privateowned_thirdparty']")
    )
    CO2_emissions_reduction_min_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        null=True, blank=True,
        help_text="Minimum allowed percentage reduction of CO2 emissions, relative to the business-as-usual case, over the financial lifecycle of the project."
    )
    CO2_emissions_reduction_max_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        null=True, blank=True,
        help_text="Maximum allowed percentage reduction of CO2 emissions, relative to the business-as-usual case, over the financial lifecycle of the project."
    )
    renewable_electricity_min_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10)
        ],
        null=True, blank=True,
        help_text="Minimum allowed percentage of site electric consumption met by renewable energy on an annual basis."
    )
    renewable_electricity_max_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10)
        ],
        null=True, blank=True,
        help_text="Maximum allowed percentage of site electric consumption met by renewable energy on an annual basis."
    )

    include_grid_renewable_fraction_in_RE_constraints = models.BooleanField(
        default=False,
        blank=True,
        help_text=("If True, then the renewable energy content of energy from the grid is included in any min or max renewable energy requirements.")
    )

    include_exported_elec_emissions_in_total = models.BooleanField(
        default=True,
        blank=True,
        help_text=("If True, then energy exported to the grid is included in emissions calculations.")
    )
    include_exported_renewable_electricity_in_total = models.BooleanField(
        default=True,
        blank=True,
        help_text=("If True, then renewable energy exported to the grid is counted in renewable electricity percent calculation.")
    )
    outdoor_air_temperature_degF = ArrayField(
        models.FloatField(
            null=True,
            blank=True
        ),
        default=list,
        null=True,
        blank=True,
        help_text=("The outdoor air (dry-bulb) temperature in degrees Fahrenheit as determined by the site's location TMY3 data from the PVWatts call or user input. This is used for GHP COP and ASHP COP and CF values based on the default or custom mapping of those.")
    )

    def clean(self):
        if self.sector == self.SECTORS.FEDERAL:
            error_messages = {}
            if self.federal_procurement_type == "":
                error_messages["required inputs"] = "If sector is federal, must provide federal_procurement_type."
            if self.federal_sector_state == "":
                error_messages["required inputs"] = "If sector is federal, must provide federal_sector_state."
            if error_messages:
                raise ValidationError(error_messages)

class SiteOutputs(BaseModel, models.Model):
    key = "SiteOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="SiteOutputs",
        primary_key=True
    )

    annual_onsite_renewable_electricity_kwh = models.FloatField(
        null=True, blank=True,
        help_text=(
                  "Electricity consumption (incl. electric heating/cooling loads) that is derived from on-site renewable resource generation."
                  "Calculated as total annual RE electric generation, minus storage losses and curtailment, with the user selecting whether exported renewable generation is included). "
                  )
    )
    onsite_renewable_electricity_fraction_of_elec_load = models.FloatField(
        null=True, blank=True,
        help_text=(
                  "Portion of electricity consumption (incl. electric heating/cooling loads) that is derived from on-site renewable resource generation."
                  "Calculated as total annual RE electric generation, minus storage losses and curtailment, with the user selecting whether exported renewable generation is included, "
                  "divided by total annual electric consumption."
                  )
    )
    onsite_renewable_energy_fraction_of_total_load = models.FloatField(
        null=True, blank=True,
        help_text=(
                  "Portion of annual total energy consumption that is derived from on-site renewable resource generation."
                  "The numerator is calculated as total annual RE electricity consumption (calculation described for annual_onsite_renewable_electricity_kwh output),"
                  "plus total annual thermal energy content of steam/hot water generated from renewable fuels (non-electrified heat loads)."
                  "The thermal energy content is calculated as total energy content of steam/hot water generation from renewable fuels,"
                  "minus waste heat generated by renewable fuels, minus any applicable hot water thermal energy storage efficiency losses."
                  "The denominator is calculated as total annual electricity consumption plus total annual thermal steam/hot water load."
                  )
    )
    onsite_and_grid_renewable_electricity_fraction_of_elec_load  = models.FloatField(
        null=True, blank=True,
        help_text=(
                  "Calculation is the same as onsite_renewable_electricity_fraction_of_elec_load, but additionally includes the renewable energy"
                  "content of grid-purchased electricity, accounting for any battery efficiency losses."
                  )
    )
    onsite_and_grid_renewable_energy_fraction_of_total_load = models.FloatField(
        null=True, blank=True,
        help_text=(
                  "Calculation is the same as onsite_renewable_energy_fraction_of_total_load, but additionally includes the renewable energy"
                  "content of grid-purchased electricity, accounting for any battery efficiency losses."
                  )
    )
    annual_emissions_tonnes_CO2 = models.FloatField(
        null=True, blank=True,
        help_text="Average annual total tons of emissions associated with the site's grid-purchased electricity and on-site fuel consumption."
    )
    annual_emissions_tonnes_NOx = models.FloatField(
        null=True, blank=True,
        help_text="Average annual total tons of emissions associated with the site's grid-purchased electricity and on-site fuel consumption."
    )
    annual_emissions_tonnes_SO2 = models.FloatField(
        null=True, blank=True,
        help_text="Average annual total tons of emissions associated with the site's grid-purchased electricity and on-site fuel consumption."
    )
    annual_emissions_tonnes_PM25 = models.FloatField(
        null=True, blank=True,
        help_text="Average annual total tons of emissions associated with the site's grid-purchased electricity and on-site fuel consumption."
    )
    annual_emissions_from_fuelburn_tonnes_CO2 = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of CO2e emissions associated with the site's onsite fuel burn in an average year."
    )
    annual_emissions_from_fuelburn_tonnes_NOx = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of NOx emissions associated with the site's onsite fuel burn in an average year."
    )
    annual_emissions_from_fuelburn_tonnes_SO2 = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of SO2 emissions associated with the site's onsite fuel burn in an average year."
    )
    annual_emissions_from_fuelburn_tonnes_PM25 = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of PM2.5 emissions associated with the site's onsite fuel burn in an average year."
    )
    lifecycle_emissions_tonnes_CO2 = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of CO2e emissions associated with the site's energy consumption over the analysis period."
    )
    lifecycle_emissions_tonnes_NOx = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of NOx emissions associated with the site's energy consumption over the analysis period."
    )
    lifecycle_emissions_tonnes_SO2 = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of SO2 emissions associated with the site's energy consumption over the analysis period."
    )
    lifecycle_emissions_tonnes_PM25 = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of PM2.5 emissions associated with the site's energy consumption over the analysis period."
    )
    lifecycle_emissions_from_fuelburn_tonnes_CO2 = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of CO2e emissions associated with the site's onsite fuel burn over the analysis period."
    )
    lifecycle_emissions_from_fuelburn_tonnes_NOx = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of NOx emissions associated with the site's onsite fuel burn over the analysis period."
    )
    lifecycle_emissions_from_fuelburn_tonnes_SO2 = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of SO2 emissions associated with the site's onsite fuel burn over the analysis period."
    )
    lifecycle_emissions_from_fuelburn_tonnes_PM25 = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of PM2.5 emissions associated with the site's onsite fuel burn over the analysis period."
    )
    annual_onsite_renewable_electricity_kwh_bau = models.FloatField(
        null=True, blank=True,
        help_text=(
                  "Electricity consumption (incl. electric heating/cooling loads) that is derived from on-site renewable resource generation in the BAU case."
                  "Calculated as total RE electric generation in the BAU case, minus storage losses and curtailment, with the user selecting whether exported renewable generation is included). "
                  )
    )
    onsite_renewable_electricity_fraction_of_elec_load_bau = models.FloatField(
        null=True, blank=True,
        help_text=(
                  "Electricity consumption (incl. electric heating/cooling loads) that is derived from on-site renewable resource generation in the BAU case."
                  "Calculated as total annual RE electric generation in the BAU case, minus storage losses and curtailment, with the user selecting whether exported renewable generation is included, "
                  "divided by total annual electric consumption."
                  )
    )
    onsite_renewable_energy_fraction_of_total_load_bau = models.FloatField(
        null=True, blank=True,
        help_text=(
                  "Portion of annual total energy consumption that is derived from on-site renewable resource generation in the BAU case."
                  "The numerator is calculated as total annual RE electricity consumption (calculation described for annual_onsite_renewable_electricity_kwh_bau output),"
                  "plus total annual thermal energy content of steam/hot water generated from renewable fuels (non-electrified heat loads)."
                  "The thermal energy content is calculated as total energy content of steam/hot water generation from renewable fuels,"
                  "minus waste heat generated by renewable fuels, minus any applicable hot water thermal energy storage efficiency losses."
                  "The denominator is calculated as total annual electricity consumption plus total annual thermal steam/hot water load."
                  )
    )
    onsite_and_grid_renewable_electricity_fraction_of_elec_load_bau = models.FloatField(
        null=True, blank=True,
        help_text=(
                  "Calculation is the same as onsite_renewable_electricity_fraction_of_elec_load_bau, but additionally includes the renewable energy"
                  "content of grid-purchased electricity, accounting for any battery efficiency losses."
                  )
    )
    onsite_and_grid_renewable_energy_fraction_of_total_load_bau = models.FloatField(
        null=True, blank=True,
        help_text=(
                  "Calculation is the same as onsite_renewable_energy_fraction_of_total_load_bau, but additionally includes the renewable energy"
                  "content of grid-purchased electricity, accounting for any battery efficiency losses."
                  )
    )
    annual_emissions_tonnes_CO2_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of CO2e emissions associated with the site's energy consumption in an average year in the BAU case."
    )
    annual_emissions_tonnes_NOx_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of NOx emissions associated with the site's energy consumption in an average year in the BAU case."
    )
    annual_emissions_tonnes_SO2_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of SO2 emissions associated with the site's energy consumption in an average year in the BAU case."
    )
    annual_emissions_tonnes_PM25_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of PM2.5 emissions associated with the site's energy consumption in an average year in the BAU case."
    )
    annual_emissions_from_fuelburn_tonnes_CO2_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of CO2 emissions associated with the site's onsite fuel burn in an average year in the BAU case."
    )
    annual_emissions_from_fuelburn_tonnes_NOx_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of NOx emissions associated with the site's onsite fuel burn in an average year in the BAU case."
    )
    annual_emissions_from_fuelburn_tonnes_SO2_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of SO2 emissions associated with the site's onsite fuel burn in an average year in the BAU case."
    )
    annual_emissions_from_fuelburn_tonnes_PM25_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of PM2.5 emissions associated with the site's onsite fuel burn in an average year in the BAU case."
    )
    lifecycle_emissions_tonnes_CO2_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of CO2e emissions associated with the site's energy consumption over the analysis period in the BAU case."
    )
    lifecycle_emissions_tonnes_NOx_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of NOx emissions associated with the site's energy consumption over the analysis period in the BAU case."
    )
    lifecycle_emissions_tonnes_SO2_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of SO2 emissions associated with the site's energy consumption over the analysis period in the BAU case."
    )
    lifecycle_emissions_tonnes_PM25_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of PM2.5 emissions associated with the site's energy consumption over the analysis period in the BAU case."
    )
    lifecycle_emissions_from_fuelburn_tonnes_CO2_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of CO2e emissions associated with the site's onsite fuel burn over the analysis period in the BAU case."
    )
    lifecycle_emissions_from_fuelburn_tonnes_NOx_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of NOx emissions associated with the site's onsite fuel burn over the analysis period in the BAU case."
    )
    lifecycle_emissions_from_fuelburn_tonnes_SO2_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of SO2 emissions associated with the site's onsite fuel burn over the analysis period in the BAU case."
    )
    lifecycle_emissions_from_fuelburn_tonnes_PM25_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total tons of PM2.5 emissions associated with the site's onsite fuel burn over the analysis period in the BAU case."
    )
    lifecycle_emissions_reduction_CO2_fraction = models.FloatField(
        null=True, blank=True,
        help_text="Percent reduction in total pounds of carbon dioxide emissions in the optimal case relative to the BAU case"
    )

class FinancialInputs(BaseModel, models.Model):
    key = "Financial"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="FinancialInputs",
        primary_key=True
    )

    analysis_years = models.IntegerField(
        default=25,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(75)
        ],
        blank=True,
        help_text="Analysis period in years. Must be integer."
    )
    elec_cost_escalation_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Annual nominal utility electricity cost escalation rate."
    )
    offtaker_discount_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text=("Nominal energy offtaker discount rate. In single ownership model the offtaker is also the "
                   "generation owner.")
    )
    offtaker_tax_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(0.999)
        ],
        blank=True,
        null=True,
        help_text="Host tax rate"
    )
    om_cost_escalation_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Annual nominal O&M cost escalation rate"
    )
    owner_discount_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text=("Nominal generation owner discount rate. Used for two party financing model. In two party ownership "
                   "model the offtaker does not own the generator(s).")
    )
    owner_tax_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(0.999)
        ],
        blank=True,
        null=True,
        help_text=("Generation owner tax rate. Used for two party financing model. In two party ownership model the "
                   "offtaker does not own the generator(s).")
    )
    third_party_ownership = models.BooleanField(
        blank=True,
        null=True,
        help_text=("Specify if ownership model is direct ownership or two party. In two party model the offtaker does "
                   "not purcharse the generation technologies, but pays the generation owner for energy from the "
                   "generator(s).")
    )
    value_of_lost_load_per_kwh = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e6)
        ],
        blank=True,
        help_text=("Value placed on unmet site load during grid outages. Units are US dollars per unmet kilowatt-hour. "
                   "The value of lost load (VoLL) is used to determine outage costs by multiplying VoLL by unserved load for each outage start time and duration. "
                   "Only applies when modeling outages using "
                   "the outage_start_time_steps, outage_durations, and outage_probabilities inputs, and do not "
                   "apply when modeling a single outage using outage_start_time_step and outage_end_time_step.")
    )
    microgrid_upgrade_cost_fraction = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text=("Additional cost, in percent of non-islandable capital costs, to make a distributed energy system "
                   "islandable from the grid and able to serve critical loads. Includes all upgrade costs such as "
                   "additional labor and critical load panels. Costs apply only when modeling outages using "
                   "the outage_start_time_steps, outage_durations, and outage_probabilities inputs, and do not "
                   "apply when modeling a single outage using outage_start_time_step and outage_end_time_step.")
    )
    offgrid_other_capital_costs = models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1e6)
            ],
            blank=True,
            null=True,
            default=0.0,
            help_text=("Only applicable when off_grid_flag is true, applies a straight-line depreciation to this capex cost, reducing taxable income.")
    )
    offgrid_other_annual_costs = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e6)
        ],
        blank=True,
        null=True,
        default=0.0,
        help_text=("Only applicable when off_grid_flag is true. These per year costs are considered tax deductible for owner.")
    )
    min_initial_capital_costs_before_incentives = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e12)
        ],
        blank=True,
        null=True,
        help_text=("Minimum up-front capital cost for all technologies, excluding replacement costs and incentives [$].")
    )
    max_initial_capital_costs_before_incentives = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e12)
        ],
        blank=True,
        null=True,
        help_text=("Maximum up-front capital cost for all technologies, excluding replacement costs and incentives [$].")
    )
    CO2_cost_per_tonne = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e6)
        ],
        blank=True,
        null=True,
        default=51.0,
        help_text=("Social Cost of CO2 in the first year of the analysis. Units are US dollars per metric ton of CO2. The default of $51/t is the 2020 value (using a 3 pct discount rate) estimated by the U.S. Interagency Working Group on Social Cost of Greenhouse Gases.")
    )
    CO2_cost_escalation_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        default=0.042173,
        help_text=("Annual nominal Social Cost of CO2 escalation rate (as a decimal).")
    )
    NOx_grid_cost_per_tonne = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e6)
        ],
        blank=True,
        null=True,
        help_text=("Public health cost of NOx emissions from grid electricity in the first year of the analysis. Units are US dollars per metric ton. Default values for the U.S. obtained from the EASIUR model.")
    )
    SO2_grid_cost_per_tonne = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e6)
        ],
        blank=True,
        null=True,
        help_text=("Public health cost of SO2 emissions from grid electricity in the first year of the analysis. Units are US dollars per metric ton. Default values for the U.S. obtained from the EASIUR model.")
    )
    PM25_grid_cost_per_tonne = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e6)
        ],
        blank=True,
        null=True,
        help_text=("Public health cost of PM2.5 emissions from grid electricity in the first year of the analysis. Units are US dollars per metric ton. Default values for the U.S. obtained from the EASIUR model.")
    )
    NOx_onsite_fuelburn_cost_per_tonne = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e6)
        ],
        blank=True,
        null=True,
        help_text=("Public health cost of NOx from onsite fuelburn in the first year of the analysis. Units are US dollars per metric ton. Default values for the U.S. obtained from the EASIUR model.")
    )
    SO2_onsite_fuelburn_cost_per_tonne = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e6)
        ],
        blank=True,
        null=True,
        help_text=("Public health cost of SO2 from onsite fuelburn in the first year of the analysis. Units are US dollars per metric ton. Default values for the U.S. obtained from the EASIUR model.")
    )
    PM25_onsite_fuelburn_cost_per_tonne = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e6)
        ],
        blank=True,
        null=True,
        help_text=("Public health cost of PM2.5 from onsite fuelburn in the first year of the analysis. Units are US dollars per metric ton. Default values for the U.S. obtained from the EASIUR model.")
    )
    NOx_cost_escalation_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text=("Annual nominal escalation rate of the public health cost of 1 tonne of NOx emissions (as a decimal). The default value is calculated from the EASIUR model for a height of 150m.")
    )
    SO2_cost_escalation_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text=("Annual nominal escalation rate of the public health cost of 1 tonne of SO2 emissions (as a decimal). The default value is calculated from the EASIUR model for a height of 150m.")
    )
    PM25_cost_escalation_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text=("Annual nominal escalation rate of the public health cost of 1 tonne of PM2.5 emissions (as a decimal). The default value is calculated from the EASIUR model for a height of 150m.")
    )
    generator_fuel_cost_escalation_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text=("Annual nominal boiler fuel cost escalation rate")
    )    
    existing_boiler_fuel_cost_escalation_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text=("Annual nominal existing boiler fuel cost escalation rate")
    )
    boiler_fuel_cost_escalation_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text=("Annual nominal boiler fuel cost escalation rate")
    )
    chp_fuel_cost_escalation_rate_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text=("Annual nominal chp fuel cost escalation rate")
    )

    def clean(self):
        if not self.third_party_ownership:
            self.owner_tax_rate_fraction = self.offtaker_tax_rate_fraction
            self.owner_discount_rate_fraction = self.offtaker_discount_rate_fraction


class FinancialOutputs(BaseModel, models.Model):
    key = "FinancialOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="FinancialOutputs",
        primary_key=True
    )

    lcc = models.FloatField(
        null=True, blank=True,
        help_text="Optimal lifecycle cost"
    )
    lcc_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual lifecycle cost"
    )
    npv = models.FloatField(
        null=True, blank=True,
        help_text="Net present value of savings realized by the project"
    )
    lifecycle_capital_costs_plus_om_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Capital cost for all technologies plus present value of operations and maintenance over anlaysis period"
    )
    lifecycle_om_costs_before_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business-as-usual present value of operations and maintenance over analysis period",
    )
    lifecycle_capital_costs = models.FloatField(
        null=True, blank=True,
        help_text="Net capital costs for all technologies, in present value, including replacement costs and incentives."
    )
    lifecycle_capital_costs_bau = models.FloatField(
        null=True, blank=True,
        help_text="Net capital costs for BAU technologies such as ExistingBoiler and ExistingChiller, in present value."
    )    
    microgrid_upgrade_cost = models.FloatField(
        null=True, blank=True,
        help_text=("Cost to make a distributed energy system islandable from the grid. Determined by multiplying the "
            "total capital costs of resultant energy systems from REopt (such as PV and Storage system) with the input "
            "value for microgrid_upgrade_cost_fraction (which defaults to 0).")
    )
    initial_capital_costs = models.FloatField(
        null=True, blank=True,
        help_text="Up-front capital costs for all technologies, in present value, excluding replacement costs and incentives."
    )
    initial_capital_costs_after_incentives = models.FloatField(
        null=True, blank=True,
        help_text="Up-front capital costs for all technologies, in present value, excluding replacement costs, including incentives."
    )
    initial_capital_costs_after_incentives_bau = models.FloatField(
        null=True, blank=True,
        help_text="Up-front capital costs for BAU technologies such as ExistingBoiler and ExistingChiller, in present value."
    )    
    capital_costs_after_non_discounted_incentives_without_macrs = models.FloatField(
        null=True, blank=True,
        help_text="Capital costs for all technologies, including present value of replacement costs and incentives except for MACRS."
    )
    capital_costs_after_non_discounted_incentives = models.FloatField(
        null=True, blank=True,
        help_text="Capital costs for all technologies, including present value of replacement costs and all non-discounted incentives including MACRS."
    )  
    om_and_replacement_present_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Net O&M and replacement costs in present value, after-tax."
    )
    lifecycle_om_costs_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Life cycle operations and maintenance cost over analysis period before tax."
    )
    year_one_om_costs_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Year one operations and maintenance cost before tax."
    )
    year_one_om_costs_before_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Year one operations and maintenance cost before tax in the BAU case."
    )
    year_one_om_costs_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Year one operations and maintenance cost after tax."
    )
    year_one_om_costs_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Year one operations and maintenance cost after tax in the BAU case."
    )    
    year_one_fuel_cost_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Year one fuel cost of all combined fuel-burning techs, before tax."
    )
    year_one_fuel_cost_before_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Year one fuel cost of all combined fuel-burning techs, before tax in the BAU case."
    )        
    year_one_fuel_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Year one fuel cost of all combined fuel-burning techs, after tax."
    )
    year_one_fuel_cost_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Year one fuel cost of all combined fuel-burning techs, after tax in the BAU case."
    )
    year_one_chp_standby_cost_before_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Year one CHP standby charges, before tax.")
    )
    year_one_chp_standby_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Year one CHP standby charges, after tax.")
    )
    year_one_total_operating_cost_before_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Year one total operating (electricity, fuel, O&M) costs, before tax.")
    )
    year_one_total_operating_cost_before_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Year one total operating (electricity, fuel, O&M) costs, before tax in the BAU case.")
    )
    year_one_total_operating_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Year one total operating (electricity, fuel, O&M) costs, after tax.")
    )
    year_one_total_operating_cost_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Year one total operating (electricity, fuel, O&M) costs, after tax in the BAU case.")
    )
    year_one_total_operating_cost_savings_before_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Year one total operating (electricity, fuel, O&M) cost savings compared to BAU case, before tax.")
    )
    year_one_total_operating_cost_savings_after_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Year one total operating (electricity, fuel, O&M) cost savings compared to BAU case, after tax.")
    )
    simple_payback_years = models.FloatField(
        null=True, blank=True,
        help_text=("Number of years until the cumulative annual cashflows turn positive. "
            "If the cashflows become negative again after becoming positive (i.e. due to battery repalcement costs)"
            " then simple payback is increased by the number of years that the cash flow "
            "is negative beyond the break-even year.")
    )
    internal_rate_of_return = models.FloatField(
        null=True, blank=True,
        help_text=("internal Rate of Return of the cost-optimal system. In two-party cases the "
                   "developer discount rate is used in place of the offtaker discount rate.")
    )
    net_present_cost = models.FloatField(
        null=True, blank=True,
        help_text=("Present value of the total costs incurred by the third-party owning and operating the "
                    "distributed energy resource assets.")
    )
    annualized_payment_to_third_party = models.FloatField(
        null=True, blank=True,
        help_text=("The annualized amount the host will pay to the third-party owner over the life of the project.")
    )
    offtaker_annual_free_cashflows = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list, blank=True,
        help_text=("Annual free cashflows for the host in the optimal case for all analysis years, "
                    "including year 0. Future years have not been discounted to account for the time value of money.")
    )
    offtaker_discounted_annual_free_cashflows = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list, blank=True,
        help_text=("Annual discounted free cashflows for the host in the optimal case for all analysis years, "
                    "including year 0. Future years have been discounted to account for the time value of money.")
    )
    offtaker_annual_free_cashflows_bau = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list, blank=True,
        help_text=("Annual free cashflows for the host in the business-as-usual case for all analysis years, "
                    "including year 0. Future years have not been discounted to account for the time value of "
                    "money. Only calculated in the non-third-party case.")
    )
    offtaker_discounted_annual_free_cashflows_bau = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list, blank=True,
        null=True,
        help_text=("Annual discounted free cashflow for the host in the business-as-usual case for all analysis "
                   "years, including year 0. Future years have been discounted to account for the time value of "
                   "money. Only calculated in the non-third-party case.")
    )
    developer_annual_free_cashflows = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list, blank=True,
        help_text=("Annual free cashflow for the developer in the business-as-usual third party case for all "
                   "analysis years, including year 0. Future years have not been discounted to account for "
                   "the time value of money. Only calculated in the third-party case.")
    )
    developer_om_and_replacement_present_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Net O&M and replacement costs in present value, after-tax for the third-party developer."
                   "Only calculated in the third-party case.")
    )
    lifecycle_generation_tech_capital_costs = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). Net capital costs for all generation technologies."
                    "Costs are given in present value, including replacement costs and incentives."
                    "This value does not include offgrid_other_capital_costs.")
    )
    lifecycle_storage_capital_costs = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). Net capital costs for all storage technologies."
                    "Value is in present value, including replacement costs and incentives."
                    "This value does not include offgrid_other_capital_costs.")
    )
    lifecycle_om_costs_after_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). This value is the present value of all O&M costs, after tax.")
    )
    lifecycle_om_costs_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text=("BAU Component of lifecycle costs (LCC). This value is the present value of all O&M costs, after tax in the BAU case.")
    )
    lifecycle_fuel_costs_after_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). This value is the present value of all fuel costs over the analysis period, after tax.")
    )
    lifecycle_fuel_costs_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). This value is the present value of all fuel costs over the analysis period, after tax in the BAU case.")
    )
    lifecycle_chp_standby_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). This value is the present value of all CHP standby charges, after tax.")
    )
    lifecycle_chp_standby_cost_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text=("BAU Component of lifecycle costs (LCC). This value is the present value of all CHP standby charges, after tax.")
    )
    lifecycle_elecbill_after_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). This value is the present value of all electric utility charges, after tax.")
    )
    lifecycle_elecbill_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text=("BAU Component of lifecycle costs (LCC). This value is the present value of all electric utility charges, after tax.")
    )
    lifecycle_production_incentive_after_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). This value is the present value of all production-based incentives, after tax.")
    )
    lifecycle_production_incentive_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text=("BAU Component of lifecycle costs (LCC). This value is the present value of all production-based incentives, after tax.")
    )
    lifecycle_offgrid_other_annual_costs_after_tax = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). This value is the present value of offgrid_other_annual_costs over the analysis period, after tax.")
    )
    lifecycle_offgrid_other_capital_costs = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). This value is equal to offgrid_other_capital_costs with straight line depreciation applied"
                    " over the analysis period. The depreciation expense is assumed to reduce the owner's taxable income.")
    )
    lifecycle_outage_cost = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). Expected outage cost.")
    )
    lifecycle_outage_cost_bau = models.FloatField(
        null=True, blank=True,
        help_text=("BAU Component of lifecycle costs (LCC). Expected outage cost.")
    )
    lifecycle_MG_upgrade_and_fuel_cost = models.FloatField(
        null=True, blank=True,
        help_text=("Component of lifecycle costs (LCC). This is the cost to upgrade generation and storage technologies to be included in microgrid"
                    "plus present value of microgrid fuel costs.")
    )
    lifecycle_MG_upgrade_and_fuel_cost_bau = models.FloatField(
        null=True, blank=True,
        help_text=("BAU Component of lifecycle costs (LCC). This is the cost to upgrade generation and storage technologies to be included in microgrid"
                    "plus present value of microgrid fuel costs.")
    )
    replacements_future_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Future cost of replacing storage and/or generator systems, after tax."
    )
    replacements_present_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Present value cost of replacing storage and/or generator systems, after tax."
    )
    offgrid_microgrid_lcoe_dollars_per_kwh = models.FloatField(
        null=True, blank=True,
        help_text="Levelized cost of electricity for modeled off-grid system."
    )
    lifecycle_emissions_cost_climate = models.FloatField(
        null=True, blank=True,
        help_text="Total cost of CO2 emissions associated with the site's energy consumption over the analysis period."
    )
    lifecycle_emissions_cost_health = models.FloatField(
        null=True, blank=True,
        help_text="Total cost of NOx, SO2, and PM2.5 emissions associated with the site's energy consumption over the analysis period."
    )
    lifecycle_emissions_cost_climate_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total cost of CO2 emissions associated with the site's energy consumption over the analysis period in the BAU case."
    )
    lifecycle_emissions_cost_health_bau = models.FloatField(
        null=True, blank=True,
        help_text="Total cost of NOx, SO2, and PM2.5 emissions associated with the site's energy consumption over the analysis period in the BAU case."
    )
    breakeven_cost_of_emissions_reduction_per_tonne_CO2 = models.FloatField(
        null=True, blank=True,
        help_text=("Cost of emissions required to breakeven (NPV = 0) compared to the BAU case LCC."
                    "If the cost of health emissions were included in the objective function," 
                    "calculation of this output value keeps the cost of those emissions at the values input by the user.")
    )

class ElectricLoadInputs(BaseModel, models.Model):
    key = "ElectricLoad"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ElectricLoadInputs",
        primary_key=True
    )

    possible_sets = [
        ["loads_kw"],
        ["doe_reference_name", "monthly_totals_kwh"],
        ["annual_kwh", "doe_reference_name"],
        ["doe_reference_name"],
        ["blended_doe_reference_names", "blended_doe_reference_percents"]
    ]

    DOE_REFERENCE_NAME = models.TextChoices('DOE_REFERENCE_NAME', (
        'FastFoodRest '
        'FullServiceRest '
        'Hospital '
        'LargeHotel '
        'LargeOffice '
        'MediumOffice '
        'MidriseApartment '
        'Outpatient '
        'PrimarySchool '
        'RetailStore '
        'SecondarySchool '
        'SmallHotel '
        'SmallOffice '
        'StripMall '
        'Supermarket '
        'Warehouse '
        'FlatLoad '
        'FlatLoad_24_5 '
        'FlatLoad_16_7 '
        'FlatLoad_16_5 '
        'FlatLoad_8_7 '
        'FlatLoad_8_5'
    ))

    annual_kwh = models.FloatField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10000000000)
        ],
        null=True, blank=True,
        help_text=("Annual site energy consumption from electricity, in kWh, used to scale simulated default building "
                   "load profile for the site's climate zone")
    )
    doe_reference_name = models.TextField(
        null=False,
        blank=True,  # TODO do we have to include "" in choices for blank=True to work?
        choices=DOE_REFERENCE_NAME.choices,
        help_text=("Simulated load profile from DOE Commercial Reference Buildings "
                   "https://energy.gov/eere/buildings/commercial-reference-buildings")
    )
    year = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(9999)
        ],
        null=True, blank=True,
        help_text=("Year of Custom Load Profile. If a custom load profile is uploaded via the loads_kw parameter, it "
                   "is important that this year correlates with the load profile so that weekdays/weekends are "
                   "determined correctly for the utility rate tariff. If a DOE Reference Building profile (aka "
                   "'simulated' profile) is used, the year is set to 2017 since the DOE profiles start on a Sunday.")
    )
    monthly_totals_kwh = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1.0e9)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Monthly site energy consumption (an array 12 entries long), in kWh, used to scale either loads_kw series "
                   "(with normalize_and_scale_load_profile_input) or the simulated default building load profile for the site's climate zone")
    )
    monthly_peaks_kw = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1.0e8)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Monthly peak power consumption (an array 12 entries long), in kW, used to scale either loads_kw series "
                   "(with normalize_and_scale_load_profile_input) or the simulated default building load profile for the site's climate zone."
                   "Monthly energy is maintained while scaling to the monthly peaks."
                   )
    )
    loads_kw = ArrayField(
        models.FloatField(blank=True),
        default=list, blank=True,
        help_text=("Typical load over all hours in one year. Must be hourly (8,760 samples), 30 minute (17,"
                   "520 samples), or 15 minute (35,040 samples). All non-net load values must be greater than or "
                   "equal to zero. "
                   )
    )
    normalize_and_scale_load_profile_input = models.BooleanField(
        blank=True,
        default=False,
        help_text=("Takes the input loads_kw and normalizes and scales it to the inputs annual_kwh, monthly_totals_kwh, and/or monthly_peaks_kw.")
    )
    critical_loads_kw = ArrayField(
        models.FloatField(blank=True),
        default=list, blank=True,
        help_text=("Critical load during an outage period. Must be hourly (8,760 samples), 30 minute (17,520 samples),"
                   "or 15 minute (35,040 samples). All non-net load values must be greater than or equal to zero."
                   )
    )
    loads_kw_is_net = models.BooleanField(
        blank=True,
        default=True,
        help_text=("If there is existing PV, must specify whether provided load is the net load after existing PV or "
                   "not.")
    )
    critical_loads_kw_is_net = models.BooleanField(
        blank=True,
        default=False,
        help_text=("If there is existing PV, must specify whether provided load is the net load after existing PV or "
                   "not.")
    )
    critical_load_fraction = models.FloatField(
        blank=True,
        default = 0.5,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(2)
        ],
        # default=0.5,
        help_text="Critical load factor is multiplied by the typical load to determine the critical load that must be "
                  "met during an outage. Value must be between zero and one, inclusive."

    )

    operating_reserve_required_fraction = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        help_text="Only applicable when off_grid_flag=True; defaults to 0.1 (10 pct) for off-grid scenarios and fixed at 0 otherwise."
                    "Required operating reserves applied to each timestep as a fraction of electric load in that timestep."

    )

    min_load_met_annual_fraction = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        help_text="Only applicable when off_grid_flag = True. Fraction of the load that must be met on an annual energy basis."

    )

    blended_doe_reference_names = ArrayField(
        models.TextField(
            choices=DOE_REFERENCE_NAME.choices,
            blank=True
        ),
        default=list,
        blank=True,
        help_text=("Used in concert with blended_doe_reference_percents to create a blended load profile from multiple "
                   "DoE Commercial Reference Buildings.")
    )
    blended_doe_reference_percents = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=("Used in concert with blended_doe_reference_names to create a blended load profile from multiple "
                   "DoE Commercial Reference Buildings. Must sum to 1.0.")
    )
    # outage_is_major_event = models.BooleanField(
    #     null=True,
    #     blank=True,
    #     default=True,
    #     help_text="Boolean value for if outage is a major event, which affects the avoided_outage_costs. If "
    #               "True, the avoided outage costs are calculated for a single outage occurring in the first year of "
    #               "the analysis_years. If False, the outage event is assumed to be an average outage event that occurs "
    #               "every year of the analysis period. In the latter case, the avoided outage costs for one year are "
    #               "escalated and discounted using the escalation_rate_fraction and offtaker_discount_rate_fraction to account for an "
    #               "annually recurring outage. (Average outage durations for certain utility service areas can be "
    #               "estimated using statistics reported on EIA form 861.)"
    # )

    def clean(self):
        error_messages = {}

        # possible sets for defining load profile
        if not at_least_one_set(self.dict, self.possible_sets):
            error_messages["required inputs"] = \
                "Must provide at least one set of valid inputs from {}.".format(self.possible_sets)

        if len(self.blended_doe_reference_names) > 0 and self.doe_reference_name == "":
            if len(self.blended_doe_reference_names) != len(self.blended_doe_reference_percents):
                error_messages["blended_doe_reference_names"] = \
                    "The number of blended_doe_reference_names must equal the number of blended_doe_reference_percents."
            if not math.isclose(sum(self.blended_doe_reference_percents),  1.0):
                error_messages["blended_doe_reference_percents"] = "Sum must = 1.0."

        if self.doe_reference_name != "" or \
                len(self.blended_doe_reference_names) > 0:
            self.year = 2017  # the validator provides an "info" message regarding this

        if error_messages:
            raise ValidationError(error_messages)


class ElectricLoadOutputs(BaseModel, models.Model):
    key = "ElectricLoadOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="ElectricLoadOutputs"
    )

    load_series_kw = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Annual time series of BAU electric load. Does not include electric load for any new heating or cooling techs."
    )
    critical_load_series_kw = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text=("Hourly critical load for outage simulator. Values are either uploaded by user, "
                   "or determined from typical load (either uploaded or simulated) and critical_load_fraction.")
    )
    annual_calculated_kwh = models.FloatField(
        null=True, blank=True,
        help_text="Annual energy consumption calculated by summing up load_series_kw. Does not include electric load for any new heating or cooling techs."
    )
    monthly_calculated_kwh = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Monthly energy consumption calculated by summing up load_series_kw. Does not include electric load for any new heating or cooling techs."
    )
    monthly_peaks_kw = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Monthly peak energy demand determined from load_series_kw. Does not include electric load for any new heating or cooling techs."
    )
    annual_peak_kw = models.FloatField(
        null=True, blank=True,
        help_text="Annual peak energy demand determined from load_series_kw. Does not include electric load for any new heating or cooling techs."
    )
    annual_electric_load_with_thermal_conversions_kwh = models.FloatField(
        null=True, blank=True,
        help_text="Total end-use electrical load, including electrified heating and cooling end-use load."
    )
    bau_critical_load_met = models.BooleanField(
        null=True, blank=True,
        help_text="Boolean for if the critical load is met by the existing technologies in the BAU scenario."
    )
    bau_critical_load_met_time_steps = models.IntegerField(
        null=True, blank=True,
        help_text="Number of time steps the existing system can sustain the critical load."
    )
    offgrid_load_met_fraction = models.FloatField(
        null=True, blank=True,
        help_text="Percentage of total electric load met on an annual basis, for off-grid scenarios only"
    )
    offgrid_annual_oper_res_required_series_kwh = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Total operating reserves required (for load and techs) on an annual basis, for off-grid scenarios only"
    )
    offgrid_annual_oper_res_provided_series_kwh = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Total operating reserves provided on an annual basis, for off-grid scenarios only"
    )
    offgrid_load_met_series_kw = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Percentage of total electric load met on an annual basis, for off-grid scenarios only"
    )

class ElectricTariffInputs(BaseModel, models.Model):
    key = "ElectricTariff"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ElectricTariffInputs",
        primary_key=True
    )

    possible_sets = [
        ["urdb_response"],
        ["monthly_demand_rates", "monthly_energy_rates"],
        ["blended_annual_energy_rate", "blended_annual_demand_rate"],
        ["urdb_label"],
        ["urdb_utility_name", "urdb_rate_name"],
        ["tou_energy_rates_per_kwh"]
    ]

    monthly_demand_rates = ArrayField(
        models.FloatField(blank=True),
        default=list, blank=True,
        size=12,
        help_text="Array (length of 12) of blended demand charges in dollars per kW"
    )
    monthly_energy_rates = ArrayField(
        models.FloatField(blank=True),
        default=list, blank=True,
        size=12,
        help_text="Array (length of 12) of blended energy rates in dollars per kWh."
    )
    urdb_label = models.TextField(
        blank=True,
        help_text=("Label attribute of utility rate structure from Utility Rate Database API "
                   "https://openei.org/services/doc/rest/util_rates/?version=8")
    )
    urdb_response = models.JSONField(
        null=True, blank=True,
        help_text=("Utility rate structure from Utility Rate Database API "
                   "https://openei.org/services/doc/rest/util_rates/?version=8")
    )
    urdb_rate_name = models.TextField(
        blank=True,
        help_text="Name of utility rate from Utility Rate Database https://openei.org/wiki/Utility_Rate_Database"
    )
    urdb_utility_name = models.TextField(
        blank=True,
        help_text="Name of Utility from Utility Rate Database https://openei.org/wiki/Utility_Rate_Database"
    )
    blended_annual_demand_rate = models.FloatField(
        blank=True,
        null=True,
        help_text="Average monthly demand charge ($ per kW per month). Rate will be applied to monthly peak demand."
    )
    blended_annual_energy_rate = models.FloatField(
        blank=True,
        null=True,
        help_text="Annual blended energy rate (total annual energy in kWh divided by annual cost in $)"
    )
    wholesale_rate = ArrayField(
        models.FloatField(
            blank=True,
            validators=[
                MinValueValidator(0)
            ]
        ),
        default=list, blank=True,
        help_text=("Price of electricity sold back to the grid in absence of net metering."
                  " Can be a scalar value, which applies for all-time, or an array with time-sensitive"
                  " values. If an array is input then it must have a length of 8760, 17520, or 35040. The inputed array"
                  "values are up/down-sampled using mean values to match the Settings.time_steps_per_hour.")
    )
    export_rate_beyond_net_metering_limit = ArrayField(
        models.FloatField(
            blank=True,
            validators=[
                MinValueValidator(0)
            ]
        ),
        default=list,
        blank=True,
        help_text=("Price of electricity sold back to the grid above the site load, regardless of net metering. Can be "
                   "a scalar value, which applies for all-time, or an array with time-sensitive values. If an array is "
                   "input then it must have a length of 8760, 17520, or 35040. The inputed array values are up/down-"
                   "sampled using mean values to match the Scenario time_steps_per_hour.")
    )
    tou_energy_rates_per_kwh = ArrayField(
        models.FloatField(blank=True),
        default=list,
        blank=True,
        help_text=("Time-of-use energy rates, provided by user. Must be an array with length equal to number of "
                   "time steps per year. Hourly or 15 minute rates allowed.")
    )
    add_monthly_rates_to_urdb_rate = models.BooleanField(
        blank=True,
        default=False,
        help_text=("Set to true to add the monthly blended energy rates and demand charges to the URDB rate schedule. "
                   "Otherwise, blended rates will only be considered if a URDB rate is not provided.")

    )
    add_tou_energy_rates_to_urdb_rate = models.BooleanField(
        blank=True,
        default=False,
        help_text=("Set to true to add tou_energy_rates_per_kwh to the URDB rate schedule. Otherwise, tou energy rates "
                   "will only be considered if a URDB rate is not provided.")

    )
    coincident_peak_load_active_time_steps = ArrayField(
        ArrayField(
            models.IntegerField(
                blank=True,
                validators=[
                    MinValueValidator(1)
                ]
            ),
            blank=True,
            default=list
        ),
        blank=True,
        default=list,
        help_text=("The optional coincident_peak_load_charge_per_kw will apply to the max grid-purchased "
                   "power during these time steps. Note time steps are indexed to a base of 1 not 0.")
    )
    coincident_peak_load_charge_per_kw = ArrayField(
        models.FloatField(
            blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1.0e8)
            ],
        ),
        null=True, blank=True,
        default=list,
        help_text=("Optional coincident peak demand charge that is applied to the max load during the time_steps "
                   "specified in coincident_peak_load_active_time_steps")
    )
    urdb_metadata = models.JSONField(
        null=True, blank=True,
        help_text=("Utility rate meta data from Utility Rate Database API")
    )    

    def clean(self):
        error_messages = {}

        # possible sets for defining tariff
        if not at_least_one_set(self.dict, self.possible_sets):
            error_messages["required inputs"] = \
                f"Must provide at least one set of valid inputs from {self.possible_sets}. If this is an off-grid analysis, ElectricTariff inputs will not be used in REopt, and can be removed from input JSON."

        for possible_set in self.possible_sets:
            if len(possible_set) == 2:  # check dependencies
                if (possible_set[0] and not possible_set[1]) or (not possible_set[0] and possible_set[1]):
                    error_messages["required inputs"] = f"Must provide both {possible_set[0]} and {possible_set[1]}"

        self.wholesale_rate = scalar_or_monthly_to_8760(self.wholesale_rate)
        self.export_rate_beyond_net_metering_limit = scalar_or_monthly_to_8760(self.export_rate_beyond_net_metering_limit)

        if len(self.coincident_peak_load_charge_per_kw) > 0:
            if len(self.coincident_peak_load_active_time_steps) != len(self.coincident_peak_load_charge_per_kw):
                error_messages["coincident peak"] = (
                    "The number of rates in coincident_peak_load_charge_per_kw must match the number of "
                    "timestep sets in coincident_peak_load_active_time_steps")

        if self.urdb_label is not None:
            label_checker = URDB_LabelValidator(self.urdb_label)
            if label_checker.errors:
                error_messages["urdb_label"] = label_checker.errors
        if self.urdb_response is not None:
            try:
                rate_checker = URDB_RateValidator(**self.urdb_response)
                if rate_checker.errors:
                    error_messages["urdb_response"] = rate_checker.errors
            except:
                error_messages["urdb_response"] = "Error parsing urdb_response. Please check the keys and values."
        
        if error_messages:
            raise ValidationError(error_messages)

    def save(self, *args, **kwargs):
        """
        Special case for coincident_peak_load_active_time_steps: back-end database requires that
        "multidimensional arrays must have array expressions with matching dimensions"
        so we fill the arrays that are shorter than the longest arrays with repeats of the last value.
        By repeating the last value we do not have to deal with a mix of data types in the arrays and it does not
        affect the constraints in REopt.
        """
        # TODO: we might want to instead make the underlying IntegerField nullable and pad with None,
        # because avoiding duplicate constraints could speed up solve time.
        if len(self.coincident_peak_load_active_time_steps) > 0:
            max_length = max(len(inner_array) for inner_array in self.coincident_peak_load_active_time_steps)
            for inner_array in self.coincident_peak_load_active_time_steps:
                if len(inner_array) != max_length:
                    for _ in range(max_length - len(inner_array)):
                        inner_array.append(inner_array[-1])
        super(ElectricTariffInputs, self).save(*args, **kwargs)

    @property
    def dict(self):
        """
        Serialize Django Model.__dict__, custom implementation for ElectricTariffInputs
        NOTE: to get correct field types you must run self.clean_fields() first (eg. convert int to float)
        :return: dict
        """
        d = copy.deepcopy(self.__dict__)
        if "coincident_peak_load_active_time_steps" in d.keys():
            # filter out repeated values created to make the inner arrays have equal length
            d["coincident_peak_load_active_time_steps"] = \
                [list(set(l)) for l in d["coincident_peak_load_active_time_steps"]]
        d.pop("_state", None)
        d.pop("id", None)
        d.pop("basemodel_ptr_id", None)
        d.pop("meta_id", None)
        return d


class ElectricUtilityInputs(BaseModel, models.Model):
    key = "ElectricUtility"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ElectricUtilityInputs",
        primary_key=True
    )

    outage_start_time_step = models.IntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1)
            # max value validated in InputValidator b/c it requires Settings.time_steps_per_hour
        ],
        help_text="Time step that grid outage starts. Must be less than or equal to outage_end_time_step. Use to model a single, deterministic outage."
    )
    outage_end_time_step = models.IntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1)
            # max value validated in InputValidator b/c it requires Settings.time_steps_per_hour
        ],
        help_text="Time step that grid outage ends. Must be greater than or equal to outage_start_time_step. Use to model a single, deterministic outage."
    )
    outage_start_time_steps = ArrayField(
        models.IntegerField(
            blank=True,
            validators=[
                MinValueValidator(1)
            ]
        ),
        blank=True,
        default=list,
        help_text=("A list of time steps that the grid outage may start. "
                    "This input is used for robust optimization across multiple outages. "
                    "The maximum (over outage_start_time_steps) of the expected value "
                    "(over outage_durations with probabilities outage_probabilities) of "
                    "outage cost is included in the objective function minimized by REopt."
                )
    )
    outage_durations = ArrayField(
        models.IntegerField(
            blank=True,
            validators=[
                MinValueValidator(1)
            ]
        ),
        blank=True,
        default=list,
        help_text=("One-to-one with outage_probabilities. A list of possible time step durations of the grid outage. "
                    "This input is used for robust optimization across multiple outages. "
                    "The maximum (over outage_start_time_steps) of the expected value "
                    "(over outage_durations with probabilities outage_probabilities) of "
                    "outage cost is included in the objective function minimized by REopt."
                )
    )
    outage_probabilities = ArrayField(
        models.FloatField(
            blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1)
            ]
        ),
        blank=True,
        default=list,
        help_text=("One-to-one with outage_durations. The probability of each duration of the grid outage. Defaults to equal probability for each duration. "
                    "This input is used for robust optimization across multiple outages. "
                    "The maximum (over outage_start_time_steps) of the expected value "
                    "(over outage_durations with probabilities outage_probabilities) of "
                    "outage cost is included in the objective function minimized by REopt."
                )
    )
    interconnection_limit_kw = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        default=1.0e9,
        blank=True,
        help_text="Limit on total system capacity that can be interconnected to the grid."
    )
    net_metering_limit_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        null=True, blank=True,
        help_text="Upper limit on the total capacity of technologies that can participate in net metering agreement."
    )
    allow_simultaneous_export_import = models.BooleanField(
        blank=True,
        default = True,
        help_text=("If true the site has two meters (in effect).")
    )
    cambium_scenario = models.TextField(
        blank=True,
        default = "Mid-case",
        help_text=("Cambium Scenario for evolution of electricity sector (see Cambium documentation for descriptions)."
                   "Options: ['Mid-case', 'Low renewable energy cost',   'High renewable energy cost', 'High demand growth',  'Low natural gas prices', 'High natural gas prices', 'Mid-case with 95% decarbonization by 2050',  'Mid-case with 100% decarbonization by 2035']")
    )
    cambium_location_type = models.TextField(
        blank=True,
        default = "GEA Regions 2023",
        help_text=("Geographic boundary at which emissions and clean energy fraction are calculated. Options: ['Nations', 'GEA Regions 2023'].")
    )
    cambium_co2_metric = models.TextField(
        blank=True,
        default = "lrmer_co2e",
        help_text=("Emissions metric used. Default is Long-run marginal emissions rate for CO2-equivalant, combined combustion and pre-combustion emissions rates. Options: See metric definitions and names in the Cambium documentation.")
    )
    cambium_start_year = models.IntegerField(
        default=2025,
        validators=[
            MinValueValidator(2025),
            MaxValueValidator(2050)
        ],
        blank=True,
        help_text="First year of operation of system. Emissions will be levelized starting in this year for the duration of cambium_levelization_years."
    )
    cambium_levelization_years = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(100)
        ],
        blank=True,
        null=True,
        help_text=("Expected lifetime or analysis period of the intervention being studied. "
                    "Emissions and clean energy fraction will be averaged over this period. Default: analysis_years (from Financial struct)")
    )
    cambium_grid_level = models.TextField(
        blank=True,
        default = "enduse",
        help_text=("Impacts grid climate emissions calculation. Options: ['enduse' or 'busbar']. Busbar refers to point where bulk generating stations connect to grid; enduse refers to point of consumption (includes distribution loss rate).")
    )
    co2_from_avert = models.BooleanField(
        default=False,
        blank=True,
        help_text="Default is to use Cambium data for CO2 grid emissions. Set to `true` to instead use data from the EPA's AVERT database. "
    )
    emissions_factor_series_lb_CO2_per_kwh = ArrayField(
        models.FloatField(
            blank=True,
        ),
        default=list, blank=True,
        help_text=("CO2 emissions factor over all hours in one year. Can be provided as either a single constant fraction that will be applied across all timesteps, or an annual timeseries array at an hourly (8,760 samples), 30 minute (17,520 samples), or 15 minute (35,040 samples) resolution.")
    )
    emissions_factor_CO2_decrease_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        null=True, blank=True,
        help_text="Not applied with use of Cambium data for climate emissions. Annual percent decrease in the total annual CO2 emissions rate of the grid. A negative value indicates an annual increase."
    )
    avert_emissions_region = models.TextField(
        blank=True,
        help_text=("Name of the AVERT emissions region to use. Options are: "
                "'California', 'Central', 'Florida', 'Mid-Atlantic', 'Midwest', 'Carolinas', "
                "'New England', 'Northwest', 'New York', 'Rocky Mountains', 'Southeast', 'Southwest', "
                "'Tennessee', 'Texas', 'Alaska', 'Hawaii (except Oahu)', 'Hawaii (Oahu)'. "
                "If emissions_factor_series_lb_<pollutant>_per_kwh inputs are not provided, "
                "avert_emissions_region overrides latitude and longitude in determining emissions factors.")
    )
    emissions_factor_series_lb_NOx_per_kwh = ArrayField(
        models.FloatField(
            blank=True,
        ),
        default=list, blank=True,
        help_text=("NOx emissions factor over all hours in one year. Can be provided as either a single constant fraction that will be applied across all timesteps, or an annual timeseries array at an hourly (8,760 samples), 30 minute (17,520 samples), or 15 minute (35,040 samples) resolution.")
    )
    emissions_factor_series_lb_SO2_per_kwh = ArrayField(
        models.FloatField(
            blank=True,
        ),
        default=list, blank=True,
        help_text=("SO2 emissions factor over all hours in one year. Can be provided as either a single constant fraction that will be applied across all timesteps, or an annual timeseries array at an hourly (8,760 samples), 30 minute (17,520 samples), or 15 minute (35,040 samples) resolution.")
    )
    emissions_factor_series_lb_PM25_per_kwh = ArrayField(
        models.FloatField(
            blank=True,
        ),
        default=list, blank=True,
        help_text=("PM2.5 emissions factor over all hours in one year. Can be provided as either a single constant fraction that will be applied across all timesteps, or an annual timeseries array at an hourly (8,760 samples), 30 minute (17,520 samples), or 15 minute (35,040 samples) resolution.")
    )
    
    emissions_factor_NOx_decrease_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        null=True, blank=True,
        help_text="Annual percent decrease in the total annual NOx marginal emissions rate of the grid. A negative value indicates an annual increase."
    )
    emissions_factor_SO2_decrease_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        null=True, blank=True,
        help_text="Annual percent decrease in the total annual SO2 marginal emissions rate of the grid. A negative value indicates an annual increase."
    )
    emissions_factor_PM25_decrease_fraction = models.FloatField(
        validators=[
            MinValueValidator(-1),
            MaxValueValidator(1)
        ],
        null=True, blank=True,
        help_text="Annual percent decrease in the total annual PM2.5 marginal emissions rate of the grid. A negative value indicates an annual increase."
    )

    cambium_cef_metric = models.TextField(
        blank=True,
        default = "cef_load",
        help_text=("Options = ['cef_load', 'cef_gen']. cef_load is the fraction of generation that is clean, for the generation that is allocated to a region’s end-use load; cef_gen is the fraction of generation that is clean within a region.")
    )

    renewable_energy_fraction_series = ArrayField(
        models.FloatField(
            blank=True,
        ),
        default=list, blank=True,
        help_text=("Fraction of energy supplied by the grid that is renewable. Can be scalar or timeseries (aligned with time_steps_per_hour).")
    )

    def clean(self):
        error_messages = {}

        # outage start/end time step dependencies
        if self.outage_start_time_step and self.outage_end_time_step is None:
            error_messages["outage_end_time_step"] = "Got outage_start_time_step but no outage_end_time_step."

        if self.outage_end_time_step and self.outage_start_time_step is None:
            error_messages["outage_start_time_step"] = "Got outage_end_time_step but no outage_start_time_step."

        if self.outage_start_time_step is not None and self.outage_end_time_step is not None:
            if self.outage_start_time_step > self.outage_end_time_step:
                error_messages["outage start/stop time steps"] = \
                    ('outage_end_time_step must be larger than or equal to outage_start_time_step.')
        
        if self.outage_probabilities not in [None,[]]:
            if abs(1.0-sum(self.outage_probabilities)) > 1e-08:
                error_messages["outage_probabilities"] = "outage_probabilities must have a sum of 1.0."
            if self.outage_durations not in [None,[]]:
                if len(self.outage_probabilities) != len(self.outage_durations):
                    error_messages["mismatched length"] = "outage_probabilities and outage_durations must have the same length."
            else: 
                error_messages["missing required inputs"] = "outage_durations is required if outage_probabilities is present."
        elif self.outage_durations not in [None,[]]: 
            self.outage_probabilities = [1/len(self.outage_durations)] * len(self.outage_durations)

        if (self.co2_from_avert or len(self.emissions_factor_series_lb_CO2_per_kwh) > 0) and self.emissions_factor_CO2_decrease_fraction == None:
            # use default if not provided and using AVERT or custom EFs. Leave blank otherwise and the Julia Pkg will set to 0 unless site is in AK or HI.
            self.emissions_factor_CO2_decrease_fraction = EMISSIONS_DECREASE_DEFAULTS.get("CO2e", None) 

        if self.emissions_factor_NOx_decrease_fraction == None:
            self.emissions_factor_NOx_decrease_fraction = EMISSIONS_DECREASE_DEFAULTS.get("NOx", 0.0)
        if self.emissions_factor_SO2_decrease_fraction == None:
            self.emissions_factor_SO2_decrease_fraction = EMISSIONS_DECREASE_DEFAULTS.get("SO2", 0.0)
        if self.emissions_factor_PM25_decrease_fraction == None:
            self.emissions_factor_PM25_decrease_fraction = EMISSIONS_DECREASE_DEFAULTS.get("PM25", 0.0)

        if error_messages:
            raise ValidationError(error_messages)


class ElectricUtilityOutputs(BaseModel, models.Model):
    key = "ElectricUtilityOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ElectricUtilityOutputs",
        primary_key=True
    )

    electric_to_load_series_kw = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list, blank=True,
        help_text=("Optimal average annual grid to load time series")
    )
    electric_to_load_series_kw_bau = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list, blank=True,
        help_text=("Business as usual average annual grid to load time series")
    )
    electric_to_storage_series_kw = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list, blank=True,
        help_text=("Optimal average annual grid to battery time series")
    )
    annual_energy_supplied_kwh = models.FloatField(
        null=True, blank=True,
        help_text=("Average annual energy supplied from grid to load")
    )
    annual_energy_supplied_kwh_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Average annual energy supplied from grid to load")
    )
    annual_renewable_electricity_supplied_kwh = models.FloatField(
        null=True, blank=True,
        help_text=("Total renewable electricity supplied from the grid in an average year.")
    )
    annual_renewable_electricity_supplied_kwh_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Total renewable electricity supplied from the grid in an average year.")
    )
    annual_emissions_tonnes_CO2 = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of CO2 emissions associated with the site's grid-purchased electricity in an average year. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    annual_emissions_tonnes_CO2_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of CO2 emissions associated with the site's grid-purchased electricity in an average year in the BAU case. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    annual_emissions_tonnes_NOx = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of NOx emissions associated with the site's grid-purchased electricity in an average year. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    annual_emissions_tonnes_NOx_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of NOx emissions associated with the site's grid-purchased electricity in an average year in the BAU case. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    annual_emissions_tonnes_SO2 = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of CO2 emissions associated with the site's grid-purchased electricity in an average year. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    annual_emissions_tonnes_SO2_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of SO2 emissions associated with the site's grid-purchased electricity in an average year in the BAU case. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    annual_emissions_tonnes_PM25 = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of PM2.5 emissions associated with the site's grid-purchased electricity in an average year. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    annual_emissions_tonnes_PM25_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of PM2.5 emissions associated with the site's grid-purchased electricity in an average year in the BAU case. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )

    lifecycle_emissions_tonnes_CO2 = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of CO2 emissions associated with the site's grid-purchased electricity over the analysis period. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    lifecycle_emissions_tonnes_CO2_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of CO2 emissions associated with the site's grid-purchased electricity over the analysis period in the BAU case. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    lifecycle_emissions_tonnes_NOx = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of NOx emissions associated with the site's grid-purchased electricity over the analysis period. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    lifecycle_emissions_tonnes_NOx_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of NOx emissions associated with the site's grid-purchased electricity over the analysis period in the BAU case. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    lifecycle_emissions_tonnes_SO2 = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of CO2 emissions associated with the site's grid-purchased electricity over the analysis period. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    lifecycle_emissions_tonnes_SO2_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of SO2 emissions associated with the site's grid-purchased electricity over the analysis period in the BAU case. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    lifecycle_emissions_tonnes_PM25 = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of PM2.5 emissions associated with the site's grid-purchased electricity over the analysis period. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    lifecycle_emissions_tonnes_PM25_bau = models.FloatField(
        null=True, blank=True,
        help_text=("Total tons of PM2.5 emissions associated with the site's grid-purchased electricity over the analysis period in the BAU case. "
                    "If include_exported_elec_emissions_in_total is False, this value only reflects grid purchaes. "
                    "Otherwise, it accounts for emissions offset from any export to the grid.")
    )
    avert_emissions_region = models.TextField(
        blank=True,
        help_text=("Name of the AVERT emissions region to use. Options are: "
                "'California', 'Central', 'Florida', 'Mid-Atlantic', 'Midwest', 'Carolinas', "
                "'New England', 'Northwest', 'New York', 'Rocky Mountains', 'Southeast', 'Southwest', "
                "'Tennessee', 'Texas', 'Alaska', 'Hawaii (except Oahu)', 'Hawaii (Oahu)'. "
                "If emissions_factor_series_lb_<pollutant>_per_kwh inputs are not provided, "
                "avert_emissions_region overrides latitude and longitude in determining emissions factors.")
    )
    distance_to_avert_emissions_region_meters = models.FloatField(
        null=True, blank=True,
        help_text=("Distance in meters from the site to the nearest AVERT emissions region.")
    )
    cambium_region = models.TextField(
        blank=True,
        help_text=("Name of the Cambium emissions region used for climate emissions for grid electricity. " 
                   "Determined from site longitude and latitude and the cambium_location_type if "
                   "custom emissions_factor_series_lb_CO2_per_kwh not provided and co2_from_avert is false.")
    )
    peak_grid_demand_kw = models.FloatField(
        null=True, blank=True,
        help_text="Maximum grid demand calculated as the maximum of (electric_to_load_series_kw .+ electric_to_storage_series_kw)."
    )
    peak_grid_demand_kw_bau = models.FloatField(
        null=True, blank=True,
        help_text="Maximum grid demand in the BAU case calculated as the maximum of electric_to_load_series_kw."
    )

    def calculate_peak_demand(self):
        if self.electric_to_load_series_kw and self.electric_to_storage_series_kw:
            self.peak_grid_demand_kw = max(self.electric_to_load_series_kw + self.electric_to_storage_series_kw)
        if self.electric_to_load_series_kw_bau:
            self.peak_grid_demand_kw_bau = max(self.electric_to_load_series_kw_bau)

    def save(self, *args, **kwargs):
        self.calculate_peak_demand()
        super().save(*args, **kwargs)


class OutageOutputs(BaseModel, models.Model):
    key = "OutageOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="OutageOutputs",
        primary_key=True
    )
    expected_outage_cost = models.FloatField(
        null=True, blank=True,
        help_text="The expected outage cost over the random outages modeled."
    )
    max_outage_cost_per_outage_duration = ArrayField(
        models.FloatField(
            blank=True,
        ),
        default=list, blank=True,
        help_text="The maximum outage cost for every outage duration modeled."
    )
    critical_loads_per_outage_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True,
            ),
            default=list, blank=True,
        ),
        default=list, blank=True,
        help_text="The critical load in each outage time step for each outage start time and duration. Outage duration changes along the first dimension, outage start time step along the second, and time step in outage along the third."
    )    
    unserved_load_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True,
            ),
            default=list, blank=True,
        ),
        default=list, blank=True,
        help_text="The amount of unserved load in each outage time step for each outage start time and duration. Outage duration changes along the first dimension, outage start time step along the second, and time step in outage along the third."
    )
    unserved_load_per_outage_kwh = ArrayField(
        ArrayField(
            models.FloatField(
                blank=True,
            ),
            default=list, blank=True,
        ),
        default=list, blank=True,
        help_text="The total unserved load for each outage start time and duration. Outage duration changes along the first dimension and outage start time changes along the second dimension."
    )
    microgrid_upgrade_capital_cost = models.FloatField(
        null=True, blank=True,
        help_text="Total capital cost of including technologies in the microgrid."
    )
    storage_microgrid_upgrade_cost = models.FloatField(
        null=True, blank=True,
        help_text="Capital cost of including the electric storage system in the microgrid."
    )
    storage_discharge_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of storage power discharged in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    soc_series_fraction = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of storage state of charge (SOC) in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    electric_storage_microgrid_upgraded = models.BooleanField(
        null=True, blank=True,
        help_text=("True/False for if ElectricStorage is included in the microgrid.")
    )
    pv_microgrid_size_kw = models.FloatField(
        null=True, blank=True,
        help_text="Optimal PV capacity included in the microgrid."
    )
    pv_microgrid_upgrade_cost = models.FloatField(
        null=True, blank=True,
        help_text="Capital cost of including the PV system in the microgrid."
    )
    pv_to_storage_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of PV power sent to the battery in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    pv_curtailed_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of PV power curtailed in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    pv_to_load_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of PV power used to meet load in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    wind_microgrid_size_kw = models.FloatField(
        null=True, blank=True,
        help_text="Optimal Wind capacity included in the microgrid."
    )
    wind_microgrid_upgrade_cost = models.FloatField(
        null=True, blank=True,
        help_text="Capital cost of including the Wind system in the microgrid."
    )
    wind_to_storage_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of Wind power sent to the battery in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    wind_curtailed_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of Wind power curtailed in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    wind_to_load_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of Wind power used to meet load in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )    
    generator_microgrid_size_kw = models.FloatField(
        null=True, blank=True,
        help_text="Optimal generator capacity included in the microgrid."
    )
    generator_microgrid_upgrade_cost = models.FloatField(
        null=True, blank=True,
        help_text="Capital cost of including the generator system in the microgrid."
    )
    generator_to_storage_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of generator power sent to the battery in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    generator_curtailed_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of generator power curtailed in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    generator_to_load_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of generator power used to meet load in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    generator_fuel_used_per_outage_gal = ArrayField(
        ArrayField(
            models.FloatField(
                blank=True,
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text="Generator fuel used in each outage modeled. Outage duration changes along the first dimension and outage start time changes along the second dimension."
    )
    chp_microgrid_size_kw = models.FloatField(
        null=True, blank=True,
        help_text="Optimal CHP electric capacity included in the microgrid."
    )
    chp_microgrid_upgrade_cost = models.FloatField(
        null=True, blank=True,
        help_text="Capital cost of including the CHP system in the microgrid."
    )
    chp_to_storage_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of CHP power sent to the battery in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    chp_curtailed_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of CHP power curtailed in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    chp_to_load_series_kw = ArrayField(
        ArrayField(
            ArrayField(
                models.FloatField(
                    blank=True,
                ),
                default=list, blank=True
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text=("Array of CHP power used to meet load in every outage modeled. "
                    "Outage duration changes along the first dimension, "
                    "outage start time changes along the second dimension, "
                    "and hour within outage changes along the third dimension.")
    )
    chp_fuel_used_per_outage_mmbtu = ArrayField(
        ArrayField(
            models.FloatField(
                blank=True,
            ),
            default=list, blank=True
        ),
        default=list, blank=True,
        help_text="CHP fuel used in each outage modeled. Outage duration changes along the first dimension and outage start time changes along the second dimension."
    )

class ElectricTariffOutputs(BaseModel, models.Model):
    key = "ElectricTariffOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ElectricTariffOutputs",
        primary_key=True
    )

    monthly_fixed_cost_series_before_tax = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Year one fixed utility costs for each month."
    )
    monthly_fixed_cost_series_before_tax_bau = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Business as usual year one fixed utility costs for each month."
    )
    energy_cost_series_before_tax = models.JSONField(
        null=True, blank=True,
        help_text="Series of cost of power purchased from grid to serve load in each timestep, by Tier_i."
    )
    energy_cost_series_before_tax_bau = models.JSONField(
        null=True, blank=True,
        help_text="Business as usual series of cost of power purchased from grid to serve load in each timestep, by Tier_i."
    )
    monthly_energy_cost_series_before_tax = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Series of monthly cost of power purchased from grid to serve loads."
    )
    monthly_energy_cost_series_before_tax_bau = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Business as usual series of monthly cost of power purchased from grid to serve loads."
    )
    monthly_facility_demand_cost_series_before_tax = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Series of total (all tiers) monthly facility demand charges by month."
    )
    monthly_facility_demand_cost_series_before_tax_bau = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Business as usual series of total (all tiers) monthly facility demand charges by month."
    )
    energy_rate_series = models.JSONField(
        null=True, blank=True,
        help_text="Series of billed energy rates for each timestep in year one."
    )
    energy_rate_average_series = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Series of average (across tiers) energy rates for each timestep in year one."
    )
    monthly_tou_demand_cost_series_before_tax = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Series of total time-of-use demand charges for each month."
    )
    monthly_tou_demand_cost_series_before_tax_bau = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Business as usual series of total time-of-use demand charges for each month."
    )
    monthly_demand_cost_series_before_tax = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Series of total (facility and TOU for all tiers) monthly demand charges for each month."
    )
    monthly_demand_cost_series_before_tax_bau = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Business as usual series of total (facility and TOU for all tiers) monthly demand charges for each month."
    )
    tou_demand_metrics = models.JSONField(
        null=True, blank=True,
        help_text="Dictionary of TOU demand metrics, including month, tier, demand_rate, measured_tou_peak_demand, and demand_charge_before_tax"
    )
    facility_demand_monthly_rate_tier_limits = models.JSONField(
        null=True, blank=True,
        help_text="Facility (not dependent on TOU) demand charge tier limits"
    )
    facility_demand_monthly_rate_series = models.JSONField(
        null=True, blank=True,
        help_text="Facility (not dependent on TOU) demand charge rates by Tier_i"
    )
    tou_demand_rate_tier_limits = models.JSONField(
        null=True, blank=True,
        help_text="TOU demand rate tier limits"
    )
    energy_rate_tier_limits = models.JSONField(
        null=True, blank=True,
        help_text="Energy rate tier limits"
    )
    tou_demand_rate_series = models.JSONField(
        null=True, blank=True,
        help_text="Series of demand rates by Tier_i for each timestep."
    )
    demand_rate_average_series = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Series of average (across tiers) demand rates for each timestep in year one."
    )
    year_one_energy_cost_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal year one utility energy cost"
    )
    year_one_demand_cost_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal year one utility demand cost"
    )
    year_one_fixed_cost_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal year one utility fixed cost"
    )
    year_one_min_charge_adder_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal year one utility minimum charge adder"
    )
    year_one_energy_cost_before_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual year one utility energy cost"
    )
    year_one_demand_cost_before_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual year one utility demand cost"
    )
    year_one_fixed_cost_before_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual year one utility fixed cost"
    )
    year_one_min_charge_adder_before_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual year one utility minimum charge adder"
    )
    lifecycle_energy_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal life cycle utility energy cost, after-tax"
    )
    lifecycle_demand_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal life cycle utility demand cost, after-tax"
    )
    lifecycle_fixed_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal life cycle utility fixed cost, after-tax"
    )
    lifecycle_min_charge_adder_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal life cycle utility minimum charge adder, after-tax"
    )
    lifecycle_energy_cost_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual life cycle utility energy cost, after-tax"
    )
    lifecycle_demand_cost_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual life cycle lifecycle utility demand cost, after-tax"
    )
    lifecycle_fixed_cost_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual life cycle utility fixed cost, after-tax"
    )
    lifecycle_min_charge_adder_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual life cycle utility minimum charge adder, after-tax"
    )
    lifecycle_export_benefit_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal life cycle value of exported energy, after-tax"
    )
    lifecycle_export_benefit_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual life cycle value of exported energy, after-tax"
    )
    year_one_bill_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal year one utility bill"
    )
    year_one_bill_before_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual year one utility bill"
    )
    year_one_bill_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal year one utility bill, after tax"
    )
    year_one_bill_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual year one utility bill, after tax"
    )    
    year_one_export_benefit_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal year one value of exported energy. A positive value indicates a benefit."
    )
    year_one_export_benefit_before_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual year one value of exported energy. A positive value indicates a benefit."
    )
    year_one_export_benefit_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal year one value of exported energy, after tax. A positive value indicates a benefit."
    )
    year_one_export_benefit_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual year one value of exported energy, after tax. A positive value indicates a benefit."
    )    
    year_one_coincident_peak_cost_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal year one coincident peak charges"
    )
    year_one_coincident_peak_cost_before_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual year one coincident peak charges"
    )
    lifecycle_coincident_peak_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal total coincident peak charges over the analysis period, after-tax"
    )
    lifecycle_coincident_peak_cost_after_tax_bau = models.FloatField(
        null=True, blank=True,
        help_text="Business as usual life cycle coincident peak charges, after-tax"
    )
    year_one_chp_standby_cost_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal year one standby charge cost incurred by CHP"
    )
    lifecycle_chp_standby_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Optimal life cycle standby charge cost incurred by CHP, after-tax"
    )


class PVInputs(BaseModel, models.Model):
    key = "PV"
    meta = models.ForeignKey(
        to=APIMeta,
        on_delete=models.CASCADE,
        related_name="PVInputs",
        unique=False
    )

    class ARRAY_TYPE_CHOICES(models.IntegerChoices):
        GROUND_MOUNT_FIXED_OPEN_RACK = 0
        ROOFTOP_FIXED = 1
        GROUND_MOUNT_ONE_AXIS_TRACKING = 2
        ONE_AXIS_BACKTRACKING = 3
        GROUND_MOUNT_TWO_AXIS_TRACKING = 4

    class MODULE_TYPE_CHOICES(models.IntegerChoices):
        STANDARD = 0
        PREMIUM = 1
        THIN_FILM = 2

    class PV_LOCATION_CHOICES(models.TextChoices):
        ROOF = 'roof'
        GROUND = 'ground'
        BOTH = 'both'

    name = models.TextField(
        blank=True,
        default="PV",
        help_text="PV description for distinguishing between multiple PV models"
    )
    existing_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e5)
        ],
        blank=True,
        help_text="Existing PV size"
    )
    min_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Minimum PV size constraint for optimization (lower bound on additional capacity beyond existing_kw)."
    )
    max_kw = models.FloatField(
        default=1.0e9,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum PV size constraint for optimization (upper bound on additional capacity beyond existing_kw). Set to zero to disable PV"
    )
    size_class = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ],
        null=True,
        blank=True,
        help_text="PV size class. Must be an integer value between 1 and 5. Default is 2, representing commercial-scale"
    )
    installed_cost_per_kw = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e5)
        ],
        null=True,
        blank=True,
        help_text="Installed PV cost in $/kW"
    )
    om_cost_per_kw = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e3)
        ],
        null=True,
        blank=True,
        help_text="Annual PV operations and maintenance costs in $/kW"
    )
    macrs_option_years = models.IntegerField(
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )
    macrs_bonus_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )
    macrs_itc_reduction = models.FloatField(
        default=0.5,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of the ITC value by which depreciable basis is reduced"
    )
    federal_itc_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percentage of capital costs that are credited towards federal taxes"
    )
    state_ibi_fraction = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percentage of capital costs offset by state incentives"
    )
    state_ibi_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum dollar value of state percentage-based capital cost incentive"
    )
    utility_ibi_fraction = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percentage of capital costs offset by utility incentives"
    )
    utility_ibi_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum dollar value of utility percentage-based capital cost incentive"
    )
    federal_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Federal rebates based on installed capacity"
    )
    state_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="State rebate based on installed capacity"
    )
    state_rebate_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum state rebate"
    )
    utility_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Utility rebate based on installed capacity"
    )
    utility_rebate_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum utility rebate"
    )
    production_incentive_per_kwh = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Production-based incentive value"
    )
    production_incentive_max_benefit = models.FloatField(
        default=1.0e9,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum annual value in present terms of production-based incentives"
    )
    production_incentive_years = models.IntegerField(
        default=1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        blank=True,
        help_text="Duration of production-based incentives from installation date"
    )
    production_incentive_max_kw = models.FloatField(
        default=1.0e9,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum system size eligible for production-based incentive"
    )
    degradation_fraction = models.FloatField(
        default=0.005,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Annual rate of degradation in PV energy production"
    )
    azimuth = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(360)
        ],
        blank=True,
        null=True,
        help_text=("PV azimuth angle")
    )
    losses = models.FloatField(
        default=0.14,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(0.99)
        ],
        blank=True,
        help_text=("PV system performance losses")
    )
    array_type = models.IntegerField(
        default=ARRAY_TYPE_CHOICES.ROOFTOP_FIXED,
        choices=ARRAY_TYPE_CHOICES.choices,
        blank=True,
        help_text=("PV Watts array type (0: Ground Mount Fixed (Open Rack); 1: Rooftop, Fixed; 2: Ground Mount 1-Axis "
                   "Tracking; 3 : 1-Axis Backtracking; 4: Ground Mount, 2-Axis Tracking)")
    )
    module_type = models.IntegerField(
        default=MODULE_TYPE_CHOICES.STANDARD,
        choices=MODULE_TYPE_CHOICES.choices,
        blank=True,
        help_text="PV module type (0: Standard; 1: Premium; 2: Thin Film)"
    )
    gcr = models.FloatField(
        default=0.4,
        validators=[
            MinValueValidator(0.01),
            MaxValueValidator(0.99)
        ],
        null=True, blank=True,
        help_text=("PV ground cover ratio (photovoltaic array area : total ground area).")
    )
    dc_ac_ratio = models.FloatField(
        default=1.2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(2)
        ],
        blank=True,
        help_text="PV DC-AC ratio"
    )
    inv_eff = models.FloatField(
        default=0.96,
        validators=[
            MinValueValidator(0.9),
            MaxValueValidator(0.995)
        ],
        null=True, blank=True,
        help_text="PV inverter efficiency"
    )
    radius = models.IntegerField(
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        null=True, blank=True,
        help_text=("Radius, in miles, to use when searching for the closest climate data station. Use zero to use the "
                   "closest station regardless of the distance.")
    )
    tilt = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(90)
        ],
        blank=True,
        null=True,
        help_text="PV system tilt angle. Default tilt is 20 degrees for fixed arrays (rooftop or ground-mounted) and 0 degrees for axis-tracking systems."
    )
    location = models.TextField(
        default=PV_LOCATION_CHOICES.BOTH,
        choices=PV_LOCATION_CHOICES.choices,
        blank=True,
        help_text="Where PV can be deployed. One of [roof, ground, both] with default as both."
    )
    kw_per_square_foot = models.FloatField(
        default=0.01,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10)
        ],
        blank=True,
        help_text=("The installed power density for rooftop PV systems in kW per square foot, accounting for setbacks, row spacing, etc. The recommended PV system size is constrained "
                   "based on the sum of land area available, assuming the specified ground-mount power density, and roofspace available, assuming the rooftop power density specified here.")
    )
    acres_per_kw = models.FloatField(
        default=0.006,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10)
        ],
        blank=True,
        help_text=("The acres per kW-DC for ground-mount PV systems in acres per kW, accounting for setbacks, row spacing, etc. The recommended PV system size is constrained "
                   "based on the sum of land area available, assuming the ground-mount power density specified here, and roofspace available, assuming the specified rooftop power density.")
    )
    production_factor_series = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list, blank=True,
        help_text=("Optional user-defined production factors. Must be normalized to units of kW-AC/kW-DC nameplate, "
                   "representing the AC power (kW) output per 1 kW-DC of system capacity in each time step. "
                   "The series must be one year (January through December) of hourly, 30-minute, or 15-minute PV "
                   "generation data.")
    )
    can_net_meter = models.BooleanField(
        blank=True,
        default = True,
        help_text=("True/False for if technology has option to participate in net metering agreement with utility. "
                   "Note that a technology can only participate in either net metering or wholesale rates (not both)."
                   "Note that if off-grid is true, net metering is always set to False.")
    )
    can_wholesale = models.BooleanField(
        blank=True,
        default = True,
        help_text=("True/False for if technology has option to export energy that is compensated at the wholesale_rate. "
                   "Note that a technology can only participate in either net metering or wholesale rates (not both)."
                   "Note that if off-grid is true, can_wholesale is always set to False.")
    )
    can_export_beyond_nem_limit = models.BooleanField(
        blank=True,
        default = True,
        help_text=("True/False for if technology can export energy beyond the annual site load (and be compensated for "
                   "that energy at the export_rate_beyond_net_metering_limit)."
                   "Note that if off-grid is true, can_export_beyond_nem_limit is always set to False.")
    )
    can_curtail = models.BooleanField(
        default=True,
        blank=True,
        help_text="True/False for if technology has the ability to curtail energy production."
    )

    operating_reserve_required_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        null=True,
        help_text=("Only applicable when off_grid_flag=True; defaults to 0.25 (25 pct) for off-grid scenarios and fixed at 0 otherwise." 
                "Required operating reserves applied to each timestep as a fraction of PV generation serving load in that timestep.")
    )


class PVOutputs(BaseModel, models.Model):
    key = "PVOutputs"
    meta = models.ForeignKey(
        to=APIMeta,
        on_delete=models.CASCADE,
        related_name="PVOutputs",
        unique=False
    )
    name = models.TextField(
        blank=True,
        default="PV",
        help_text="PV description for distinguishing between multiple PV models"
    )
    size_kw = models.FloatField(null=True, blank=True)
    installed_cost_per_kw = models.FloatField(null=True, blank=True)
    om_cost_per_kw = models.FloatField(null=True, blank=True)
    lifecycle_om_cost_after_tax = models.FloatField(null=True, blank=True)
    lifecycle_om_cost_after_tax_bau = models.FloatField(null=True, blank=True)
    lifecycle_om_cost_bau = models.FloatField(null=True, blank=True)
#     station_latitude = models.FloatField(null=True, blank=True)
#     station_longitude = models.FloatField(null=True, blank=True)
#     station_distance_km = models.FloatField(null=True, blank=True)
    annual_energy_produced_kwh = models.FloatField(null=True, blank=True)
    annual_energy_produced_kwh_bau = models.FloatField(null=True, blank=True)
    annual_energy_exported_kwh = models.FloatField(null=True, blank=True)
    year_one_energy_produced_kwh = models.FloatField(null=True, blank=True)
    year_one_energy_produced_kwh_bau = models.FloatField(null=True, blank=True)
    electric_to_storage_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )
    electric_to_load_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )
    electric_to_grid_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )
    electric_curtailed_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )
    lcoe_per_kwh = models.FloatField(null=True, blank=True)
    production_factor_series = ArrayField(
        models.FloatField(null=True, blank=True),
        default=list, blank=True
    )


class WindInputs(BaseModel, models.Model):
    key = "Wind"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="WindInputs",
        primary_key=True
    )

    class WIND_SIZE_CLASS_CHOICES(models.TextChoices):
        RESIDENTIAL = 'residential'
        COMMERCIAL = 'commercial'
        MEDIUM = 'medium'
        LARGE = 'large'
        BLANK = ""

    size_class = models.TextField(
        blank=True,
        choices=WIND_SIZE_CLASS_CHOICES.choices,
        default=WIND_SIZE_CLASS_CHOICES.BLANK,
        help_text=('Turbine size-class. One of ["residential", "commercial", "medium", "large"]. If not provided then '
                   'the size_class is determined based on the average electric load.')
    )
    wind_meters_per_sec = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True,
        default=list,
        help_text="Data downloaded from Wind ToolKit for modeling wind turbine."
    )
    wind_direction_degrees = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True,
        default=list,
        help_text="Data downloaded from Wind ToolKit for modeling wind turbine."
    )
    temperature_celsius = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True,
        default=list,
        help_text="Data downloaded from Wind ToolKit for modeling wind turbine."
    )
    pressure_atmospheres = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True,
        default=list,
        help_text="Data downloaded from Wind ToolKit for modeling wind turbine."
    )
    min_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Minimum PV size constraint for optimization"
    )
    max_kw = models.FloatField(
        default=1.0e9,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum size constraint for optimization."
    )
    installed_cost_per_kw = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e5)
        ],
        blank=True,
        null=True,
        help_text="Installed cost in $/kW. Default cost is determined based on size_class."
    )
    om_cost_per_kw = models.FloatField(
        default=42,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        help_text="Annual operations and maintenance costs in $/kW"
    )
    macrs_option_years = models.IntegerField(
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )
    macrs_bonus_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )
    macrs_itc_reduction = models.FloatField(
        default=0.5,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of the ITC value by which depreciable basis is reduced"
    )
    federal_itc_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percentage of capital costs that are credited towards federal taxes"
    )
    state_ibi_fraction = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percentage of capital costs offset by state incentives"
    )
    state_ibi_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum dollar value of state percentage-based capital cost incentive"
    )
    utility_ibi_fraction = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percentage of capital costs offset by utility incentives"
    )
    utility_ibi_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum dollar value of utility percentage-based capital cost incentive"
    )
    federal_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Federal rebates based on installed capacity"
    )
    state_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="State rebate based on installed capacity"
    )
    state_rebate_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum state rebate"
    )
    utility_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Utility rebate based on installed capacity"
    )
    utility_rebate_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum utility rebate"
    )
    production_incentive_per_kwh = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Production-based incentive value"
    )
    production_incentive_max_benefit = models.FloatField(
        default=1.0e9,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum annual value in present terms of production-based incentives"
    )
    production_incentive_years = models.IntegerField(
        default=1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        blank=True,
        help_text="Duration of production-based incentives from installation date"
    )
    production_incentive_max_kw = models.FloatField(
        default=1.0e9,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum system size eligible for production-based incentive"
    )
    production_factor_series = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list, blank=True,
        help_text=("Optional user-defined production factors. Must be normalized to units of kW-AC/kW-DC nameplate, "
                   "representing the AC power (kW) output per 1 kW-DC of system capacity in each time step. "
                   "The series must be one year (January through December) of hourly, 30-minute, or 15-minute  "
                   "generation data.")
    )
    can_net_meter = models.BooleanField(
        default=True,
        blank=True,
        help_text=("True/False for if technology has option to participate in net metering agreement with utility. "
                   "Note that a technology can only participate in either net metering or wholesale rates (not both)."
                   "Note that if off-grid is true, net metering is always set to False.")
    )
    can_wholesale = models.BooleanField(
        default=True,
        blank=True,
        help_text=("True/False for if technology has option to export energy that is compensated at the wholesale_rate. "
                   "Note that a technology can only participate in either net metering or wholesale rates (not both)."
                   "Note that if off-grid is true, can_wholesale is always set to False.")
    )
    can_export_beyond_nem_limit = models.BooleanField(
        default=True,
        blank=True,
        help_text=("True/False for if technology can export energy beyond the annual site load (and be compensated for "
                   "that energy at the export_rate_beyond_net_metering_limit)."
                   "Note that if off-grid is true, can_export_beyond_nem_limit is always set to False.")
    )
    can_curtail = models.BooleanField(
        default=True,
        blank=True,
        help_text="True/False for if technology has the ability to curtail energy production."
    )
    operating_reserve_required_fraction = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        null=True,
        blank=True,
        help_text="Only applicable when off_grid_flag=True; defaults to 0.5 (50 pct) for off-grid scenarios and fixed at 0 otherwise."
            "Required operating reserves applied to each timestep as a fraction of wind generation serving load in that timestep."
    )
    acres_per_kw = models.FloatField(
        default=0.03,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100.0)
        ],
        blank=True,
        help_text="Land area required per kW of wind capacity in acres/kW; only constrained by this for systems greater than 1500 kW"
    )

    def clean(self):
        if self.size_class != "" and self.installed_cost_per_kw is None:
            self.installed_cost_per_kw = WIND_COST_DEFAULTS.get(self.size_class, None) # will get set in REopt.jl if size_class not supplied

class WindOutputs(BaseModel, models.Model):
    key = "WindOutputs"
    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="WindOutputs",
        primary_key=True
    )

    size_kw = models.FloatField(null=True, blank=True)
    lifecycle_om_cost_after_tax = models.FloatField(null=True, blank=True)
    year_one_om_cost_before_tax = models.FloatField(null=True, blank=True)
    annual_energy_produced_kwh = models.FloatField(null=True, blank=True)
    annual_energy_exported_kwh = models.FloatField(null=True, blank=True)
    electric_to_storage_series_kw = ArrayField(
            models.FloatField(null=True, blank=True), blank=True, default=list)
    electric_to_load_series_kw = ArrayField(
            models.FloatField(null=True, blank=True), blank=True, default=list)
    electric_to_grid_series_kw = ArrayField(
            models.FloatField(null=True, blank=True), blank=True, default=list)
    electric_curtailed_series_kw = ArrayField(
            models.FloatField(null=True, blank=True), blank=True, default=list)
    lcoe_per_kwh = models.FloatField(null=True, blank=True)
    production_factor_series = ArrayField(
        models.FloatField(null=True, blank=True),
        default=list, blank=True
    )


class ElectricStorageInputs(BaseModel, models.Model):
    key = "ElectricStorage"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ElectricStorageInputs",
        primary_key=True
    )

    min_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Minimum storage inverter capacity constraint for optimization."
    )
    max_kw = models.FloatField(
        default=1.0e9,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum storage inverter capacity constraint for optimization."
    )
    min_kwh = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Minimum energy storage capacity constraint for optimization."
    )
    max_kwh = models.FloatField(
        default=1.0e6,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum energy storage capacity constraint for optimization."
    )
    internal_efficiency_fraction = models.FloatField(
        default=0.975,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Battery inherent efficiency independent of inverter and rectifier"
    )
    inverter_efficiency_fraction = models.FloatField(
        default=0.96,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Battery inverter efficiency"
    )
    rectifier_efficiency_fraction = models.FloatField(
        default=0.96,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Battery rectifier efficiency"
    )
    soc_min_fraction = models.FloatField(
        default=0.2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Minimum allowable battery state of charge as fraction of energy capacity."
    )
    soc_min_applies_during_outages = models.BooleanField(
        default=False,
        blank=True,
        help_text="Whether the minimum allowable battery state of charge is enforced during outages in addition to normal operations."
    )
    soc_init_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Battery state of charge at first hour of optimization as fraction of energy capacity."
    )
    can_grid_charge = models.BooleanField(
        blank=True,
        help_text="Flag to set whether the battery can be charged from the grid, or just onsite generation."
    )
    installed_cost_per_kw = models.FloatField(
        default=968.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e4)
        ],
        blank=True,
        help_text="Total upfront battery power capacity costs (e.g. inverter and balance of power systems)"
    )
    installed_cost_per_kwh = models.FloatField(
        default=253.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e4)
        ],
        blank=True,
        help_text="Total upfront battery costs"
    )
    installed_cost_constant = models.FloatField(
        default=222115.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Fixed upfront cost for battery installation, independent of size."
    )
    replace_cost_per_kw = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e4)
        ],
        blank=True,
        help_text="Battery power capacity replacement cost at time of replacement year"
    )
    replace_cost_per_kwh = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e4)
        ],
        blank=True,
        help_text="Battery energy capacity replacement cost at time of replacement year"
    )
    replace_cost_constant = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Fixed replacement cost for battery, independent of size."
    )
    inverter_replacement_year = models.IntegerField(
        default=10,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_YEARS)
        ],
        blank=True,
        help_text="Number of years from start of analysis period to replace inverter"
    )
    battery_replacement_year = models.IntegerField(
        default=10,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_YEARS)
        ],
        blank=True,
        help_text="Number of years from start of analysis period to replace battery"
    )
    cost_constant_replacement_year = models.IntegerField(
        default=10,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_YEARS)
        ],
        blank=True,
        help_text="Number of years from start of analysis period to apply replace_cost_constant."
    )
    om_cost_fraction_of_installed_cost = models.FloatField(
        default=0.025,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Annual O&M cost as a fraction of installed cost."
    )
    macrs_option_years = models.IntegerField(
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )
    macrs_bonus_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )
    macrs_itc_reduction = models.FloatField(
        default=0.5,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of the ITC value by which depreciable basis is reduced"
    )
    total_itc_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Total investment tax credit in percent applied toward capital costs"
    )
    total_rebate_per_kw = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Rebate based on installed power capacity"
    )
    total_rebate_per_kwh = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Rebate based on installed energy capacity"
    )
    min_duration_hours = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Minimum amount of time storage can discharge at its rated power capacity"
    )
    max_duration_hours = models.FloatField(
        default=100000.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum amount of time storage can discharge at its rated power capacity"
    )

    optimize_soc_init_fraction = models.BooleanField(
        default=False,
        blank=True,
        help_text="If true, soc_init_fraction will not apply. Model will optimize initial SOC and constrain initial SOC = final SOC."
    )


class ElectricStorageOutputs(BaseModel, models.Model):
    key = "ElectricStorageOutputs"
    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ElectricStorageOutputs",
        primary_key=True
    )
    size_kw = models.FloatField(null=True, blank=True)
    size_kwh = models.FloatField(null=True, blank=True)
    soc_series_fraction = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )
    storage_to_load_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )
    initial_capital_cost = models.FloatField(null=True, blank=True)
    maintenance_cost = models.FloatField(null=True, blank=True)
    state_of_health = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )


class GeneratorInputs(BaseModel, models.Model):
    key = "Generator"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="GeneratorInputs",
        primary_key=True
    )

    existing_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e5)
        ],
        blank=True,
        help_text="Existing diesel generator size"
    )
    min_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Minimum diesel generator size constraint for optimization"
    )
    max_kw = models.FloatField(
        default=1.0e9,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum diesel generator size constraint for optimization. Set to zero to disable PV"
    )
    installed_cost_per_kw = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0e5)
        ],
        blank=True,
        null=True,
        help_text="Installed diesel generator cost in $/kW"
    )
    om_cost_per_kw = models.FloatField( #depends on Settings.off_grid_flag
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        null=True,
        help_text="Annual diesel generator fixed operations and maintenance costs in $/kW"
    )
    om_cost_per_kwh = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        help_text="Diesel generator per unit production (variable) operations and maintenance costs in $/kWh"
    )
    fuel_cost_per_gallon = models.FloatField(
        default=2.25,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0e2)
        ],
        blank=True,
        help_text="Diesel cost in $/gallon"
    )
    electric_efficiency_half_load = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        null=True,
        help_text="Electric efficiency of the generator running at half load. Defaults to electric_efficiency_full_load."
    )
    electric_efficiency_full_load = models.FloatField(
        default=0.322,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Electric efficiency of the generator running at full load."
    )
    fuel_avail_gal = models.FloatField(
        default=MAX_BIG_NUMBER*10,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER*10)
        ],
        blank=True,
        null=True,
        help_text="On-site generator fuel available in gallons per year."
    )
    fuel_higher_heating_value_kwh_per_gal = models.FloatField(
        default=40.7,
        validators=[
            MinValueValidator(1e-6),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        blank=True,
        null=True,
        help_text="Higher heating value of the generator fuel in kWh/gal. Defaults to the HHV of diesel."
    )
    min_turn_down_fraction = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        null=True,
        help_text="Minimum generator loading in percent of capacity (size_kw)."
    )
    only_runs_during_grid_outage = models.BooleanField(
        default=True,
        blank=True,
        help_text="Determines if the generator can run only during grid outage or all the time."
    )
    sells_energy_back_to_grid = models.BooleanField(
        default=False,
        blank=True,
        help_text="Determines if generator can participate in NEM and wholesale markets."
    )
    macrs_option_years = models.IntegerField(
        default=MACRS_YEARS_CHOICES.ZERO,
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )
    macrs_bonus_fraction = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )
    macrs_itc_reduction = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of the ITC value by which depreciable basis is reduced"
    )
    federal_itc_fraction = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percentage of capital costs that are credited towards federal taxes"
    )
    state_ibi_fraction = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percentage of capital costs offset by state incentives"
    )
    state_ibi_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum dollar value of state percentage-based capital cost incentive"
    )
    utility_ibi_fraction = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percentage of capital costs offset by utility incentives"
    )
    utility_ibi_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum dollar value of utility percentage-based capital cost incentive"
    )
    federal_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Federal rebates based on installed capacity"
    )
    state_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="State rebate based on installed capacity"
    )
    state_rebate_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum state rebate"
    )
    utility_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Utility rebate based on installed capacity"
    )
    utility_rebate_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum utility rebate"
    )
    production_incentive_per_kwh = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Production-based incentive value"
    )
    production_incentive_max_benefit = models.FloatField(
        default=1.0e9,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum annual value in present terms of production-based incentives"
    )
    production_incentive_years = models.IntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        blank=True,
        help_text="Duration of production-based incentives from installation date"
    )
    production_incentive_max_kw = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum system size eligible for production-based incentive"
    )
    can_net_meter = models.BooleanField(
        default=False,
        blank=True,
        help_text=("True/False for if technology has option to participate in net metering agreement with utility. "
                   "Note that a technology can only participate in either net metering or wholesale rates (not both).")
    )
    can_wholesale = models.BooleanField(
        default=False,
        blank=True,
        help_text=("True/False for if technology has option to export energy that is compensated at the wholesale_rate. "
                   "Note that a technology can only participate in either net metering or wholesale rates (not both).")
    )
    can_export_beyond_nem_limit = models.BooleanField(
        default=False,
        blank=True,
        help_text=("True/False for if technology can export energy beyond the annual site load (and be compensated for "
                   "that energy at the export_rate_beyond_net_metering_limit).")
    )
    can_curtail = models.BooleanField(
        default=False,
        blank=True,
        help_text="True/False for if technology has the ability to curtail energy production."
    )
    fuel_renewable_energy_fraction = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Fraction of the generator fuel considered renewable."
    )
    emissions_factor_lb_CO2_per_gal = models.FloatField(
        default=22.58,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        help_text="Pounds of CO2e emitted per gallon of generator fuel burned."
    )
    emissions_factor_lb_NOx_per_gal = models.FloatField(
        default=0.0775544,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        help_text="Pounds of NOx emitted per gallon of generator fuel burned."
    )
    emissions_factor_lb_SO2_per_gal = models.FloatField(
        default=0.040020476,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        help_text="Pounds of SO2 emitted per gallon of generator fuel burned."
    )
    emissions_factor_lb_PM25_per_gal = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        help_text="Pounds of PM2.5 emitted per gallon of generator fuel burned."
    )
    replacement_year = models.IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        blank=True,
        null=True,
        help_text="Project year in which generator capacity will be replaced at a cost of replace_cost_per_kw."
    )
    replace_cost_per_kw = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER*10)
        ],
        blank=True,
        null=True,
        help_text="Per kW replacement cost for generator capacity. Replacement costs are considered tax deductible."
    )

    def clean(self):
        if not self.electric_efficiency_half_load:
            self.electric_efficiency_half_load = self.electric_efficiency_full_load



class GeneratorOutputs(BaseModel, models.Model):
    key = "GeneratorOutputs"
    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="GeneratorOutputs",
        primary_key=True
    )

    ## TODO: check all BAU outputs throughout.

    annual_fuel_consumption_gal = models.FloatField(null=True, blank=True)
    annual_fuel_consumption_gal_bau = models.FloatField(null=True, blank=True)
    size_kw = models.FloatField(null=True, blank=True)
    annual_energy_produced_kwh = models.FloatField(null=True, blank=True)
    electric_to_storage_series_kw = ArrayField(
            models.FloatField(null=True, blank=True), null=True, blank=True)
    electric_to_load_series_kw = ArrayField(
            models.FloatField(null=True, blank=True), null=True, blank=True, default=list)
    electric_to_grid_series_kw = ArrayField(
            models.FloatField(null=True, blank=True), null=True, blank=True, default=list)
    year_one_variable_om_cost_before_tax = models.FloatField(null=True, blank=True)
    year_one_variable_om_cost_before_tax_bau = models.FloatField(null=True, blank=True)
    year_one_fuel_cost_before_tax = models.FloatField(null=True, blank=True)
    year_one_fuel_cost_before_tax_bau = models.FloatField(null=True, blank=True)
    year_one_fuel_cost_after_tax = models.FloatField(null=True, blank=True)
    year_one_fuel_cost_after_tax_bau = models.FloatField(null=True, blank=True)    
    year_one_fixed_om_cost_before_tax = models.FloatField(null=True, blank=True)
    year_one_fixed_om_cost_before_tax_bau = models.FloatField(null=True, blank=True)
    lifecycle_variable_om_cost_after_tax = models.FloatField(null=True, blank=True)
    lifecycle_variable_om_cost_after_tax_bau = models.FloatField(null=True, blank=True)
    lifecycle_fuel_cost_after_tax = models.FloatField(null=True, blank=True)
    lifecycle_fuel_cost_after_tax_bau = models.FloatField(null=True, blank=True)
    lifecycle_fixed_om_cost_after_tax = models.FloatField(null=True, blank=True)
    lifecycle_fixed_om_cost_after_tax_bau = models.FloatField(null=True, blank=True)

class CHPInputs(BaseModel, models.Model):
    key = "CHP"
    meta = models.OneToOneField(
        to=APIMeta,
        on_delete=models.CASCADE,
        related_name="CHPInputs",
        unique=True
    )

    # Prime mover
    PRIME_MOVER = models.TextChoices('PRIME_MOVER', (
        "recip_engine",
        "micro_turbine",
        "combustion_turbine",
        "fuel_cell"
    ))

    FUEL_TYPE_LIST = models.TextChoices('FUEL_TYPE_LIST', (
        "natural_gas",
        "landfill_bio_gas",
        "propane",
        "diesel_oil"
    ))

    #Always required
    fuel_cost_per_mmbtu = ArrayField(
        models.FloatField(
            blank=True,
            validators=[
                MinValueValidator(0)
            ]
        ),
        default=list,
        null=False,
        blank=True,
        help_text=(
            "The `fuel_cost_per_mmbtu` is a required input and can be a scalar, a list of 12 monthly values, or a time series of values for every time step."
        )
    )

    # Prime mover - highly suggested, but not required
    prime_mover = models.TextField(
        null=True,
        blank=True,
        choices=PRIME_MOVER.choices,
        help_text="CHP prime mover, one of recip_engine, micro_turbine, combustion_turbine, fuel_cell"
    )
    # These are assigned using chp_defaults() logic by choosing prime_mover and size_class (if not supplied) based on average heating load
    installed_cost_per_kw = ArrayField(
            models.FloatField(null=True, blank=True), 
            default=list, 
            null=True,
            blank=True,
            help_text="Installed cost in $/kW"
    )
    tech_sizes_for_cost_curve = ArrayField(
            models.FloatField(null=True, blank=True), 
            default=list, 
            null=True,
            blank=True,
            help_text="Capacity intervals correpsonding to cost rates in installed_cost_per_kW, in kW"
    )
    om_cost_per_kwh = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0e3)
        ],
        null=True,
        blank=True,
        help_text="CHP per unit production (variable) operations and maintenance costs in $/kWh"
    )
    electric_efficiency_half_load = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        null=True, 
        blank=True,
        help_text="Electric efficiency of CHP prime-mover at half-load, HHV-basis"    
    )
    electric_efficiency_full_load = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        null=True, 
        blank=True,
        help_text="Electric efficiency of CHP prime-mover at full-load, HHV-basis"    
    )
    min_turn_down_fraction = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        null=True,
        help_text="Minimum CHP loading in fraction of capacity (size_kw)."
    )
    thermal_efficiency_full_load = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        null=True, 
        blank=True,
        help_text="CHP fraction of fuel energy converted to hot-thermal energy at full electric load"    
    )
    thermal_efficiency_half_load = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        null=True, 
        blank=True,
        help_text="CHP fraction of fuel energy converted to hot-thermal energy at half electric load"    
    )
    min_allowable_kw = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True, 
        blank=True,
        help_text="Minimum nonzero CHP size (in kWe) (i.e. it is possible to select no CHP system)"
    )
    max_kw = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True, 
        blank=True,
        help_text="Maximum CHP size (in kWe) constraint for optimization. Set to zero to disable CHP"
    )
    cooling_thermal_factor = models.FloatField(
        validators=[
            MinValueValidator(0.01),
            MaxValueValidator(1.0)
        ],
        null=True, 
        blank=True,
        help_text=(
            "Knockdown factor on absorption chiller COP based on the CHP prime_mover not being able to produce "
            "as high of temp/pressure hot water/steam"
        )
    )  # only needed with cooling load
    unavailability_periods = ArrayField(
            PickledObjectField(null=True, editable=True), 
            null=True,
            blank=True,
            help_text=(
                "CHP unavailability periods for scheduled and unscheduled maintenance, list of dictionaries with keys of "
                "['month', 'start_week_of_month', 'start_day_of_week', 'start_hour', 'duration_hours'] "
                "all values are one-indexed and start_day_of_week uses 1 for Monday, 7 for Sunday"
            )
            
    )
    # Optional inputs
    size_class = models.IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(7)
        ],
        null=True,
        blank=True,
        help_text="CHP size class. Must be an integer value between 0 and 7"
    )
    min_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Minimum CHP size constraint for optimization"
    )
    fuel_type = models.TextField(
        null=False,
        blank=True,
        choices=FUEL_TYPE_LIST.choices,
        default="natural_gas",
        help_text="Existing CHP fuel type, one of natural_gas, landfill_bio_gas, propane, diesel_oil"
    )
    om_cost_per_kw = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        null=True,
        help_text="Annual CHP fixed operations and maintenance costs in $/kW"
    )
    om_cost_per_hr_per_kw_rated = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        help_text="CHP system per-operating-hour (variable) operations and maintenance costs in $/hr-kW"
    )
    supplementary_firing_capital_cost_per_kw = models.FloatField(
        default=150,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0e5)
        ],
        null=True, 
        blank=True,
        help_text="Installed CHP supplementary firing system cost in $/kWe"
    )
    supplementary_firing_max_steam_ratio = models.FloatField(
        default=1.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(10.0)
        ],
        null=True, 
        blank=True,
        help_text="Ratio of max fired steam to un-fired steam production. Relevant only for combustion_turbine prime_mover"
    )
    supplementary_firing_efficiency =models.FloatField(
        default=0.92,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        null=True, 
        blank=True,
        help_text=(
            "Thermal efficiency of the incremental steam production from supplementary firing. Relevant only for "
            "combustion_turbine prime_mover"
        )
    )
    standby_rate_per_kw_per_month = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1000)
        ],
        null=True, 
        blank=True,
        help_text=("Standby rate charged to CHP based on CHP electric power size")
    )
    reduces_demand_charges = models.BooleanField(
        default=True,
        null=True,
        blank=True,
        help_text=("Boolean indicator if CHP reduces demand charges")
    )
    can_supply_steam_turbine = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CHP can supply steam to the steam turbine for electric production"   
    )
    serve_absorption_chiller_only = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CHP produced heat either serves absorption chiller or sends it to waste"   
    )
    months_serving_absorption_chiller_only = ArrayField(
        models.IntegerField(
            validators=[
                MinValueValidator(1),
                MaxValueValidator(12)
            ],
            null=True, blank=True
        ),
        default=list, blank=True,
        help_text="Months of the year in which the CHP only serves the absorption chiller load, only used if serve_absorption_chiller_only is True"
    )
    include_cooling_in_chp_size = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Boolean indicator if cooling load (via absorption chiller) is included in the heuristic CHP sizing calculation along with heating loads"   
    )    
    follow_electrical_load = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CHP follows the electrical load by running at capacity or meeting the load only"   
    )
    can_serve_dhw = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CHP can serve  hot water load"   
    )
    can_serve_space_heating = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CHP can serve space heating load"   
    )
    can_serve_process_heat = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CHP can serve process heat load"   
    )


    #Financial and emissions    
    macrs_option_years = models.IntegerField(
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )
    macrs_bonus_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )
    macrs_itc_reduction = models.FloatField(
        default=0.5,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of the ITC value by which depreciable basis is reduced"
    )
    federal_itc_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percentage of capital costs that are credited towards federal taxes"
    )
    federal_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Federal rebates based on installed capacity"
    )
    state_ibi_fraction = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percentage of capital costs offset by state incentives"
    )
    state_ibi_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum dollar value of state percentage-based capital cost incentive"
    )
    state_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="State rebate based on installed capacity"
    )
    state_rebate_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum state rebate"
    )
    utility_ibi_fraction = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percentage of capital costs offset by utility incentives"
    )
    utility_ibi_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum dollar value of utility percentage-based capital cost incentive"
    )
    utility_rebate_per_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Utility rebate based on installed capacity"
    )
    utility_rebate_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum utility rebate"
    )
    production_incentive_per_kwh = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Production-based incentive value"
    )
    production_incentive_max_benefit = models.FloatField(
        default=1.0e9,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum annual value in present terms of production-based incentives"
    )
    production_incentive_years = models.IntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        blank=True,
        help_text="Duration of production-based incentives from installation date"
    )
    production_incentive_max_kw = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum system size eligible for production-based incentive"
    )
    can_net_meter = models.BooleanField(
        default=False,
        blank=True,
        help_text=("True/False for if technology has option to participate in net metering agreement with utility. "
                   "Note that a technology can only participate in either net metering or wholesale rates (not both).")
    )
    can_wholesale = models.BooleanField(
        default=False,
        blank=True,
        help_text=("True/False for if technology has option to export energy that is compensated at the wholesale_rate. "
                   "Note that a technology can only participate in either net metering or wholesale rates (not both).")
    )
    can_export_beyond_nem_limit = models.BooleanField(
        default=False,
        blank=True,
        help_text=("True/False for if technology can export energy beyond the annual site load (and be compensated for "
                   "that energy at the export_rate_beyond_net_metering_limit).")
    )
    can_curtail = models.BooleanField(
        default=False,
        blank=True,
        help_text="True/False for if technology has the ability to curtail energy production."
    )
    fuel_renewable_energy_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Fraction of the CHP fuel considered renewable. Default depends on fuel type."
    )
    emissions_factor_lb_CO2_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        null=True,
        help_text="Pounds of CO2 emitted per MMBTU of CHP fuel burned."
    )
    emissions_factor_lb_NOx_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        null=True,
        help_text="Pounds of CO2 emitted per MMBTU of CHP fuel burned."
    )
    emissions_factor_lb_SO2_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        null=True,
        help_text="Pounds of CO2 emitted per MMBTU of CHP fuel burned."
    )
    emissions_factor_lb_PM25_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        null=True,
        help_text="Pounds of CO2 emitted per MMBTU of CHP fuel burned."
    )
    
    def clean(self):
        error_messages = {}
        if not self.dict.get("fuel_cost_per_mmbtu"):
            error_messages["required inputs"] = "Must provide fuel_cost_per_mmbtu to model {}".format(self.key)

        if error_messages:
            raise ValidationError(error_messages)

        self.fuel_cost_per_mmbtu = scalar_or_monthly_to_8760(self.fuel_cost_per_mmbtu)

        if self.fuel_renewable_energy_fraction == None:
            self.fuel_renewable_energy_fraction = FUEL_DEFAULTS["fuel_renewable_energy_fraction"].get(self.fuel_type, 0.0)

        if self.emissions_factor_lb_CO2_per_mmbtu == None:
            self.emissions_factor_lb_CO2_per_mmbtu = FUEL_DEFAULTS["emissions_factor_lb_CO2_per_mmbtu"].get(self.fuel_type, 0.0)
        
        if self.emissions_factor_lb_SO2_per_mmbtu == None:
            self.emissions_factor_lb_SO2_per_mmbtu = FUEL_DEFAULTS["emissions_factor_lb_SO2_per_mmbtu"].get(self.fuel_type, 0.0)
        
        if self.emissions_factor_lb_NOx_per_mmbtu == None:
            self.emissions_factor_lb_NOx_per_mmbtu = FUEL_DEFAULTS["emissions_factor_lb_NOx_per_mmbtu"].get(self.fuel_type, 0.0)
        
        if self.emissions_factor_lb_PM25_per_mmbtu == None:
            self.emissions_factor_lb_PM25_per_mmbtu = FUEL_DEFAULTS["emissions_factor_lb_PM25_per_mmbtu"].get(self.fuel_type, 0.0)


class CHPOutputs(BaseModel, models.Model):
    key = "CHPOutputs"
    meta = models.OneToOneField(
        to=APIMeta,
        on_delete=models.CASCADE,
        related_name="CHPOutputs",
        unique=True
    )
    
    size_kw = models.FloatField(
        null=True, blank=True,
        help_text="Power capacity size of the CHP system [kW]"
    )
    size_supplemental_firing_kw = models.FloatField(
        null=True, blank=True,
        help_text="Power capacity of CHP supplementary firing system [kW]"
    )
    annual_fuel_consumption_mmbtu = models.FloatField(
        null=True, blank=True,
        help_text="Fuel consumed in a year [MMBtu]"
    )
    annual_electric_production_kwh = models.FloatField(
        null=True, blank=True,
        help_text="Electric energy produced in a year [kWh]"
    )
    annual_thermal_production_mmbtu = models.FloatField(
        null=True, blank=True,
        help_text="Thermal energy produced in a year [MMBtu]"
    )
    electric_production_series_kw = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list, blank=True,
        help_text="Electric power production time-series array [kW]"
    )
    electric_to_grid_series_kw = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list, blank=True,
        help_text="Electric power exported time-series array [kW]"
    )
    electric_to_storage_series_kw = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list, blank=True,
        help_text="Electric power to charge the battery storage time-series array [kW]"
    )
    electric_to_load_series_kw = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list, blank=True,
        help_text="Electric power serving the electric load time-series array [kW]"
    )
    thermal_to_storage_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list, blank=True,
        help_text="Thermal power to TES time-series array [MMBtu/hr]"
    )
    thermal_curtailed_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list, blank=True,
        help_text="Thermal power wasted/unused/vented time-series array [MMBtu/hr]"
    )
    thermal_to_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list, blank=True,
        help_text="Thermal power to serve the heating load time-series array [MMBtu/hr]"
    )
    thermal_to_steamturbine_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list, blank=True,
        help_text="Thermal power to steam turbine time-series array [MMBtu/hr]"
    )    
    thermal_to_absorption_chiller_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            null=True, blank=True
        ),
        default=list,
        help_text="Thermal power to absorption chiller time-series array [MMBtu/hr]"
    )    
    year_one_fuel_cost_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="Cost of fuel consumed by the CHP system in year one [$]"
    )
    year_one_fuel_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Cost of fuel consumed by the CHP system in year one, after tax [$]"
    )    
    lifecycle_fuel_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Present value of cost of fuel consumed by the CHP system, after tax [$]"
    )
    year_one_standby_cost_before_tax = models.FloatField(
        null=True, blank=True,
        help_text="CHP standby charges in year one [$]"
    )
    year_one_standby_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="CHP standby charges in year one, after tax [$]"
    )    
    lifecycle_standby_cost_after_tax = models.FloatField(
        null=True, blank=True,
        help_text="Present value of all CHP standby charges, after tax."
    )
    thermal_production_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )
    thermal_to_dhw_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )
    thermal_to_space_heating_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )
    thermal_to_process_heat_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )
    initial_capital_costs = models.FloatField(
        null=True, blank=True,
        help_text="Initial capital costs of the CHP system, before incentives [$]"
    )

    def clean():
        pass

class Message(BaseModel, models.Model):
    """
    For Example:
    {"messages":{
                "warnings": "This is a warning message.",
                "error": "REopt had an error."
                }
    }
    """
    meta = models.ForeignKey(
        APIMeta,
        on_delete=models.CASCADE,
        unique=False,
        related_name="Message"
    )
    message_type = models.TextField(default='')
    message = models.TextField(default='')

# TODO other necessary models from reo/models.py

class CoolingLoadInputs(BaseModel, models.Model):
    
    key = "CoolingLoad"
    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="CoolingLoadInputs",
        primary_key=True
    )
	
    possible_sets = [
        ["thermal_loads_ton"],
        ["doe_reference_name"],
        ["blended_doe_reference_names", "blended_doe_reference_percents"],
        ["annual_fraction_of_electric_load"],
        ["monthly_fractions_of_electric_load"],
        ["per_time_step_fractions_of_electric_load"],
        []
	]
	
    DOE_REFERENCE_NAME = models.TextChoices('DOE_REFERENCE_NAME', (
        'FastFoodRest '
        'FullServiceRest '
        'Hospital '
        'LargeHotel '
        'LargeOffice '
        'MediumOffice '
        'MidriseApartment '
        'Outpatient '
        'PrimarySchool '
        'RetailStore '
        'SecondarySchool '
        'SmallHotel '
        'SmallOffice '
        'StripMall '
        'Supermarket '
        'Warehouse '
        'FlatLoad '
        'FlatLoad_24_5 '
        'FlatLoad_16_7 '
        'FlatLoad_16_5 '
        'FlatLoad_8_7 '
        'FlatLoad_8_5'
    ))

    doe_reference_name = models.TextField(
        null=False,
        blank=True,
        choices=DOE_REFERENCE_NAME.choices,
        help_text=("Building type to use in selecting a simulated load profile from DOE "
                    "<a href='https: //energy.gov/eere/buildings/commercial-reference-buildings' target='blank'>Commercial Reference Buildings</a>."
                    "By default, the doe_reference_name of the ElectricLoad is used.")
	    )

    blended_doe_reference_names = ArrayField(
        models.TextField(
            choices=DOE_REFERENCE_NAME.choices,
            blank=True
        ),
        default=list,
        blank=True,
        help_text=("Used in concert with blended_doe_reference_percents to create a blended load profile from multiple "
                   "DoE Commercial Reference Buildings.")
    )

    blended_doe_reference_percents = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=("Used in concert with blended_doe_reference_names to create a blended load profile from multiple "
                   "DoE Commercial Reference Buildings to simulate buildings/campuses. Must sum to 1.0.")
    )

    annual_tonhour = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0e9)
        ],
        null=True,
        blank=True,
        help_text=("Annual electric chiller thermal energy production, in [Ton-Hour],"
                    "used to scale simulated default electric chiller load profile for the site's climate zone")
    )

    monthly_tonhour = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list,
        blank=True,
        help_text=("Monthly site space cooling requirement in [Ton-Hour], used "
                   "to scale simulated default building load profile for the site's climate zone")
    )

    thermal_loads_ton = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        help_text=("Typical electric chiller thermal production to serve the load for all hours in one year. Must be hourly (8,760 samples), 30 minute (17,"
                   "520 samples), or 15 minute (35,040 samples)."
                   )
    )

    year = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(9999)
        ],
        null=True, blank=True,
        help_text=("Year of Custom Load Profile. If a custom load profile is uploaded via the thermal_loads_ton parameter, it "
                   "is important that this year correlates with the electric load profile so that weekdays/weekends are "
                   "determined correctly for the utility rate tariff. If a DOE Reference Building profile (aka "
                   "'simulated' profile) is used, the year is set to 2017 since the DOE profiles start on a Sunday.")
    )    

    annual_fraction_of_electric_load = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        null=True,
        blank=True,
        help_text=("Annual electric chiller energy consumption scalar as a fraction of total electric load applied to every time step"
                "used to scale simulated default electric chiller load profile for the site's climate zone"
        )
    )

    monthly_fractions_of_electric_load = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Monthly fraction of site's total electric consumption used up by electric chiller, applied to every hour of each month,"
                    "to scale simulated default building load profile for the site's climate zone")
    )

    per_time_step_fractions_of_electric_load = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        help_text=("Per timestep fraction of site's total electric consumption used up by electric chiller."
                    "Must be hourly (8,760 samples), 30 minute (17,520 samples), or 15 minute (35,040 samples)."
                   )
    )		

    def clean(self):
        error_messages = {}

        # possible sets for defining load profile
        if not at_least_one_set(self.dict, self.possible_sets):
            error_messages["required inputs"] = \
                "Must provide at least one set of valid inputs from {}.".format(self.possible_sets)

        if len(self.blended_doe_reference_names) > 0 and self.doe_reference_name == "":
            if len(self.blended_doe_reference_names) != len(self.blended_doe_reference_percents):
                error_messages["blended_doe_reference_names"] = \
                    "The number of blended_doe_reference_names must equal the number of blended_doe_reference_percents."
            if not math.isclose(sum(self.blended_doe_reference_percents),  1.0):
                error_messages["blended_doe_reference_percents"] = "Sum must = 1.0."
        
        if len(self.monthly_fractions_of_electric_load) > 0:
            if len(self.monthly_fractions_of_electric_load) != 12:
                error_messages["monthly_fractions_of_electric_load"] = \
                    "Provided cooling monthly_fractions_of_electric_load array does not have 12 values."
        
        # Require 12 values if monthly_tonhours is provided.
        if 12 > len(self.monthly_tonhour) > 0:
            error_messages["required inputs"] = \
                "Must provide 12 elements as inputs to monthly_tonhour. Received {}.".format(self.monthly_tonhour)

        if error_messages:
            raise ValidationError(error_messages)
        
        pass


class ExistingChillerInputs(BaseModel, models.Model):
    
    key = "ExistingChiller"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ExistingChillerInputs",
        primary_key=True
    )

    cop = models.FloatField(
        validators=[
            MinValueValidator(0.01),
            MaxValueValidator(20)
        ],
        null=True,
        blank=True,
        help_text=("Existing electric chiller system coefficient of performance (COP) "
                    "(ratio of usable cooling thermal energy produced per unit electric energy consumed)")
    )

    max_thermal_factor_on_peak_load = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0)
        ],
        default=1.25,
        blank=True,
        help_text=("Factor on peak thermal LOAD which the electric chiller can supply. "
                    "This accounts for the assumed size of the electric chiller which typically has a safety factor above the peak load."
                    "This factor limits the max production which could otherwise be exploited with ColdThermalStorage")
    )

    retire_in_optimal = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if the existing chiller is unavailable in the optimal case (still used in BAU)"   
    )

    installed_cost_per_ton = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        help_text="Thermal power capacity-based cost incurred in BAU and only based on what's needed in Optimal scenario"
    )    

    installed_cost_dollars = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        help_text="Cost incurred in BAU scenario, as well as Optimal if needed still, in dollars"
    )

    def clean(self):
        pass


class ExistingChillerOutputs(BaseModel, models.Model):
    
    key = "ExistingChillerOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ExistingChillerOutputs",
        primary_key=True
    )

    size_ton = models.FloatField(null=True, blank=True)
    size_ton_bau = models.FloatField(null=True, blank=True)

    thermal_to_storage_series_ton = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        null=True,
        help_text=("Annual hourly time series of electric chiller thermal to cold TES [Ton]")
    )

    thermal_to_load_series_ton = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        null=True,
        help_text=("Annual hourly time series of electric chiller thermal to cooling load [Ton]")
    )

    electric_consumption_series_kw = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        null=True,
        help_text=("Annual hourly time series of chiller electric consumption [kW]")
    )

    annual_electric_consumption_kwh = models.FloatField(
        null=True,
        blank=True,
        help_text=("Annual chiller electric consumption [kWh]")
    )

    annual_electric_consumption_kwh_bau = models.FloatField(
        null=True,
        blank=True,
        help_text=("Annual chiller electric consumption for BAU case [kWh]")
    )    

    annual_thermal_production_tonhour = models.FloatField(
        null=True,
        blank=True,
        help_text=("Annual chiller thermal production [Ton Hour]")
    )

    annual_thermal_production_tonhour_bau = models.FloatField(
        null=True,
        blank=True,
        help_text=("Annual chiller thermal production for BAU case [Ton Hour]")
    )        

    def clean(self):
        pass
	
class ExistingBoilerInputs(BaseModel, models.Model):
    
    key = "ExistingBoiler"
    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
		related_name="ExistingBoilerInputs",
        primary_key=True
    )
	
    PRODUCTION_TYPE = models.TextChoices('PRODUCTION_TYPE', (
        'steam',
        'hot_water'
    ))

    FUEL_TYPE_LIST = models.TextChoices('FUEL_TYPE_LIST', (
        "natural_gas",
        "landfill_bio_gas",
        "propane",
        "diesel_oil"
    ))

    '''
    This field is populated based on heating loads provided via domestic hot water and space heating loads. TODO test with flexibleHVAC
    max_heat_demand_kw = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        null=True,
        blank=True,
        help_text=""
    )
    '''

    production_type = models.TextField(
        blank=True,
        null=False,
        choices=PRODUCTION_TYPE.choices,
        default="hot_water",
        help_text="Boiler thermal production type, hot water or steam"
    )

    max_thermal_factor_on_peak_load = models.FloatField(
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(5.0)
        ],
        null=True,
        blank=True,
        default=1.25,
        help_text="Factor on peak thermal LOAD which the boiler can supply"
    )

    efficiency = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        null=True,
        blank=True,
        help_text="Existing boiler system efficiency - conversion of fuel to usable heating thermal energy."
    )

    retire_in_optimal = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if the existing boiler is unavailable in the optimal case (still used in BAU)"   
    )

    fuel_renewable_energy_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Fraction of the fuel considered renewable. Default depends on fuel type."
    )

    emissions_factor_lb_CO2_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text="Pounds of CO2e emitted per MMBTU of fuel burned."
    )

    emissions_factor_lb_NOx_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text="Pounds of NOx emitted per MMBTU of fuel burned."
    )

    emissions_factor_lb_SO2_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text="Pounds of SO2 emitted per MMBTU of fuel burned."
    )

    emissions_factor_lb_PM25_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text="Pounds of PM2.5 emitted per MMBTU fuel burned."
    )

    fuel_cost_per_mmbtu = ArrayField(
        models.FloatField(
            blank=True,
            validators=[
                MinValueValidator(0)
            ]
        ),
        default=list,
        blank=True,
        help_text=("The ExistingBoiler default operating cost is zero. Please provide this field to include non-zero BAU heating costs."
                    "The `fuel_cost_per_mmbtu` can be a scalar, a list of 12 monthly values, or a time series of values for every time step."
                    "If a vector of length 8760, 17520, or 35040 is provided, it is adjusted to match timesteps per hour in the optimization.")
    )

    fuel_type = models.TextField(
        null=False,
        blank=True,
        choices=FUEL_TYPE_LIST.choices,
        default="natural_gas",
        help_text="Existing boiler fuel type, one of natural_gas, landfill_bio_gas, propane, diesel_oil"
    )


    installed_cost_per_mmbtu_per_hour = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        help_text="Thermal power capacity-based cost incurred in BAU and only based on what's needed in Optimal scenario"
    )    

    installed_cost_dollars = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        help_text="Cost incurred in BAU scenario, as well as Optimal if needed still, in dollars"
    )

    can_supply_steam_turbine = models.BooleanField(
        default=False,
        blank=True,
        null=True,
        help_text="If the boiler can supply steam to the steam turbine for electric production"
    )

    can_serve_dhw = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if the existing boiler can serve domestic hot water load"   
    )

    can_serve_space_heating = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if the existing boiler can serve space heating load"   
    )

    can_serve_process_heat = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if the existing boiler can serve process heat load"   
    )

    # For custom validations within model.
    def clean(self):
        error_messages = {}
        if not self.dict.get("fuel_cost_per_mmbtu"):
            error_messages["required inputs"] = "Must provide fuel_cost_per_mmbtu to model {}".format(self.key)

        if error_messages:
            raise ValidationError(error_messages)
        
        self.fuel_cost_per_mmbtu = scalar_or_monthly_to_8760(self.fuel_cost_per_mmbtu)

        if self.fuel_renewable_energy_fraction == None:
            self.fuel_renewable_energy_fraction = FUEL_DEFAULTS["fuel_renewable_energy_fraction"].get(self.fuel_type, 0.0)

        if self.emissions_factor_lb_CO2_per_mmbtu == None:
            self.emissions_factor_lb_CO2_per_mmbtu = FUEL_DEFAULTS["emissions_factor_lb_CO2_per_mmbtu"].get(self.fuel_type, 0.0)
        
        if self.emissions_factor_lb_SO2_per_mmbtu == None:
            self.emissions_factor_lb_SO2_per_mmbtu = FUEL_DEFAULTS["emissions_factor_lb_SO2_per_mmbtu"].get(self.fuel_type, 0.0)
        
        if self.emissions_factor_lb_NOx_per_mmbtu == None:
            self.emissions_factor_lb_NOx_per_mmbtu = FUEL_DEFAULTS["emissions_factor_lb_NOx_per_mmbtu"].get(self.fuel_type, 0.0)
        
        if self.emissions_factor_lb_PM25_per_mmbtu == None:
            self.emissions_factor_lb_PM25_per_mmbtu = FUEL_DEFAULTS["emissions_factor_lb_PM25_per_mmbtu"].get(self.fuel_type, 0.0)

class ExistingBoilerOutputs(BaseModel, models.Model):
    
    key = "ExistingBoilerOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ExistingBoilerOutputs",
        primary_key=True
    )

    size_mmbtu_per_hour = models.FloatField(null=True, blank=True)
    size_mmbtu_per_hour_bau = models.FloatField(null=True, blank=True)
    annual_fuel_consumption_mmbtu = models.FloatField(null=True, blank=True)
    annual_fuel_consumption_mmbtu_bau = models.FloatField(null=True, blank=True)

    fuel_consumption_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default=list,
    )

    lifecycle_fuel_cost_after_tax = models.FloatField(null=True, blank=True)
    lifecycle_fuel_cost_after_tax_bau = models.FloatField(null=True, blank=True)
    annual_thermal_production_mmbtu = models.FloatField(null=True, blank=True)
    annual_thermal_production_mmbtu_bau = models.FloatField(null=True, blank=True)
    year_one_fuel_cost_before_tax = models.FloatField(null=True, blank=True)
    year_one_fuel_cost_after_tax = models.FloatField(null=True, blank=True)
    year_one_fuel_cost_before_tax_bau = models.FloatField(null=True, blank=True)
    year_one_fuel_cost_after_tax_bau = models.FloatField(null=True, blank=True)

    thermal_to_storage_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_to_steamturbine_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_production_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_to_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_to_absorption_chiller_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_dhw_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_space_heating_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_process_heat_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    def clean(self):
        # perform custom validation here.
        pass

class ElectricHeaterInputs(BaseModel, models.Model):
    key = "ElectricHeater"
    meta = models.OneToOneField(
        to=APIMeta,
        on_delete=models.CASCADE,
        related_name="ElectricHeaterInputs",
        primary_key=True
    )
    
    min_mmbtu_per_hour = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        default=0.0,
        help_text="Minimum thermal power size"
    )

    max_mmbtu_per_hour = models.FloatField(
        null=True,
        blank=True,        
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        default=1.0E7,
        help_text="Maximum thermal power size"
    )

    installed_cost_per_mmbtu_per_hour = models.FloatField(
        default=154902.0,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        help_text="Thermal power-based cost"
    )

    om_cost_per_mmbtu_per_hour = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        help_text="Thermal power-based fixed O&M cost"
    )

    macrs_option_years = models.IntegerField(
        default=MACRS_YEARS_CHOICES.ZERO,
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )

    macrs_bonus_fraction = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )

    cop = models.FloatField(
        validators=[
            MinValueValidator(0.01),
            MaxValueValidator(20)
        ],
        default=1.0,
        null=True,
        blank=True,
        help_text=("Electric heater system coefficient of performance (COP) "
                    "(ratio of usable thermal energy produced per unit electric energy consumed)")
    )

    can_supply_steam_turbine = models.BooleanField(
        default=True,
        blank=True,
        null=True,
        help_text="If the boiler can supply steam to the steam turbine for electric production"
    )

    can_serve_dhw = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if the electric heater can serve domestic hot water load"   
    )

    can_serve_space_heating = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if the electric heater can serve space heating load"   
    )

    can_serve_process_heat = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if the electric heater can serve process heat load"   
    )

class ElectricHeaterOutputs(BaseModel, models.Model):
    key = "ElectricHeaterOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ElectricHeaterOutputs",
        primary_key=True
    )

    size_mmbtu_per_hour = models.FloatField(null=True, blank=True)
    annual_electric_consumption_kwh = models.FloatField(null=True, blank=True)

    electric_consumption_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        default=list,
    )

    annual_thermal_production_mmbtu = models.FloatField(null=True, blank=True)

    thermal_to_storage_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_to_steamturbine_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_production_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_to_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_to_absorption_chiller_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_dhw_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_space_heating_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_process_heat_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_high_temp_thermal_storage_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

class ASHPSpaceHeaterInputs(BaseModel, models.Model):
    key = "ASHPSpaceHeater"
    meta = models.OneToOneField(
        to=APIMeta,
        on_delete=models.CASCADE,
        related_name="ASHPSpaceHeaterInputs",
        primary_key=True
    )
    
    min_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default = 0.0,
        help_text=("Minimum thermal power size constraint for optimization [ton]")
    )

    max_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Maximum thermal power size constraint for optimization [ton]")
    )

    min_allowable_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Minimum nonzero thermal power size constraint for optimization [ton]")
    )

    min_allowable_peak_capacity_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Minimum nonzero thermal power as a fucniton of coincident peak load - constraint for optimization [ton]")
    )

    sizing_factor = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Size of system relative to max dispatch output [fraction]")
    )
    
    
    installed_cost_per_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Thermal power-based cost of ASHP space heater [$/ton] (3.5 ton to 1 kWt)")
    )

    om_cost_per_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Thermal power-based cost of ASHP space heater [$/ton] (3.5 ton to 1 kWt)")
    )

    macrs_option_years = models.IntegerField(
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )

    macrs_bonus_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )

    heating_cop_reference = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(20.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=(("Reference points for ASHP space heating system heating coefficient of performance (COP) "
                    "(ratio of usable heating thermal energy produced per unit electric energy consumed)"))
    )

    heating_cf_reference = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(20.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=(("Reference points for ASHP space heating system heating capac)ity factor"
                    "(ratio of heating thermal power to rated capacity)"))
    )

    heating_reference_temps_degF = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(-275),
                MaxValueValidator(200.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=(("Reference temperatures for ASHP space heating system's heating COP and CF"))
    )

    cooling_cop_reference = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(20.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=(("Reference points for ASHP space heating system cooling coefficient of performance (COP) "
                    "(ratio of usable heating thermal energy produced per unit electric energy consumed)"))
    )

    cooling_cf_reference = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(20.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=(("Reference points for ASHP space heating system cooling capac)ity factor"
                    "(ratio of heating thermal power to rated capacity)"))
    )

    cooling_reference_temps_degF = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(-275),
                MaxValueValidator(200.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=(("Reference temperatures for ASHP space heating system's cooling COP and CF"))
    )

    can_serve_cooling = models.BooleanField(
        null=True, 
        blank=True,
        help_text="Boolean indicator if ASHP space heater can serve cooling load"   
    )

    force_into_system = models.BooleanField(
        null=True, 
        blank=True,
        help_text="Boolean indicator if ASHP space heater serves compatible thermal loads exclusively in optimized scenario"   
    )

    force_dispatch = models.BooleanField(
        null=True, 
        default=True,
        help_text="Boolean indicator that ASHP space heater outputs either maximum capacity or site load if true"   
    )

    avoided_capex_by_ashp_present_value = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default = 0.0,
        help_text=("net present value of avoided capital expenditures due to ASHP system being present [$]")
    )

    back_up_temp_threshold_degF = models.FloatField(
        validators=[
            MinValueValidator(-275.0),
            MaxValueValidator(200.0)
        ],
        null=True,
        blank=True,
        help_text=("Temperature threshold below which resistive back-up heater turns on [Fahrenheit]")
    )

    def clean(self):
        error_messages = {}
        if self.dict.get("min_allowable_ton") in [None, "", []] and self.dict.get("min_allowable_peak_capacity_fraction") in [None, "", []]:
            self.min_allowable_peak_capacity_fraction = 0.25

        if self.dict.get("min_allowable_ton") not in [None, "", []] and self.dict.get("min_allowable_peak_capacity_fraction") not in [None, "", []]:
            error_messages["bad inputs"] = "At most one of min_allowable_ton and min_allowable_peak_capacity_fraction may be input to model {}".format(self.key)

        if len(self.dict.get("heating_cop_reference")) != len(self.dict.get("heating_cf_reference")) or len(self.dict.get("heating_cop_reference")) != len(self.dict.get("heating_reference_temps_degF")):
            error_messages["mismatched length"] = "Model {} inputs heating_cop_reference, heating_cf_reference, and heating_reference_temps_degF must all have the same length.".format(self.key)

        if len(self.dict.get("cooling_cop_reference")) != len(self.dict.get("cooling_cf_reference")) or len(self.dict.get("cooling_cop_reference")) != len(self.dict.get("cooling_reference_temps_degF")):
            error_messages["mismatched length"] = "Model {} inputs cooling_cop_reference, cooling_cf_reference, and cooling_reference_temps_degF must all have the same length.".format(self.key)

        if error_messages:
            raise ValidationError(error_messages)



class ASHPSpaceHeaterOutputs(BaseModel, models.Model):
    key = "ASHPSpaceHeaterOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ASHPSpaceHeaterOutputs",
        primary_key=True
    )

    size_ton = models.FloatField(null=True, blank=True)
    annual_electric_consumption_kwh = models.FloatField(null=True, blank=True)

    electric_consumption_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        default=list
    )

    annual_thermal_production_mmbtu = models.FloatField(null=True, blank=True)
    annual_thermal_production_tonhour = models.FloatField(null=True, blank=True)

    thermal_to_storage_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_production_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_space_heating_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_storage_series_ton = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_load_series_ton = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    heating_cop = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    heating_cf = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    cooling_cop = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    cooling_cf = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    electric_consumption_for_cooling_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    electric_consumption_for_heating_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    annual_electric_consumption_for_cooling_kwh = models.FloatField(null=True, blank=True)
    annual_electric_consumption_for_heating_kwh = models.FloatField(null=True, blank=True)

class ASHPWaterHeaterInputs(BaseModel, models.Model):
    key = "ASHPWaterHeater"
    meta = models.OneToOneField(
        to=APIMeta,
        on_delete=models.CASCADE,
        related_name="ASHPWaterHeaterInputs",
        primary_key=True
    )
    
    min_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default = 0.0,
        help_text=("Minimum thermal power size constraint for optimization [ton]")
    )

    max_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Maximum thermal power size constraint for optimization [ton]")
    )

    min_allowable_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Minimum nonzero thermal power size constraint for optimization [ton]")
    )

    min_allowable_peak_capacity_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Minimum nonzero thermal power as a function of coincident peak load / CF - constraint for optimization [ton]")
    )

    sizing_factor = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Size of system relative to max dispatch output [fraction]")
    )
    
    installed_cost_per_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Thermal power-based cost of ASHP water heater [$/ton] (3.5 ton to 1 kWt)")
    )

    om_cost_per_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Thermal power-based cost of ASHP water heater [$/ton] (3.5 ton to 1 kWt)")
    )

    macrs_option_years = models.IntegerField(
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )

    macrs_bonus_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )

    heating_cop_reference = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(20.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=(("Reference points for ASHP water heating system heating coefficient of performance (COP) "
                    "(ratio of usable heating thermal energy produced per unit electric energy consumed)"))
    )

    heating_cf_reference = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(20.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=(("Reference points for ASHP water heating system heating capacity factor"
                    "(ratio of heating thermal power to rated capacity)"))
    )

    heating_reference_temps_degF = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(-275.0),
                MaxValueValidator(200.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=(("Reference temperatures for ASHP water heating system's heating COP and CF [Fahrenheit]"))
    )

    avoided_capex_by_ashp_present_value = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default = 0.0,
        help_text=("Net present value of avoided capital expenditures due to ASHP system being present [$]")
    )

    back_up_temp_threshold_degF = models.FloatField(
        validators=[
            MinValueValidator(-275.0),
            MaxValueValidator(200.0)
        ],
        null=True,
        blank=True,
        help_text=("Temperature threshold below which resistive back-up heater turns on [Fahrenheit]")
    )

    force_into_system = models.BooleanField(
        null=True, 
        blank=True,
        help_text="Boolean indicator if ASHP water heater serves compatible thermal loads exclusively in optimized scenario"   
    )

    force_dispatch = models.BooleanField(
        null=True, 
        default=True,
        help_text="Boolean indicator that ASHP water heater outputs either maximum capacity or site load if true"   
    )

    def clean(self):
        error_messages = {}
        if self.dict.get("min_allowable_ton") in [None, "", []] and self.dict.get("min_allowable_peak_capacity_fraction") in [None, "", []]:
            self.min_allowable_peak_capacity_fraction = 0.25

        if self.dict.get("min_allowable_ton") not in [None, "", []] and self.dict.get("min_allowable_peak_capacity_fraction") not in [None, "", []]:
            error_messages["bad inputs"] = "At most one of min_allowable_ton and min_allowable_peak_capacity_fraction may be input to model {}".format(self.key)

        if len(self.dict.get("heating_cop_reference")) != len(self.dict.get("heating_cf_reference")) or len(self.dict.get("heating_cop_reference")) != len(self.dict.get("heating_reference_temps_degF")):
            error_messages["mismatched length"] = "Model {} inputs heating_cop_reference, heating_cf_reference, and heating_reference_temps_degF must all have the same length.".format(self.key)

        if error_messages:
            raise ValidationError(error_messages)


class ASHPWaterHeaterOutputs(BaseModel, models.Model):
    key = "ASHPWaterHeaterOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ASHPWaterHeaterOutputs",
        primary_key=True
    )

    size_ton = models.FloatField(null=True, blank=True)
    annual_electric_consumption_kwh = models.FloatField(null=True, blank=True)

    electric_consumption_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        default=list
    )

    annual_thermal_production_mmbtu = models.FloatField(null=True, blank=True)

    thermal_to_storage_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_production_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_dhw_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    heating_cop = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    heating_cf = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )


class REoptjlMessageOutputs(BaseModel, models.Model):
    
    key = "Messages"
    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="REoptjlMessageOutputs",
        primary_key=True
    )

    errors = ArrayField(
        models.TextField(null=True, blank=True),
        default = list,
    )

    warnings = ArrayField(
        models.TextField(null=True, blank=True),
        default = list,
    )

    has_stacktrace = models.BooleanField(
        blank=True,
        default=False,
        help_text=("REopt.jl can return a handled error with corrective instructions or an unhandled error with a stacktrace of what went wrong for further insepction."
                    "This field is True if the error message has a stacktrace, otherwise False.")
    )

    def clean(self):
        pass

class BoilerInputs(BaseModel, models.Model):
    key = "Boiler"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="BoilerInputs",
        primary_key=True
    )

    FUEL_TYPE_LIST = models.TextChoices('FUEL_TYPE_LIST', (
        "natural_gas",
        "landfill_bio_gas",
        "propane",
        "diesel_oil",
        "uranium"
    ))

    min_mmbtu_per_hour = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        default=0.0,
        help_text="Minimum thermal power size"
    )

    max_mmbtu_per_hour = models.FloatField(
        null=True,
        blank=True,        
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        default=1.0E7,
        help_text="Maximum thermal power size"
    )

    efficiency = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        null=True,
        blank=True,
        default=0.8,
        help_text="New boiler system efficiency - conversion of fuel to usable heating thermal energy."
    )

    fuel_cost_per_mmbtu = ArrayField(
        models.FloatField(
            blank=True,
            validators=[
                MinValueValidator(0)
            ]
        ),
        default=list,
        null=True,
        help_text="Fuel cost in [$/MMBtu]"
    )

    macrs_option_years = models.IntegerField(
        default=MACRS_YEARS_CHOICES.ZERO,
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )

    macrs_bonus_fraction = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )

    installed_cost_per_mmbtu_per_hour = models.FloatField(
        default=293000.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        blank=True,
        null=True,
        help_text="Thermal power-based cost"
    )

    om_cost_per_mmbtu_per_hour = models.FloatField(
        default=2930.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        blank=True,
        null=True,
        help_text="Thermal power-based fixed O&M cost"
    )

    om_cost_per_mmbtu = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        blank=True,
        null=True,
        help_text="Thermal energy-based variable O&M cost"
    )

    fuel_type = models.TextField(
        default=FUEL_TYPE_LIST.natural_gas,
        choices=FUEL_TYPE_LIST.choices,
        blank=True,
        null=True,
        help_text="Existing boiler fuel type, one of natural_gas, landfill_bio_gas, propane, diesel_oil, uranium"
    )

    can_supply_steam_turbine = models.BooleanField(
        default=True,
        blank=True,
        null=True,
        help_text="If the boiler can supply steam to the steam turbine for electric production"
    )

    can_serve_dhw = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if boiler can serve domestic hot water load"   
    )

    can_serve_space_heating = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if boiler can serve space heating load"   
    )

    can_serve_process_heat = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if boiler can serve process heat load"   
    )
    

    # For custom validations within model.
    def clean(self):
        error_messages = {}
        if not self.dict.get("fuel_cost_per_mmbtu"):
            error_messages["required inputs"] = "Must provide fuel_cost_per_mmbtu to model {}".format(self.key)

        if error_messages:
            raise ValidationError(error_messages)
        
        self.fuel_cost_per_mmbtu = scalar_or_monthly_to_8760(self.fuel_cost_per_mmbtu)

class BoilerOutputs(BaseModel, models.Model):

    key = "Boiler"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="BoilerOutputs",
        primary_key=True
    )

    fuel_consumption_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_to_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    year_one_fuel_cost_before_tax = models.FloatField(
        null=True, blank=True
    )

    year_one_fuel_cost_after_tax = models.FloatField(
        null=True, blank=True
    )    

    thermal_to_steamturbine_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_production_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_to_storage_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )
    
    thermal_to_absorption_chiller_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    size_mmbtu_per_hour = models.FloatField(null=True, blank=True)

    annual_fuel_consumption_mmbtu = models.FloatField(null=True, blank=True)

    lifecycle_per_unit_prod_om_costs = models.FloatField(
        null=True, blank=True
    )

    lifecycle_fuel_cost_after_tax = models.FloatField(
        null=True, blank=True
    )

    annual_thermal_production_mmbtu = models.FloatField(null=True, blank=True)

    thermal_to_dhw_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_space_heating_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_process_heat_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )


class SteamTurbineInputs(BaseModel, models.Model):

    key = "SteamTurbine"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="SteamTurbineInputs",
        primary_key=True
    )

    class SIZE_CLASS_LIST(models.IntegerChoices):
        ZERO = 0,
        ONE = 1
        TWO = 2
        THREE = 3

    min_kw = models.FloatField(
        null=True,        
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Minimum steam turbine size constraint for optimization"
    )
    max_kw = models.FloatField(
        null=True,        
        default=MAX_BIG_NUMBER,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum steam turbine size constraint for optimization"
    )

    ## default values for these fields are returned from REoptInputs() call in http.jl
    size_class = models.IntegerField(
        null=True,
        choices=SIZE_CLASS_LIST.choices,
        blank=True,
        help_text="Steam turbine size class for using appropriate default inputs"
    )

    gearbox_generator_efficiency = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Combined gearbox (if applicable) and electric motor/generator efficiency"
    )

    isentropic_efficiency = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Combined gearbox (if applicable) and electric motor/generator efficiency"
    )

    inlet_steam_pressure_psig = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0e3)
        ],
        blank=True,
        help_text="Inlet steam pressure to the steam turbine"
    )

    inlet_steam_temperature_degF = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1300.0)
        ],
        blank=True,
        help_text="Inlet steam temperature to the steam turbine"
    )

    installed_cost_per_kw = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0e5)
        ],
        blank=True,
        help_text="Installed steam turbine cost in $/kW"
    )

    om_cost_per_kwh = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0e2)
        ],
        blank=True,
        help_text="Steam turbine per unit production (variable) operations and maintenance costs in $/kWh"
    )

    outlet_steam_pressure_psig = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(-14.7),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        help_text="Outlet steam pressure from the steam turbine (to the condenser or heat recovery unit)"
    )

    net_to_gross_electric_ratio = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Efficiency factor to account for auxiliary loads such as pumps, controls, lights, etc"
    )

    # Other input fields
    electric_produced_to_thermal_consumed_ratio = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Simplified input as alternative to detailed calculations from inlet and outlet steam conditions"
    )
    
    thermal_produced_to_thermal_consumed_ratio = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Simplified input as alternative to detailed calculations from condensing outlet steam"
    )

    is_condensing = models.BooleanField(
        null=True,        
        blank=True,
        default = False,
        help_text="Steam turbine type, if it is a condensing turbine which produces no useful thermal (max electric output)"
    )

    inlet_steam_superheat_degF = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(700.0)
        ],
        default=0.0,
        help_text="Alternative input to inlet steam temperature, this is the superheat amount (delta from T_saturation) to the steam turbine"
    )

    outlet_steam_min_vapor_fraction = models.FloatField(
        null=True,        
        default=0.8,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Minimum practical vapor fraction of steam at the exit of the steam turbine"
    )

    isentropic_efficiency = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Steam turbine isentropic efficiency - uses inlet T/P and outlet T/P/X to get power out"
    )

    om_cost_per_kw = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0e3)
        ],
        default=0.0,
        null=True,
        blank=True,
        help_text="Annual steam turbine fixed operations and maintenance costs in $/kW"
    )

    can_net_meter = models.BooleanField(
        null=True,
        blank=True,
        default = False,
        help_text=("True/False for if technology has option to participate in net metering agreement with utility. "
                   "Note that a technology can only participate in either net metering or wholesale rates (not both)."
                   "Note that if off-grid is true, net metering is always set to False.")
    )

    can_wholesale = models.BooleanField(
        null=True,
        blank=True,
        default = False,
        help_text=("True/False for if technology has option to export energy that is compensated at the wholesale_rate. "
                   "Note that a technology can only participate in either net metering or wholesale rates (not both)."
                   "Note that if off-grid is true, can_wholesale is always set to False.")
    )
    can_export_beyond_nem_limit = models.BooleanField(
        null=True,
        blank=True,
        default = False,
        help_text=("True/False for if technology can export energy beyond the annual site load (and be compensated for "
                   "that energy at the export_rate_beyond_net_metering_limit)."
                   "Note that if off-grid is true, can_export_beyond_nem_limit is always set to False.")
    )

    can_curtail = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="True/False for if technology has the ability to curtail energy production."
    )

    can_serve_dhw = models.BooleanField(
        default=True,
        null=True,        
        blank=True,
        help_text="Boolean indicator if steam turbine can serve space heating load"
    )
    can_serve_space_heating = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if steam turbine can serve space heating load"   
    )
    can_serve_process_heat = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if steam turbine can serve process heat load"   
    )

    macrs_option_years = models.IntegerField(
        choices=MACRS_YEARS_CHOICES.choices,
        null=True,
        blank=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )

    macrs_bonus_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        null=True,
        blank=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )

    def clean(self):
        pass

class SteamTurbineOutputs(BaseModel, models.Model):

    key = "SteamTurbine"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="SteamTurbineOutputs",
        primary_key=True
    )


    size_kw = models.FloatField(
        null=True, blank=True
    )

    annual_thermal_consumption_mmbtu = models.FloatField(
        null=True, blank=True
    )

    annual_electric_production_kwh = models.FloatField(
        null=True, blank=True
    )

    annual_thermal_production_mmbtu = models.FloatField(
        null=True, blank=True
    )

    thermal_consumption_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    electric_production_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    electric_to_grid_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    electric_to_storage_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    electric_to_load_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_to_storage_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    thermal_to_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )
    
    thermal_to_absorption_chiller_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_dhw_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_space_heating_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_process_heat_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    thermal_to_high_temp_thermal_storage_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )    

class HotThermalStorageInputs(BaseModel, models.Model):
    key = "HotThermalStorage"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="HotThermalStorageInputs",
        primary_key=True
    )

    min_gal = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        null=True,
        blank=True,
        default=0.0,
        help_text="Minimum TES volume (energy) size constraint for optimization"
    )
    max_gal = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        default=0.0,
        help_text="Maximum TES volume (energy) size constraint for optimization. Set to zero to disable storage"
    )
    hot_water_temp_degF = models.FloatField(
        validators=[
            MinValueValidator(40.0),
            MaxValueValidator(210.0)
        ],
        blank=True,
        default=180.0,
        help_text="Hot-side supply water temperature from HotTES (top of tank) to the heating load"
    )
    cool_water_temp_degF = models.FloatField(
        validators=[
            MinValueValidator(33.0),
            MaxValueValidator(200.0)
        ],
        blank=True,
        default=160.0,
        help_text="Cold-side return water temperature from the heating load to the HotTES (bottom of tank)"
    )
    internal_efficiency_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        default=0.999999,
        help_text="Thermal losses due to mixing from thermal power entering or leaving tank"
    )
    soc_min_fraction = models.FloatField(
        default=0.1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Minimum allowable battery state of charge as fraction of energy capacity."
    )
    soc_init_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        default=0.5,
        blank=True,
        help_text="Battery state of charge at first hour of optimization as fraction of energy capacity."
    )
    installed_cost_per_gal = models.FloatField(
        default=1.5,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e4)
        ],
        blank=True,
        help_text="Installed hot TES cost in $/gal"
    )
    om_cost_per_gal = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        help_text="Annual hot TES operations and maintenance costs in $/gal"
    )
    thermal_decay_rate_fraction = models.FloatField(
        default=0.0004,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Thermal energy-based cost of TES (e.g. volume of the tank)"
    )
    macrs_option_years = models.IntegerField(
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )
    macrs_bonus_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )
    macrs_itc_reduction = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of the ITC value by which depreciable basis is reduced"
    )
    total_itc_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Total investment tax credit in percent applied toward capital costs"
    )
    total_rebate_per_kwh = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Rebate per unit installed energy capacity"
    )
    can_serve_dhw = models.BooleanField(
        default=True,
        null=True,        
        blank=True,
        help_text="Boolean indicator if hot thermal storage can serve space heating load"
    )
    can_serve_space_heating = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if hot thermal storage can serve space heating load"   
    )
    can_serve_process_heat = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if hot thermal storage can serve process heat load"   
    )
    

    def clean(self):
        # perform custom validation here.
        pass

class HotThermalStorageOutputs(BaseModel, models.Model):
    key = "HotThermalStorageOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="HotThermalStorageOutputs",
        primary_key=True
    )
    size_gal = models.FloatField(null=True, blank=True)
    size_kwh = models.FloatField(null=True, blank=True)
    soc_series_fraction = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )
    storage_to_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )
    storage_to_dhw_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    storage_to_space_heating_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    storage_to_process_heat_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )
    storage_to_steamturbine_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )
    storage_to_absorption_chiller_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )

    def clean(self):
        # perform custom validation here.
        pass

class HighTempThermalStorageInputs(BaseModel, models.Model):
    key = "HighTempThermalStorage"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="HighTempThermalStorageInputs",
        primary_key=True
    )
    fluid = models.TextField(
        blank=True,
        default="INCOMP::NaK",
        help_text="Type of fluid for your High Temp Thermal Storage system"
    )

    min_kwh = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        null=True,
        blank=True,
        default=0.0,
        help_text="Minimum TES volume (energy) size constraint for optimization"
    )
    max_kwh = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        default=0.0,
        help_text="Maximum TES volume (energy) size constraint for optimization. Set to zero to disable storage"
    )
    hot_temp_degF = models.FloatField(
        validators=[
            MinValueValidator(200.0),
            MaxValueValidator(2000.0)
        ],
        blank=True,
        default=1065.0,
        help_text="Hot-side supply water temperature from HotTES (top of tank) to the heating load"
    )
    cool_temp_degF = models.FloatField(
        validators=[
            MinValueValidator(200.0),
            MaxValueValidator(2000.0)
        ],
        blank=True,
        default=554.0,
        help_text="Cold-side return water temperature from the heating load to the HotTES (bottom of tank)"
    )
    internal_efficiency_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        default=0.999999,
        help_text="Thermal losses due to mixing from thermal power entering or leaving tank"
    )
    soc_min_fraction = models.FloatField(
        default=0.1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Minimum allowable battery state of charge as fraction of energy capacity."
    )
    soc_init_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        default=0.5,
        blank=True,
        help_text="Battery state of charge at first hour of optimization as fraction of energy capacity."
    )
    installed_cost_per_kwh = models.FloatField(
        default=86.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e4)
        ],
        blank=True,
        help_text="Installed hot TES cost in $/kwh"
    )
    om_cost_per_kwh = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        help_text="Annual hot TES operations and maintenance costs in $/kwh"
    )
    thermal_decay_rate_fraction = models.FloatField(
        default=0.0004,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Thermal energy-based cost of TES (e.g. volume of the tank)"
    )
    macrs_option_years = models.IntegerField(
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )
    macrs_bonus_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )
    macrs_itc_reduction = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of the ITC value by which depreciable basis is reduced"
    )
    total_itc_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Total investment tax credit in percent applied toward capital costs"
    )
    total_rebate_per_kwh = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Rebate per unit installed energy capacity"
    )
    can_serve_dhw = models.BooleanField(
        default=False,
        null=True,        
        blank=True,
        help_text="Boolean indicator if hot thermal storage can serve space heating load"
    )
    can_serve_space_heating = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if hot thermal storage can serve space heating load"   
    )
    can_serve_process_heat = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if hot thermal storage can serve process heat load"   
    )
    supply_turbine_only = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if hot thermal storage can serve only steam turbine"   
    )
    one_direction_flow = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if hot thermal storage can only"   
    )
    num_charge_hours = models.FloatField(
        default=4.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        help_text="Number of charge hours"
    )
    num_discharge_hours = models.FloatField(
        default=10.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        help_text="Number of charge hours"
    )

class HighTempThermalStorageOutputs(BaseModel, models.Model):
    key = "HighTempThermalStorageOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="HighTempThermalStorageOutputs",
        primary_key=True
    )
    size_kwh = models.FloatField(null=True, blank=True)
    soc_series_fraction = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )
    storage_to_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )
    storage_to_steamturbine_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )
    storage_to_absorption_chiller_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )


class ColdThermalStorageInputs(BaseModel, models.Model):
    key = "ColdThermalStorage"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ColdThermalStorageInputs",
        primary_key=True
    )

    min_gal = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        null=True,
        blank=True,
        default=0.0,
        help_text="Minimum TES volume (energy) size constraint for optimization"
    )
    max_gal = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        default=0.0,
        help_text="Maximum TES volume (energy) size constraint for optimization. Set to zero to disable storage"
    )
    cool_water_temp_degF = models.FloatField(
        validators=[
            MinValueValidator(33.0),
            MaxValueValidator(200.0)
        ],
        blank=True,
        default=44.0,
        help_text="Cold-side supply water temperature from ColdTES (top of tank) to the heating load"
    )
    hot_water_temp_degF = models.FloatField(
        validators=[
            MinValueValidator(40.0),
            MaxValueValidator(210.0)
        ],
        blank=True,
        default=56.0,
        help_text="Cold-side return water temperature from the heating load to the ColdTES (bottom of tank)"
    )
    internal_efficiency_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        default=0.999999,
        help_text="Thermal losses due to mixing from thermal power entering or leaving tank"
    )
    soc_min_fraction = models.FloatField(
        default=0.1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Minimum allowable battery state of charge as fraction of energy capacity."
    )
    soc_init_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        default=0.5,
        blank=True,
        help_text="Battery state of charge at first hour of optimization as fraction of energy capacity."
    )
    installed_cost_per_gal = models.FloatField(
        default=1.5,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e4)
        ],
        blank=True,
        help_text="Installed cold TES cost in $/gal"
    )
    om_cost_per_gal = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        help_text="Annual cold TES operations and maintenance costs in $/gal"
    )
    thermal_decay_rate_fraction = models.FloatField(
        default=0.0004,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        help_text="Thermal energy-based cost of TES (e.g. volume of the tank)"
    )
    macrs_option_years = models.IntegerField(
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )
    macrs_bonus_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )
    macrs_itc_reduction = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of the ITC value by which depreciable basis is reduced"
    )
    total_itc_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Total investment tax credit in percent applied toward capital costs"
    )
    total_rebate_per_kwh = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Rebate per unit installed energy capacity"
    )

    def clean(self):
        # perform custom validation here.
        pass

class ColdThermalStorageOutputs(BaseModel, models.Model):
    key = "ColdThermalStorageOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ColdThermalStorageOutputs",
        primary_key=True
    )
    size_gal = models.FloatField(null=True, blank=True)
    soc_series_fraction = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )
    storage_to_load_series_ton = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list,
    )

    def clean(self):
        # perform custom validation here.
        pass

class SpaceHeatingLoadInputs(BaseModel, models.Model):
    
    key = "SpaceHeatingLoad"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="SpaceHeatingLoadInputs",
        primary_key=True
    )

    possible_sets = [
        ["fuel_loads_mmbtu_per_hour"],
        ["doe_reference_name", "monthly_mmbtu"],
        ["annual_mmbtu", "doe_reference_name"],
        ["doe_reference_name"],
        ["blended_doe_reference_names", "blended_doe_reference_percents"],
        []
    ]

    DOE_REFERENCE_NAME = models.TextChoices('DOE_REFERENCE_NAME', (
        'FastFoodRest '
        'FullServiceRest '
        'Hospital '
        'LargeHotel '
        'LargeOffice '
        'MediumOffice '
        'MidriseApartment '
        'Outpatient '
        'PrimarySchool '
        'RetailStore '
        'SecondarySchool '
        'SmallHotel '
        'SmallOffice '
        'StripMall '
        'Supermarket '
        'Warehouse '
        'FlatLoad '
        'FlatLoad_24_5 '
        'FlatLoad_16_7 '
        'FlatLoad_16_5 '
        'FlatLoad_8_7 '
        'FlatLoad_8_5'
    ))

    annual_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Annual site space heating consumption, used "
                   "to scale simulated default building load profile for the site's climate zone [MMBtu]")
    )

    doe_reference_name = models.TextField(
        null=True,
        blank=True,
        choices=DOE_REFERENCE_NAME.choices,
        help_text=("Simulated load profile from DOE Commercial Reference Buildings "
                   "https://energy.gov/eere/buildings/commercial-reference-buildings")
    )

    monthly_mmbtu = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Monthly site space heating energy consumption in [MMbtu], used "
                   "to scale simulated default building load profile for the site's climate zone")
    )

    fuel_loads_mmbtu_per_hour = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        help_text=("Vector of space heating fuel loads [mmbtu/hr] over one year. Must be hourly (8,760 samples), 30 minute (17,"
                   "520 samples), or 15 minute (35,040 samples). All non-net load values must be greater than or "
                   "equal to zero. "
                   )
    )

    normalize_and_scale_load_profile_input = models.BooleanField(
        blank=True,
        default=False,
        help_text=("Takes the input fuel_loads_mmbtu_per_hour and normalizes and scales it to annual or monthly energy inputs.")
    )
    
    year = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(9999)
        ],
        null=True, blank=True,
        help_text=("Year of Custom Load Profile. If a custom load profile is uploaded via the fuel_loads_mmbtu_per_hour parameter, it "
                   "is important that this year correlates with the electric load profile so that weekdays/weekends are "
                   "determined correctly for the utility rate tariff. If a DOE Reference Building profile (aka "
                   "'simulated' profile) is used, the year is set to 2017 since the DOE profiles start on a Sunday.")
    )    

    blended_doe_reference_names = ArrayField(
        models.TextField(
            choices=DOE_REFERENCE_NAME.choices,
            blank=True,
            null=True
        ),
        default=list,
        blank=True,
        help_text=("Used in concert with blended_doe_reference_percents to create a blended load profile from multiple "
                   "DoE Commercial Reference Buildings.")
    )

    blended_doe_reference_percents = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=("Used in concert with blended_doe_reference_names to create a blended load profile from multiple "
                   "DoE Commercial Reference Buildings. Must sum to 1.0.")
    )

    addressable_load_fraction = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1.0)
            ],
            blank=True
        ),
        default=list,
        blank=True,
        help_text=( "Fraction of input fuel load which is addressable by heating technologies (default is 1.0)." 
                    "Can be a scalar or vector with length aligned with use of monthly_mmbtu (12) or fuel_loads_mmbtu_per_hour.")
    )

    '''
    Latitude and longitude are passed on to SpaceHeating struct using the Site struct.
    City is not used as an input here because it is found using find_ashrae_zone_city() when needed.
    '''

    def clean(self):
        error_messages = {}

        # possible sets for defining load profile
        if not at_least_one_set(self.dict, self.possible_sets):
            error_messages["required inputs"] = \
                "Must provide at least one set of valid inputs from {}.".format(self.possible_sets)

        if len(self.blended_doe_reference_names) > 0 and self.doe_reference_name == "":
            if len(self.blended_doe_reference_names) != len(self.blended_doe_reference_percents):
                error_messages["blended_doe_reference_names"] = \
                    "The number of blended_doe_reference_names must equal the number of blended_doe_reference_percents."
            if not math.isclose(sum(self.blended_doe_reference_percents),  1.0):
                error_messages["blended_doe_reference_percents"] = "Sum must = 1.0."
        
        if self.addressable_load_fraction == None:
            self.addressable_load_fraction = list([1.0]) # should not convert to timeseries, in case it is to be used with monthly_mmbtu or annual_mmbtu

        if error_messages:
            raise ValidationError(error_messages)
        
        pass

class DomesticHotWaterLoadInputs(BaseModel, models.Model):
    # DHW
    key = "DomesticHotWaterLoad"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="DomesticHotWaterLoadInputs",
        primary_key=True
    )

    possible_sets = [
        ["fuel_loads_mmbtu_per_hour"],
        ["doe_reference_name", "monthly_mmbtu"],
        ["annual_mmbtu", "doe_reference_name"],
        ["doe_reference_name"],
        [],
        ["blended_doe_reference_names", "blended_doe_reference_percents"]
    ]

    DOE_REFERENCE_NAME = models.TextChoices('DOE_REFERENCE_NAME', (
        'FastFoodRest '
        'FullServiceRest '
        'Hospital '
        'LargeHotel '
        'LargeOffice '
        'MediumOffice '
        'MidriseApartment '
        'Outpatient '
        'PrimarySchool '
        'RetailStore '
        'SecondarySchool '
        'SmallHotel '
        'SmallOffice '
        'StripMall '
        'Supermarket '
        'Warehouse '
        'FlatLoad '
        'FlatLoad_24_5 '
        'FlatLoad_16_7 '
        'FlatLoad_16_5 '
        'FlatLoad_8_7 '
        'FlatLoad_8_5'
    ))

    annual_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Annual site DHW consumption, used "
                   "to scale simulated default building load profile for the site's climate zone [MMBtu]")
    )

    doe_reference_name = models.TextField(
        null=True,
        blank=True,
        choices=DOE_REFERENCE_NAME.choices,
        help_text=("Simulated load profile from DOE Commercial Reference Buildings "
                   "https://energy.gov/eere/buildings/commercial-reference-buildings")
    )

    monthly_mmbtu = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Monthly site DHW energy consumption in [MMbtu], used "
                   "to scale simulated default building load profile for the site's climate zone")
    )

    fuel_loads_mmbtu_per_hour = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        help_text=("Typical load over all hours in one year. Must be hourly (8,760 samples), 30 minute (17,"
                   "520 samples), or 15 minute (35,040 samples). All non-net load values must be greater than or "
                   "equal to zero. "
                   )
    )

    normalize_and_scale_load_profile_input = models.BooleanField(
        blank=True,
        default=False,
        help_text=("Takes the input fuel_loads_mmbtu_per_hour and normalizes and scales it to annual or monthly energy inputs.")
    )

    year = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(9999)
        ],
        null=True, blank=True,
        help_text=("Year of Custom Load Profile. If a custom load profile is uploaded via the fuel_loads_mmbtu_per_hour parameter, it "
                   "is important that this year correlates with the electric load profile so that weekdays/weekends are "
                   "determined correctly for the utility rate tariff. If a DOE Reference Building profile (aka "
                   "'simulated' profile) is used, the year is set to 2017 since the DOE profiles start on a Sunday.")
    )    

    blended_doe_reference_names = ArrayField(
        models.TextField(
            choices=DOE_REFERENCE_NAME.choices,
            blank=True
        ),
        default=list,
        blank=True,
        help_text=("Used in concert with blended_doe_reference_percents to create a blended load profile from multiple "
                   "DoE Commercial Reference Buildings.")
    )

    blended_doe_reference_percents = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=("Used in concert with blended_doe_reference_names to create a blended load profile from multiple "
                   "DoE Commercial Reference Buildings to simulate buildings/campuses. Must sum to 1.0.")
    )

    addressable_load_fraction = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1.0)
            ],
            blank=True
        ),
        default=list,
        blank=True,
        help_text=( "Fraction of input fuel load which is addressable by heating technologies (default is 1.0)." 
                    "Can be a scalar or vector with length aligned with use of monthly_mmbtu (12) or fuel_loads_mmbtu_per_hour.")
    )    

    '''
    Latitude and longitude are passed on to DomesticHotWater struct using the Site struct.
    City is not used as an input here because it is found using find_ashrae_zone_city() when needed.
    If a blank key is provided, then default DOE load profile from electricload is used [cross-clean]
    '''

    def clean(self):
        error_messages = {}

        # possible sets for defining load profile
        if not at_least_one_set(self.dict, self.possible_sets):
            error_messages["required inputs"] = \
                "Must provide at least one set of valid inputs from {}.".format(self.possible_sets)

        if len(self.blended_doe_reference_names) > 0 and self.doe_reference_name == "":
            if len(self.blended_doe_reference_names) != len(self.blended_doe_reference_percents):
                error_messages["blended_doe_reference_names"] = \
                    "The number of blended_doe_reference_names must equal the number of blended_doe_reference_percents."
            if not math.isclose(sum(self.blended_doe_reference_percents),  1.0):
                error_messages["blended_doe_reference_percents"] = "Sum must = 1.0."
        
        if self.addressable_load_fraction == None:
            self.addressable_load_fraction = list([1.0]) # should not convert to timeseries, in case it is to be used with monthly_mmbtu or annual_mmbtu

class ProcessHeatLoadInputs(BaseModel, models.Model):
    # Process Heat
    key = "ProcessHeatLoad"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="ProcessHeatLoadInputs",
        primary_key=True
    )

    possible_sets = [
        ["fuel_loads_mmbtu_per_hour"],
        ["industrial_reference_name", "monthly_mmbtu"],
        ["annual_mmbtu", "industrial_reference_name"],
        ["industrial_reference_name"],
        ["blended_industrial_reference_names", "blended_industrial_reference_percents"],
        []
    ]

    INDUSTRIAL_REFERENCE_NAME = models.TextChoices('INDUSTRIAL_REFERENCE_NAME', (
        'Chemical '
        'Warehouse '
        'FlatLoad '
        'FlatLoad_24_5 '
        'FlatLoad_16_7 '
        'FlatLoad_16_5 '
        'FlatLoad_8_7 '
        'FlatLoad_8_5'        
    ))

    annual_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Annual site process heat fuel consumption, used "
                   "to scale simulated default industry load profile [MMBtu]")
    )

    industrial_reference_name = models.TextField(
        null=True,
        blank=True,
        choices=INDUSTRIAL_REFERENCE_NAME.choices,
        help_text=("Industrial process heat load reference facility/sector type")
    )

    monthly_mmbtu = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Monthly site process heat fuel consumption in [MMbtu], used "
                   "to scale simulated default building load profile for the site's climate zone")
    )

    fuel_loads_mmbtu_per_hour = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        help_text=("Vector of process heat fuel loads [mmbtu/hr] over one year. Must be hourly (8,760 samples), 30 minute (17,"
                   "520 samples), or 15 minute (35,040 samples). All non-net load values must be greater than or "
                   "equal to zero. "
                   )
    )

    year = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(9999)
        ],
        null=True, blank=True,
        help_text=("Year of Custom Load Profile. If a custom load profile is uploaded via the fuel_loads_mmbtu_per_hour parameter, it "
                   "is important that this year correlates with the electric load profile so that weekdays/weekends are "
                   "determined correctly for the utility rate tariff. If a Industrial Reference Building profile (aka "
                   "'simulated' profile) is used, the year is set to 2017 to be consistent with the DOE reference building year which starts on a Sunday.")
    )    

    normalize_and_scale_load_profile_input = models.BooleanField(
        blank=True,
        default=False,
        help_text=("Takes the input fuel_loads_mmbtu_per_hour and normalizes and scales it to annual or monthly energy inputs.")
    )   

    blended_industrial_reference_names = ArrayField(
        models.TextField(
            choices=INDUSTRIAL_REFERENCE_NAME.choices,
            blank=True,
            null=True
        ),
        default=list,
        blank=True,
        help_text=("Used in concert with blended_industrial_reference_percents to create a blended load profile from multiple "
                   "Industrial reference facility/sector types.")
    )

    blended_industrial_reference_percents = ArrayField(
        models.FloatField(
            null=True, blank=True,
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1.0)
            ],
        ),
        default=list,
        blank=True,
        help_text=("Used in concert with blended_industrial_reference_names to create a blended load profile from multiple "
                   "Industrial reference facility/sector types. Must sum to 1.0.")
    )

    addressable_load_fraction = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1.0)
            ],
            blank=True
        ),
        default=list,
        blank=True,
        help_text=( "Fraction of input fuel load which is addressable by heating technologies (default is 1.0)." 
                    "Can be a scalar or vector with length aligned with use of monthly_mmbtu (12) or fuel_loads_mmbtu_per_hour.")
    )

    def clean(self):
        error_messages = {}

        # possible sets for defining load profile
        if not at_least_one_set(self.dict, self.possible_sets):
            error_messages["required inputs"] = \
                "Must provide at least one set of valid inputs from {}.".format(self.possible_sets)

        if len(self.blended_industrial_reference_names) > 0 and self.industrial_reference_name == "":
            if len(self.blended_industrial_reference_names) != len(self.blended_industrial_reference_percents):
                error_messages["blended_industrial_reference_names"] = \
                    "The number of blended_industrial_reference_names must equal the number of blended_industrial_reference_percents."
            if not math.isclose(sum(self.blended_industrial_reference_percents),  1.0):
                error_messages["blended_industrial_reference_percents"] = "Sum must = 1.0."
        
        if self.addressable_load_fraction == None:
            self.addressable_load_fraction = list([1.0]) # should not convert to timeseries, in case it is to be used with monthly_mmbtu or annual_mmbtu

        # possible sets for defining load profile
        if not at_least_one_set(self.dict, self.possible_sets):
            error_messages["required inputs"] = \
                "Must provide at least one set of valid inputs from {}.".format(self.possible_sets)

class HeatingLoadOutputs(BaseModel, models.Model):

    key = "HeatingLoadOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="HeatingLoadOutputs",
        primary_key=True
    )

    dhw_thermal_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Hourly domestic hot water load [MMBTU/hr]")
    )

    space_heating_thermal_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Hourly space heating load [MMBTU/hr]")
    )

    process_heat_thermal_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Hourly process heat load [MMBTU/hr]")
    )

    total_heating_thermal_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Hourly total heating load [MMBTU/hr]")
    )

    dhw_boiler_fuel_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Hourly domestic hot water boiler fuel load [MMBTU/hr]")
    )

    space_heating_boiler_fuel_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Hourly space heating boiler fuel load [MMBTU/hr]")
    )

    process_heat_boiler_fuel_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Hourly process heat boiler fuel load [MMBTU/hr]")
    )

    total_heating_boiler_fuel_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Hourly total boiler fuel load [MMBTU/hr]")
    )

    annual_calculated_dhw_thermal_load_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual site DHW load [MMBTU]")
    )

    annual_calculated_space_heating_thermal_load_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual site space heating load [MMBTU]")
    )

    annual_calculated_process_heat_thermal_load_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual site process heat load [MMBTU]")
    )

    annual_calculated_total_heating_thermal_load_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual site total heating load [MMBTU]")
    )

    annual_calculated_dhw_boiler_fuel_load_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual site DHW boiler fuel load [MMBTU]")
    )

    annual_calculated_space_heating_boiler_fuel_load_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual site space heating boiler fuel load [MMBTU]")
    )

    annual_calculated_process_heat_boiler_fuel_load_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual site process heat boiler fuel load [MMBTU]")
    )

    annual_calculated_total_heating_boiler_fuel_load_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual site total heating boiler fuel load [MMBTU]")
    )

    annual_total_unaddressable_heating_load_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual site total unaddressable heating fuel [MMBTU]")
    )

    annual_emissions_from_unaddressable_heating_load_tonnes_CO2 = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual site total unaddressable heating fuel climate CO2 emissions [tonnes]")
    )      

    def clean(self):
        pass

class CoolingLoadOutputs(BaseModel, models.Model):
    
    key = "CoolingLoadOutputs"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="CoolingLoadOutputs",
        primary_key=True
    )

    load_series_ton = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Hourly total cooling load [ton]")
    )

    electric_chiller_base_load_series_kw = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(MAX_BIG_NUMBER)
            ],
            blank=True
        ),
        default=list, blank=True,
        help_text=("Hourly total base load drawn from chiller [kW-electric]")
    )

    annual_calculated_tonhour = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual site total cooling load [tonhr]")
    )

    annual_electric_chiller_base_load_kwh = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=0,
        help_text=("Annual total base load drawn from chiller [kWh-electric]")
    )

    def clean(self):
        pass

class AbsorptionChillerInputs(BaseModel, models.Model):
    key = "AbsorptionChiller"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="AbsorptionChillerInputs",
        primary_key=True
    )

    PRODUCTION_TYPE = models.TextChoices('PRODUCTION_TYPE', (
        'steam',
        'hot_water'
    ))

    HEATING_LOAD_INPUT = models.TextChoices('HEATING_LOAD_INPUT', (
        'DomesticHotWater',
        'SpaceHeating',
        'ProcessHeat'
    ))

    thermal_consumption_hot_water_or_steam = models.TextField(
        blank=True,
        null=True,
        choices=PRODUCTION_TYPE.choices,
        help_text="Boiler thermal production type, hot water or steam"
    )

    installed_cost_per_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Thermal power-based cost of absorption chiller [$/ton] (3.5 ton to 1 kWt)")
    )
    
    min_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default = 0.0,
        help_text=("Minimum thermal power size constraint for optimization [ton]")
    )

    max_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default = MAX_BIG_NUMBER,
        help_text=("Maximum thermal power size constraint for optimization [ton]")
    )

    cop_thermal = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Absorption chiller system coefficient of performance - conversion of hot thermal power input "
                    "to usable cooling thermal energy output")
    )

    cop_electric = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        default=14.1,
        help_text=("Absorption chiller electric consumption CoP from cooling tower heat rejection - conversion of electric power input "
                    "to usable cooling thermal energy output")
    )

    om_cost_per_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Yearly fixed O&M cost [$/ton]")
    )

    macrs_option_years = models.IntegerField(
        default=MACRS_YEARS_CHOICES.ZERO,
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )

    macrs_bonus_fraction = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )

    heating_load_input = models.TextField(
        blank=True,
        null=True,
        choices=HEATING_LOAD_INPUT.choices,
        help_text="Absorption chiller heat input - determines what heating load is added to by absorption chiller use"
    )

    def clean(self):
        pass

    


class AbsorptionChillerOutputs(BaseModel, models.Model):
    key = "AbsorptionChiller"

    meta = models.OneToOneField(
        APIMeta,
        on_delete=models.CASCADE,
        related_name="AbsorptionChillerOutputs",
        primary_key=True
    )

    size_kw = models.FloatField(
        null=True, blank=True,
        help_text="Thermal power capacity of the absorption chiller [kW]"
    )
    
    size_ton = models.FloatField(
        null=True, blank=True,
        help_text="Thermal power capacity of the absorption chiller [ton]"
    )

    thermal_to_storage_series_ton = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        null=True,
        help_text=("Year one hourly time series of absorption chiller thermal to cold TES [Ton]")
    )

    thermal_to_load_series_ton = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        null=True,
        help_text=("Year one hourly time series of absorption chiller thermal to cooling load [Ton]")
    )

    thermal_consumption_series_mmbtu_per_hour = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        null=True,
        help_text=("Year one hourly time series of absorption chiller electric consumption [kW]")
    )

    annual_thermal_consumption_mmbtu = models.FloatField(
        null=True,
        blank=True,
        help_text=("Year one absorption chiller electric consumption [kWh]")
    )

    annual_thermal_production_tonhour = models.FloatField(
        null=True,
        blank=True,
        help_text=("Year one absorption chiller thermal production [Ton Hour")
    )
    electric_consumption_series_kw = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list,
        blank=True,
        null=True,
        help_text=("Year one hourly time series of absorption chiller electric consumption [kW]")
    )

    annual_electric_consumption_kwh = models.FloatField(
        null=True,
        blank=True,
        help_text=("Year one absorption chiller electric consumption [kWh]")
    )

    def clean(self):
        pass


class GHPInputs(BaseModel, models.Model):
    key = "GHP"

    meta = models.OneToOneField(
        to=APIMeta,
        on_delete=models.CASCADE,
        related_name="GHPInputs",
        primary_key=True
    )

    require_ghp_purchase = models.BooleanField(
        default=False,
        blank=True,
        null=True,
        help_text="Force one of the considered GHP design options."
    )

    installed_cost_heatpump_per_ton = models.FloatField(
        default=1075.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e5)
        ],
        blank=True,
        null=True,
        help_text="Installed heating heat pump cost in $/ton (based on peak coincident cooling+heating thermal load)"
    )

    installed_cost_wwhp_heating_pump_per_ton = models.FloatField(
        default=700.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e5)
        ],
        blank=True,
        null=True,
        help_text="Installed WWHP heating heat pump cost in $/ton (based on peak heating thermal load)"
    )

    installed_cost_wwhp_cooling_pump_per_ton = models.FloatField(
        default=700.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e5)
        ],
        blank=True,
        null=True,
        help_text="Installed WWHP cooling heat pump cost in $/ton (based on peak cooling thermal load)"
    )

    heatpump_capacity_sizing_factor_on_peak_load = models.FloatField(
        default=1.1,
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(5.0)
        ],
        blank=True,
        null=True,
        help_text="Factor on peak heating and cooling load served by GHP used for determining GHP installed capacity"
    )    

    installed_cost_ghx_per_ft = models.FloatField(
        default=14.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(100.0)
        ],
        blank=True,
        null=True,
        help_text="Installed cost of the ground heat exchanger (GHX) in $/ft of vertical piping"
    ) 

    installed_cost_building_hydronic_loop_per_sqft = models.FloatField(
        default=1.70,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(100.0)
        ],
        blank=True,
        null=True,
        help_text="Installed cost of the building hydronic loop per floor space of the site"
    ) 

    om_cost_per_sqft_year = models.FloatField(
        default=-0.51,
        validators=[
            MinValueValidator(-100.0),
            MaxValueValidator(100.0)
        ],
        blank=True,
        null=True,
        help_text="Annual GHP incremental operations and maintenance costs in $/ft^2-building/year"
    ) 

    # REQUIRED FOR GHP
    building_sqft = models.FloatField(
        null=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        help_text="Building square footage for GHP/HVAC cost calculations"
    ) 

    space_heating_efficiency_thermal_factor = models.FloatField(
        validators=[
            MinValueValidator(0.001),
            MaxValueValidator(1.0)
        ],
        blank=True,
        null=True,
        help_text="Heating efficiency factor (annual average) to account for reduced space heating thermal load from GHP retrofit (e.g. reduced reheat)"
    )    

    cooling_efficiency_thermal_factor = models.FloatField(
        validators=[
            MinValueValidator(0.001),
            MaxValueValidator(1.0)
        ],
        blank=True,
        null=True,
        help_text="Cooling efficiency factor (annual average) to account for reduced cooling thermal load from GHP retrofit (e.g. reduced reheat)"
    )

    ghx_useful_life_years = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(75)
        ],
        blank=True,
        default=50,
        help_text="Lifetime of geothermal heat exchanger being modeled in years. This is used to calculate residual value at end of REopt analysis period. If this value is less than Financial.analysis_years, its set to Financial.analysis_years."
    )

    # This field is calculated in REopt and should not be provided by a user.
    ghx_only_capital_cost = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        blank=True,
        null=True,
        help_text="Capital cost of geothermal heat exchanger which is calculated by REopt automatically. User does not need to provide this input."
    )

    # This field can only be set to "electric," user does not need to provide this information.
    aux_heater_type = models.TextField(
        blank=True,
        null=True,
        help_text="This field only accepts \"electric\" as the auxillary heater type. User does not need to provide this information."
    )

    # User does not need to provide this field.
    is_ghx_hybrid = models.BooleanField(
        blank=True,
        null=True,
        help_text="REopt derived indicator for hybrid Ghx"
    )

    aux_heater_installed_cost_per_mmbtu_per_hr = models.FloatField(
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(1.0e6)
        ],
        blank=True,
        default=26000.00,
        help_text="Installed cost of auxiliary heater for hybrid ghx in $/MMBtu/hr based on peak thermal production."
    )

    aux_cooler_installed_cost_per_ton = models.FloatField(
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(1.0e6)
        ],
        blank=True,
        default=400.00,
        help_text="Installed cost of auxiliary cooler (e.g. cooling tower) for hybrid ghx in $/ton based on peak thermal production"
    )

    aux_unit_capacity_sizing_factor_on_peak_load = models.FloatField(
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(5.0)
        ],
        blank=True,
        default=1.2,
        help_text="Factor on peak heating and cooling load served by the auxiliary heater/cooler used for determining heater/cooler installed capacity"
    )

    avoided_capex_by_ghp_present_value = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        blank=True,
        default=0.0,
        help_text="Expected cost of HVAC upgrades avoided due to GHP tech over Financial.analysis_years"
    )

    ghpghx_inputs = ArrayField(
        models.JSONField(
            null=True,
            editable=True
        ),
        default=list, blank=True, null=True,
        help_text=("GhpGhx.jl inputs/POST to ghpghx app")
    )

    # See clean() for assigning ghpghx_responses with ghpghx_response_uuids from /ghpghx database
    ghpghx_response_uuids = ArrayField(
        models.TextField(
            blank=True
        ),
        default=list, blank=True, null=True,
        help_text=("List of ghp_uuid's (like run_uuid for REopt) from ghpghx app, used to get GhpGhx.jl run data")    
    )

    ghpghx_responses = ArrayField(
        models.JSONField(
            null=True,
            editable=True
        ),
        default=list, blank=True, null=True,
        help_text=("ghpghx app response(s) to re-use a previous GhpGhx.jl run without relying on a database entry")
    )

    can_serve_dhw = models.BooleanField(
        default=False,
        null=True,        
        blank=True,
        help_text="If GHP can serve the domestic hot water (DHW) portion of the heating load"
    )
    
    can_serve_space_heating = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if GHP can serve space heating load"   
    )

    can_serve_process_heat = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if GHP can serve process heat load"   
    )

    macrs_option_years = models.IntegerField(
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        null=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )
    macrs_bonus_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )
    macrs_itc_reduction = models.FloatField(
        default=0.5,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of the ITC value by which depreciable basis is reduced"
    )
    federal_itc_fraction = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        null=True,
        help_text="Percentage of capital costs that are credited towards federal taxes"
    )
    state_ibi_fraction = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percentage of capital costs offset by state incentives"
    )
    state_ibi_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum dollar value of state percentage-based capital cost incentive"
    )
    utility_ibi_fraction = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percentage of capital costs offset by utility incentives"
    )
    utility_ibi_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum dollar value of utility percentage-based capital cost incentive"
    )
    federal_rebate_per_ton = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Federal rebates based on installed capacity of heat pumps"
    )
    state_rebate_per_ton = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="State rebate based on installed capacity of heat pumps"
    )
    state_rebate_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum state rebate"
    )
    utility_rebate_per_ton = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Utility rebate based on installed capacity of heat pumps"
    )
    utility_rebate_max = models.FloatField(
        default=MAX_INCENTIVE,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_INCENTIVE)
        ],
        blank=True,
        help_text="Maximum utility rebate"
    )
    max_ton = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Maximum thermal power size constraint for GHP [ton]")
    )

    max_number_of_boreholes = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(MAX_BIG_NUMBER)
        ],
        null=True,
        blank=True,
        help_text=("Maximum number of boreholes for GHX")
    )

    load_served_by_ghp = models.TextField(
        null=False,
        blank=True,
        default="nonpeak",
        help_text="How to split between load served by GHP and load served by backup system"
    )


    def clean(self):
        # perform custom validation here.
        error_messages = {}
        if not self.dict.get("building_sqft"):
            error_messages["required inputs"] = "Must provide building_sqft to model {}".format(self.key)

        if error_messages:
            raise ValidationError(error_messages)
                
        # Get ghpghx_responses from /ghpghx database
        if self.ghpghx_response_uuids not in [None, []]:
            self.ghpghx_responses = []
            for ghp_uuid in self.ghpghx_response_uuids:
                self.ghpghx_responses.append(ghpModelManager.make_response(ghp_uuid))
            # Remove this field from the POST because it's only relevant for the API and will throw an error in REopt.jl
            self.ghpghx_response_uuids = None

class GHPOutputs(BaseModel, models.Model):
    key = "GHP"

    meta = models.OneToOneField(
        to=APIMeta,
        on_delete=models.CASCADE,
        related_name="GHPOutputs",
        primary_key=True
    )

    ghp_option_chosen = models.IntegerField(null=True, blank=True)
    ghpghx_chosen_outputs = models.JSONField(null=True, editable=True)
    size_heat_pump_ton = models.FloatField(null=True, blank=True)  # This includes a factor on the peak coincident heating+cooling load
    size_wwhp_heating_pump_ton = models.FloatField(null=True, blank=True)  # This includes a factor on the peak heating load
    size_wwhp_cooling_pump_ton = models.FloatField(null=True, blank=True)  # This includes a factor on the peak cooling load
    space_heating_thermal_load_reduction_with_ghp_mmbtu_per_hour = ArrayField(
            models.FloatField(null=True, blank=True), default=list, null=True, blank=True)
    cooling_thermal_load_reduction_with_ghp_ton = ArrayField(
            models.FloatField(null=True, blank=True), default=list, null=True, blank=True)
    ghx_residual_value_present_value = models.FloatField(null=True, blank=True)
    thermal_to_space_heating_load_series_mmbtu_per_hour = ArrayField(models.FloatField(null=True, blank=True), default=list, null=True, blank=True)
    thermal_to_dhw_load_series_mmbtu_per_hour = ArrayField(models.FloatField(null=True, blank=True), default=list, null=True, blank=True)
    thermal_to_load_series_mmbtu_per_hour = ArrayField(models.FloatField(null=True, blank=True), default=list, null=True, blank=True)
    thermal_to_load_series_ton = ArrayField(models.FloatField(null=True, blank=True), default=list, null=True, blank=True)
    avoided_capex_by_ghp_present_value = models.FloatField(null=True, blank=True) 
    annual_thermal_production_mmbtu = models.FloatField(null=True, blank=True)
    annual_thermal_production_tonhour = models.FloatField(null=True, blank=True)
    hybrid_solution_type = models.TextField(null=True, blank=True)

class CSTInputs(BaseModel, models.Model):
    key = "CST"
    meta = models.OneToOneField(
        to=APIMeta,
        on_delete=models.CASCADE,
        related_name="CSTInputs",
        unique=False
    )

    tech_type = models.TextField(
        blank=True,
        default="ptc",
        help_text="Type of CST you want to implement into your system"
    )
    min_kw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Minimum CST size constraint for optimization."
    )
    max_kw = models.FloatField(
        default=1.0e9,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        help_text="Maximum CST size constraint for optimization (upper bound on additional capacity beyond existing_kw). Set to zero to disable PV"
    )
    inlet_temp_degF = models.FloatField(
        default=400,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(750)
        ],
        blank=True,
        help_text="This is the temperature at which your process needs the heat transfer fluid specified above to be at when entering your facility. In other words, this is your 'hot' temperature."
    )
    outlet_temp_degF = models.FloatField(
        default=70,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(750)
        ],
        blank=True,
        help_text="This is the temperature at which your the heat transfer fluid specified above returns from your process after heat has been extracted. In other words, this is your cold' temperature. If you have an open system, the inlet temperature will be assumed to be ambient temperature (20 C / 68 F)."
    )
    acres_per_kw = models.FloatField(
        default=0.000939,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        help_text="Power density for CST"
    )
    installed_cost_per_kw = models.FloatField(
        default=2200.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e5)
        ],
        blank=True,
        help_text="Installed CST cost in $/kW"
    )
    om_cost_per_kw = models.FloatField(
        default=33.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        help_text="Annual CST operations and maintenance costs in $/kW"
    )
    om_cost_per_kwh = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e3)
        ],
        blank=True,
        help_text="Annual CST operations and maintenance costs in $/kWh"
    )
    macrs_option_years = models.IntegerField(
        default=MACRS_YEARS_CHOICES.ZERO,
        choices=MACRS_YEARS_CHOICES.choices,
        blank=True,
        help_text="Duration over which accelerated depreciation will occur. Set to zero to disable"
    )
    macrs_bonus_fraction = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        blank=True,
        help_text="Percent of upfront project costs to depreciate in year one in addition to scheduled depreciation"
    )
    production_factor = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list, blank=True,
        help_text=("Optional user-defined production factors for CST.")
    )
    elec_consumption_factor_series = ArrayField(
        models.FloatField(
            blank=True
        ),
        default=list, blank=True,
        help_text=("Optional user-defined electricity consumption factors for CST.")
    )
    can_supply_steam_turbine = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CST can supply steam to the steam turbine for electric production"   
    )
    can_serve_dhw = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CST can serve hot water load"   
    )
    can_serve_space_heating = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CST can serve space heating load"   
    )
    can_serve_process_heat = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CST can serve process heat load"   
    )
    charge_storage_only = models.BooleanField(
        default=False,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CST can only supply hot TES"   
    )
    can_waste_heat = models.BooleanField(
        default=True,
        null=True, 
        blank=True,
        help_text="Boolean indicator if CST waste (not use) heat relative to its potential production"   
    )    
    emissions_factor_lb_CO2_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        null=True,
        help_text="Pounds of CO2 emitted per MMBTU of fuel burned."
    )
    emissions_factor_lb_NOx_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        null=True,
        help_text="Pounds of CO2 emitted per MMBTU of fuel burned."
    )
    emissions_factor_lb_SO2_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        null=True,
        help_text="Pounds of CO2 emitted per MMBTU of fuel burned."
    )
    emissions_factor_lb_PM25_per_mmbtu = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1e4)
        ],
        blank=True,
        null=True,
        help_text="Pounds of CO2 emitted per MMBTU of fuel burned."
    )

class CSTOutputs(BaseModel, models.Model):
    key = "CSTOutputs"
    meta = models.OneToOneField(
        to=APIMeta,
        on_delete=models.CASCADE,
        related_name="CSTOutputs",
        unique=False
    )
    size_kw = models.FloatField(null=True, blank=True)
    size_mmbtu_per_hour = models.FloatField(null=True, blank=True)
    annual_electric_consumption_kwh = models.FloatField(null=True, blank=True)
    annual_thermal_production_mmbtu = models.FloatField(null=True, blank=True)
    thermal_production_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default=list, blank=True
    )
    electric_consumption_series_kw = ArrayField(
        models.FloatField(null=True, blank=True),
        default=list, blank=True
    )
    thermal_to_storage_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )
    thermal_to_high_temp_thermal_storage_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )
    thermal_to_steamturbine_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )
    thermal_curtailed_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        blank=True, default=list
    )
    thermal_to_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default=list, blank=True
    )    
    thermal_to_absorption_chiller_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )
    thermal_to_dhw_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default=list, blank=True
    )
    thermal_to_space_heating_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )
    thermal_to_process_heat_load_series_mmbtu_per_hour = ArrayField(
        models.FloatField(null=True, blank=True),
        default = list
    )


def get_input_dict_from_run_uuid(run_uuid:str):
    """
    Construct the input dict for REopt.run_reopt
    """
    # get inputs that are always created with one DB transaction
    meta = APIMeta.objects.select_related(
        "Settings",
        'FinancialInputs', 
        'SiteInputs',
        'ElectricLoadInputs',
    ).get(run_uuid=run_uuid)

    def filter_none_and_empty_array(d:dict):
        return {k: v for (k, v) in d.items() if v not in [None, [], {}, ""]}

    d = dict()
    d["user_uuid"] = meta.user_uuid
    d["api_key"] = meta.api_key
    d["Settings"] = filter_none_and_empty_array(meta.Settings.dict)
    d["Financial"] = filter_none_and_empty_array(meta.FinancialInputs.dict)
    d["Site"] = filter_none_and_empty_array(meta.SiteInputs.dict)
    d["ElectricLoad"] = filter_none_and_empty_array(meta.ElectricLoadInputs.dict)

    # We have to try for the following objects because they may or may not be defined
    try:
        pvs = meta.PVInputs.all()
        if len(pvs) == 1:
            d["PV"] = filter_none_and_empty_array(pvs[0].dict)
        elif len(pvs) > 1:
            d["PV"] = []
            for pv in pvs:
                d["PV"].append(filter_none_and_empty_array(pv.dict))
    except: pass

    # Try to get electric tariff as it may be missing in off-grid scenarios
    try: d["ElectricTariff"] = filter_none_and_empty_array(meta.ElectricTariffInputs.dict)
    except: pass

    try: d["ElectricUtility"] = filter_none_and_empty_array(meta.ElectricUtilityInputs.dict)
    except: pass

    try: d["ElectricStorage"] = filter_none_and_empty_array(meta.ElectricStorageInputs.dict)
    except: pass

    try: d["Generator"] = filter_none_and_empty_array(meta.GeneratorInputs.dict)
    except: pass

    try: d["Wind"] = filter_none_and_empty_array(meta.WindInputs.dict)
    except: pass

    try: d["CoolingLoad"] = filter_none_and_empty_array(meta.CoolingLoadInputs.dict)
    except: pass

    try: d["ExistingChiller"] = filter_none_and_empty_array(meta.ExistingChillerInputs.dict)
    except: pass

    try: d["Boiler"] = filter_none_and_empty_array(meta.BoilerInputs.dict)
    except: pass

    try: d["ExistingBoiler"] = filter_none_and_empty_array(meta.ExistingBoilerInputs.dict)
    except: pass

    try: d["SpaceHeatingLoad"] = filter_none_and_empty_array(meta.SpaceHeatingLoadInputs.dict)
    except: pass

    try: d["DomesticHotWaterLoad"] = filter_none_and_empty_array(meta.DomesticHotWaterLoadInputs.dict)
    except: pass

    try: d["ProcessHeatLoad"] = filter_none_and_empty_array(meta.ProcessHeatLoadInputs.dict)
    except: pass

    try: d["HotThermalStorage"] = filter_none_and_empty_array(meta.HotThermalStorageInputs.dict)
    except: pass

    try: d["HighTempThermalStorage"] = filter_none_and_empty_array(meta.HighTempThermalStorageInputs.dict)
    except: pass

    try: d["ColdThermalStorage"] = filter_none_and_empty_array(meta.ColdThermalStorageInputs.dict)
    except: pass
    
    try: d["CHP"] = filter_none_and_empty_array(meta.CHPInputs.dict)
    except: pass

    try: d["SteamTurbine"] = filter_none_and_empty_array(meta.SteamTurbineInputs.dict)
    except: pass

    try: d["AbsorptionChiller"] = filter_none_and_empty_array(meta.AbsorptionChillerInputs.dict)
    except: pass  

    try: d["GHP"] = filter_none_and_empty_array(meta.GHPInputs.dict)
    except: pass   

    try: d["ElectricHeater"] = filter_none_and_empty_array(meta.ElectricHeaterInputs.dict)
    except: pass

    try: d["ASHPSpaceHeater"] = filter_none_and_empty_array(meta.ASHPSpaceHeaterInputs.dict)
    except: pass   

    try: d["ASHPWaterHeater"] = filter_none_and_empty_array(meta.ASHPWaterHeaterInputs.dict)
    except: pass   

    try: d["CST"] = filter_none_and_empty_array(meta.CSTInputs.dict)
    except: pass


    return d

'''
If a scalar was provided where API expects a vector, extend it to 8760
Upsampling handled in InputValidator.cross_clean
'''
def scalar_or_monthly_to_8760(vec:list):
    if len(vec) == 1: # scalar length is provided
        return vec * 8760
    elif len(vec) == 12: # Monthly costs were provided
        days_per_month = [31,28,31,30,31,30,31,31,30,31,30,31]
        return numpy.repeat(vec, [i * 24 for i in days_per_month]).tolist()
    else:
        return vec # the vector len was not 1 or 12, handle it elsewhere