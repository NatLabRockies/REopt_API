# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import sys
import logging
import copy
from django.db import models
from django.db.models.fields import NOT_PROVIDED
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from reo.models import ScenarioModel
from reo.exceptions import SaveToDatabase
log = logging.getLogger(__name__)

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
            if field.attname.endswith("id") and field.attname != "reopt_run_uuid": continue
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
        
class ERPMeta(BaseModel, models.Model):
    run_uuid = models.UUIDField(unique=True)
    user_uuid = models.TextField(
        blank=True,
        default="",
        help_text="The assigned unique ID of a signed in REopt user."
    )
    reopt_run_uuid = models.UUIDField(
        blank=True,
        null=True,
        help_text="The unique ID of a REopt optimization run from which to load inputs."
    )
    job_type = models.TextField(
        default='developer.nlr.gov'
    )
    status = models.TextField(
        blank=True,
        default="",
        help_text="Status of the ERP job."

    )
    created = models.DateTimeField(auto_now_add=True)
    reopt_version = models.TextField(
        blank=True,
        null=True,
        default="",
        help_text="Version number of the REopt Julia package that is used to calculate reliability."
    )

class ERPGeneratorInputs(BaseModel, models.Model):
    key = "Generator"
    meta = models.OneToOneField(
        ERPMeta,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="ERPGeneratorInputs"
    )
    operational_availability = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        default=0.995, 
        blank=True,
        help_text=("Fraction of the year that each generator unit is not down for maintenance")
    )
    failure_to_start = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        default=0.0094,
        blank=True,
        help_text=("Chance of generator not starting when an outage occurs")
    )
    mean_time_to_failure = models.FloatField(
        validators=[
            MinValueValidator(1)
        ],
        default=1100,
        blank=True,
        help_text=("Average number of time steps between a generator's failures. 1/(failure to run probability).")
    )
    num_generators = models.IntegerField(
        validators=[
            MinValueValidator(1)
        ],
        blank=True,
        default=1,
        help_text=("Number of generator units")
    )
    size_kw = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        default=0.0,
        help_text=("Generator unit capacity")
    )
    fuel_avail_gal = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        default=1.0e9,
        help_text=("Amount of diesel fuel available, either for all generators or per generator depending on value of fuel_avail_gal_is_per_generator.")
    )
    fuel_avail_gal_is_per_generator = models.BooleanField(
        default=False,
        blank=True,
        help_text=("Whether fuel_avail_gal is per generator or per generator type")
    )
    electric_efficiency_half_load = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        null=True,
        help_text=("Electric efficiency of generator running at half load. Defaults to electric_efficiency_full_load")
    )
    electric_efficiency_full_load = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        default=0.34,
        help_text=("Electric efficiency of generator running at full load.")
    )

    def clean(self):
        if not self.electric_efficiency_half_load:
            self.electric_efficiency_half_load = self.electric_efficiency_full_load

    def info_dict(self):
        d = super().info_dict(self)
        d["electric_efficiency_half_load"]["default"] = "electric_efficiency_full_load"
        return d

class ERPPrimeGeneratorInputs(BaseModel, models.Model):
    key = "PrimeGenerator"
    meta = models.OneToOneField(
        ERPMeta,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="ERPPrimeGeneratorInputs"
    )
    is_chp = models.BooleanField(
        default=False,
        blank=True,
        help_text=("Whether prime generator system is CHP")
    )
    PRIME_MOVER = models.TextChoices('PRIME_MOVER', (
        "recip_engine",
        "micro_turbine",
        "combustion_turbine",
        "fuel_cell"
    ))
    prime_mover = models.TextField(
        default="recip_engine",
        choices=PRIME_MOVER.choices,
        help_text="Prime generator/CHP prime mover, one of recip_engine, micro_turbine, combustion_turbine, fuel_cell"
    )
    operational_availability = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        null=True,
        blank=True,
        help_text=("Fraction of the year that each prime generator/CHP unit is not down for maintenance")
    )
    failure_to_start = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        default=0,
        blank=True,
        help_text=("Chance of prime generator/CHP unit not starting when an outage occurs")
    )
    mean_time_to_failure = models.FloatField(
        validators=[
            MinValueValidator(1)
        ],
        null=True,
        blank=True,
        help_text=("Average number of time steps between a prime generator/CHP unit's failures. 1/(failure to run probability).")
    )
    num_generators = models.IntegerField(
        validators=[
            MinValueValidator(1)
        ],
        blank=True,
        default=1,
        help_text=("Number of prime generator/CHP units")
    )
    size_kw = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        blank=True,
        default=0.0,
        help_text=("Prime generator/CHP unit electric capacity")
    )
    electric_efficiency_half_load = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        blank=True,
        null=True,
        help_text=("Electric efficiency of prime generator/CHP unit running at half load. Defaults to electric_efficiency_full_load")
    )
    electric_efficiency_full_load = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        default=0.34,
        help_text=("Electric efficiency of prime generator/CHP unit running at full load.")
    )

    def op_avail(self, prime_mover, is_chp, size_kw):
        size_class_index = 1 if (
                prime_mover == "recip_engine" and size_kw > 800
            ) or (
                prime_mover == "combustion_turbine" and size_kw > 5000
            ) else 0
        return {
                True: {
                    "recip_engine": [0.96, 0.98],
                    "micro_turbine": [None],
                    "combustion_turbine": [0.98, 0.97],
                    "fuel_cell": [0.9]
                },
                False: {
                    "recip_engine": [0.96, 0.98],
                    "micro_turbine": [None],
                    "combustion_turbine": [0.98, 0.97],
                    "fuel_cell": [None]
                }
            }[is_chp][prime_mover][size_class_index]
        
    def mttf(self, prime_mover, is_chp, size_kw):
        size_class_index = 1 if (
                prime_mover == "recip_engine" and size_kw > 800
            ) or (
                prime_mover == "combustion_turbine" and size_kw > 5000
            ) else 0
        return {
                True: {
                    "recip_engine": [870, 2150],
                    "micro_turbine": [None],
                    "combustion_turbine": [990, 3160],
                    "fuel_cell": [2500]
                },
                False: {
                    "recip_engine": [920, 2300],
                    "micro_turbine": [None],
                    "combustion_turbine": [1040, 3250],
                    "fuel_cell": [2500]
                }
            }[is_chp][prime_mover][size_class_index]

    def clean(self):
        prime_mover = str(self.prime_mover)
        is_chp = bool(self.is_chp)
        size_kw = float(self.size_kw)
        if not self.electric_efficiency_half_load:
            self.electric_efficiency_half_load = self.electric_efficiency_full_load
        if not self.operational_availability:
            self.operational_availability = self.op_avail(prime_mover, is_chp, size_kw)
        if not self.mean_time_to_failure:
            self.mean_time_to_failure = self.mttf(prime_mover, is_chp, size_kw)
        error_messages = {}
        if self.operational_availability is None and self.mean_time_to_failure is None:
            error_messages["required inputs"] = "Must provide operational_availability and mean_time_to_failure to model {} with the specified prime_mover".format(self.key)
        elif self.operational_availability is None:
            error_messages["required inputs"] = "Must provide operational_availability to model {} with the specified prime_mover".format(self.key)
        elif self.mean_time_to_failure is None:
            error_messages["required inputs"] = "Must provide mean_time_to_failure to model {} with the specified prime_mover".format(self.key)
        if error_messages:
            raise ValidationError(error_messages)
    
    def info_dict(self):
        d = super().info_dict(self)
        d["electric_efficiency_half_load"]["default"] = "electric_efficiency_full_load"
        return d

    def info_dict_with_dependent_defaults(self, prime_mover:str, is_chp:bool, size_kw:float):
        d = self.info_dict(self)
        d["operational_availability"]["default"] = self.op_avail(self, prime_mover, is_chp, size_kw)
        d["mean_time_to_failure"]["default"] = self.mttf(self, prime_mover, is_chp, size_kw)
        return d

class ERPElectricStorageInputs(BaseModel, models.Model):
    key = "ElectricStorage"
    meta = models.OneToOneField(
        ERPMeta,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="ERPElectricStorageInputs"
    )
    operational_availability = models.FloatField(
        blank=True,
        default=0.97,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        help_text=("Fraction of the year that the battery system is not down for maintenance")
    )
    size_kw = models.FloatField(
        blank=True,
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        help_text=("Battery kW power capacity")
    )
    size_kwh = models.FloatField(
        blank=True,
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        help_text=("Battery kWh energy capacity")
    )
    starting_soc_series_fraction = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0)
            ]
        ),
        blank=True,
        default=list,
        help_text=("Battery state of charge fraction when an outage begins, at each timestep. Must be hourly (8,760 samples).")
    )
    charge_efficiency = models.FloatField(
        blank=True,
        default=0.948,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        help_text=("Efficiency of charging battery")
    )
    discharge_efficiency = models.FloatField(
        blank=True,
        default=0.948,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        help_text=("Efficiency of discharging battery")
    )
    num_battery_bins = models.IntegerField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(2000)
        ],
        help_text=("Number of bins for discretely modeling battery state of charge")
    )
    minimum_soc_fraction = models.FloatField(
        blank=True,
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        help_text=("Minimum battery state of charge allowed during an outage")
    )

    def clean(self):
        if self.num_battery_bins is None:
            if self.size_kw == 0:
                self.num_battery_bins = 1
            else:
                self.num_battery_bins = round(20 * self.size_kwh / self.size_kw)


class ERPPVInputs(BaseModel, models.Model):
    key = "PV"
    meta = models.OneToOneField(
        ERPMeta,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="ERPPVInputs"
    )    
    operational_availability = models.FloatField(
        blank=True,
        default=0.98,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        help_text=("Fraction of the year that the PV system is not down for maintenance")
    )
    size_kw = models.FloatField(
        blank=True,
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        help_text=("PV system capacity")
    )
    #TODO: add units to name (_kw_per_kw_rated)?
    production_factor_series = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1)
            ]
        ),
        blank=True,
        default=list,
        help_text=("PV system output at each timestep, normalized to PV system size. Must be hourly (8,760 samples).")
    )

class ERPWindInputs(BaseModel, models.Model):
    key = "Wind"
    meta = models.OneToOneField(
        ERPMeta,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="ERPWindInputs"
    )    
    operational_availability = models.FloatField(
        blank=True,
        default=0.97,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0)
        ],
        help_text=("Fraction of the year that the wind system is not down for maintenance")
    )
    size_kw = models.FloatField(
        blank=True,
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1.0e9)
        ],
        help_text=("Wind system capacity")
    )
    #TODO: add units to name (_kw_per_kw_rated)?
    production_factor_series = ArrayField(
        models.FloatField(
            validators=[
                MinValueValidator(0),
                MaxValueValidator(1)
            ]
        ),
        blank=True,
        default=list,
        help_text=("Wind system output at each timestep, normalized to wind system size. Must be hourly (8,760 samples).")
    )

class ERPOutageInputs(BaseModel, models.Model):
    key = "Outage"
    meta = models.OneToOneField(
        ERPMeta,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="ERPOutageInputs"
    )
    max_outage_duration = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(672),
        ],
        help_text=("Maximum outage duration modeled")
    )
    critical_loads_kw = ArrayField(
        models.FloatField(blank=True),
        help_text=("Critical load during an outage. Must be hourly (8,760 samples). All non-net load values must be greater than or equal to zero.")
    )

    
class ERPOutputs(BaseModel, models.Model):
    meta = models.OneToOneField(
        ERPMeta,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="ERPOutputs"
    )
    unlimited_fuel_mean_cumulative_survival_by_duration = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The mean, calculated over outages starting at each hour of the year, of the probability of surviving up to and including each hour of max_outage_duration, if generator fuel is unlimited.")
    )
    unlimited_fuel_min_cumulative_survival_by_duration = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The minimum, calculated over outages starting at each hour of the year, of the probability of surviving up to and including each hour of max_outage_duration, if generator fuel is unlimited.")
    )
    unlimited_fuel_cumulative_survival_final_time_step = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The probability of surviving the full max_outage_duration, for outages starting at each hour of the year, if generator fuel is unlimited.")
    )
    mean_fuel_survival_by_duration = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The probability, averaged over outages starting at each hour of the year, of having sufficient fuel to survive up to and including each hour of max_outage_duration.")
    )
    fuel_survival_final_time_step = ArrayField(
        models.IntegerField(blank=True),
        blank=True,
        default=list,
        help_text=("Whether there is sufficient fuel to survive the full max_outage_duration, for outages starting at each hour of the year. A 1 means true, a 0 means false.")
    )
    mean_cumulative_survival_by_duration = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The mean, calculated over outages starting at each hour of the year, of the probability of surviving up to and including each hour of max_outage_duration.")
    )
    min_cumulative_survival_by_duration = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The minimum, calculated over outages starting at each hour of the year, of the probability of surviving up to and including each hour of max_outage_duration.")
    )
    cumulative_survival_final_time_step = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The probability of surviving the full max_outage_duration, for outages starting at each hour of the year.")
    )
    mean_cumulative_survival_final_time_step = models.FloatField(
        null=True,
        blank=True,
        help_text=("The mean, calculated over outages starting at each hour of the year, of the probability of surviving the full max_outage_duration.")
    )
    monthly_min_cumulative_survival_final_time_step = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The monthly minimums, calculated over outages starting at each hour of the month, of the probability of surviving the full max_outage_duration.")
    )
    monthly_lower_quartile_cumulative_survival_final_time_step = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The monthly lower quartile cutoff, calculated over outages starting at each hour of the month, of the probability of surviving the full max_outage_duration.")
    )
    monthly_median_cumulative_survival_final_time_step = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The monthly medians, calculated over outages starting at each hour of the month, of the probability of surviving the full max_outage_duration.")
    )
    monthly_upper_quartile_cumulative_survival_final_time_step = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The monthly upper quartile cutoff, calculated over outages starting at each hour of the month, of the probability of surviving the full max_outage_duration.")
    )
    monthly_max_cumulative_survival_final_time_step = ArrayField(
        models.FloatField(blank=True),
        blank=True,
        default=list,
        help_text=("The monthly maximums, calculated over outages starting at each hour of the month, of the probability of surviving the full max_outage_duration.")
    )

class ResilienceModel(models.Model):

    scenariomodel = models.OneToOneField(
        ScenarioModel,
        to_field='id',
        on_delete=models.CASCADE,
        default=None,
        null=True,
        blank=True
    )
    # WITH TECH
    resilience_by_timestep = ArrayField(models.FloatField(null=True), null=True)
    resilience_hours_min = models.FloatField(null=True)
    resilience_hours_max = models.FloatField(null=True)
    resilience_hours_avg = models.FloatField(null=True)
    outage_durations = ArrayField(models.FloatField(null=True), null=True)
    probs_of_surviving = ArrayField(models.FloatField(null=True), null=True)
    probs_of_surviving_by_month = ArrayField(ArrayField(models.FloatField(null=True), null=True), null=True)
    probs_of_surviving_by_hour_of_the_day = ArrayField(ArrayField(models.FloatField(null=True), null=True), null=True)
    # BAU
    resilience_by_timestep_bau = ArrayField(models.FloatField(null=True), null=True)
    resilience_hours_min_bau = models.FloatField(null=True)
    resilience_hours_max_bau = models.FloatField(null=True)
    resilience_hours_avg_bau = models.FloatField(null=True)
    outage_durations_bau = ArrayField(models.FloatField(null=True), null=True)
    probs_of_surviving_bau = ArrayField(models.FloatField(null=True), null=True)
    probs_of_surviving_by_month_bau = ArrayField(ArrayField(models.FloatField(null=True), null=True), null=True)
    probs_of_surviving_by_hour_of_the_day_bau = ArrayField(ArrayField(models.FloatField(null=True), null=True),
                                                           null=True)
    avoided_outage_costs_us_dollars = models.FloatField(null=True, blank=True)
    present_worth_factor = models.FloatField(null=True)
    avg_critical_load = models.FloatField(null=True)

    @classmethod
    def create(cls, scenariomodel, **kwargs):
        rm = cls(scenariomodel=scenariomodel, **kwargs)
        try:
            rm.save()
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err = SaveToDatabase(exc_type, exc_value.args[0], exc_traceback, task='resilience_model', run_uuid=scenariomodel.run_uuid)
            err.save_to_db()
            raise err
        return rm

def get_erp_input_dict_from_run_uuid(run_uuid:str):
    """
    Construct the input dict for REopt backup reliability
    """
    meta = ERPMeta.objects.select_related("ERPOutageInputs").get(run_uuid=run_uuid)

    def filter_none_and_empty_array(d:dict):
        return {k: v for (k, v) in d.items() if v not in [None, [], {}]}

    def add_tech_prefixes(d:dict, prefix):
        keys_to_add_tech_prefix = {
                                    "operational_availability",
                                    "failure_to_start",
                                    "mean_time_to_failure",
                                    "fuel_intercept_per_hr",
                                    "fuel_burn_rate_per_kwh",
                                    "size_kw",
                                    "size_kwh",
                                    "starting_soc_series_fraction",
                                    "charge_efficiency",
                                    "discharge_efficiency",
                                    "production_factor_series",
                                    "minimum_soc_fraction"
                                }
        return {(prefix + "_" + k if k in keys_to_add_tech_prefix else k): v for (k, v) in d.items()}
    
    def merge_generator_inputs(gen_dicts:list):
        #assumes gen_dicts not empty and all dicts in it have all same keys
        return {k: [gen_type[k] for gen_type in gen_dicts] for k in gen_dicts[0].keys()}

    d = dict()
    d["user_uuid"] = meta.user_uuid # Add user_uuid for error handling in run_erp_task
    d.update(filter_none_and_empty_array(meta.ERPOutageInputs.dict))
    try:
        d.update(add_tech_prefixes(filter_none_and_empty_array(meta.ERPElectricStorageInputs.dict),"battery"))
    except: pass
    try:
        d.update(add_tech_prefixes(filter_none_and_empty_array(meta.ERPPVInputs.dict),"pv"))
    except: pass
    try:
        d.update(add_tech_prefixes(filter_none_and_empty_array(meta.ERPWindInputs.dict),"wind"))
    except: pass
    gen_dicts = []
    try: 
        gen = meta.ERPGeneratorInputs.dict

        # Temp conversions until extend input structure changes to julia
        # convert efficiency to slope/intercept in gen dict
        KWH_PER_GAL_DIESEL = 40.7
        fuel_burn_full_load_kwht = 1.0 / gen.pop("electric_efficiency_full_load")  # [kWe_rated/(kWhe/kWht)]
        fuel_burn_half_load_kwht = 0.5 / gen.pop("electric_efficiency_half_load")  # [kWe_rated/(kWhe/kWht)]
        fuel_slope_kwht_per_kwhe = (fuel_burn_full_load_kwht - fuel_burn_half_load_kwht) / (1.0 - 0.5)  # [kWht/kWhe]
        fuel_intercept_kwht_per_hr = fuel_burn_full_load_kwht - fuel_slope_kwht_per_kwhe * 1.0  # [kWht/hr]
        gen["fuel_burn_rate_per_kwh"] = fuel_slope_kwht_per_kwhe / KWH_PER_GAL_DIESEL # [gal/kWhe]
        gen["fuel_intercept_per_hr"] = fuel_intercept_kwht_per_hr / KWH_PER_GAL_DIESEL # [gal/hr]
        # change fuel_avail_gal to fuel_limit
        gen["fuel_limit"] = gen.pop("fuel_avail_gal")
        gen["fuel_limit_is_per_generator"] = gen.pop("fuel_avail_gal_is_per_generator")
    
        gen_dicts.append(gen)
    except AttributeError: pass
    try: 
        gen = meta.ERPPrimeGeneratorInputs.dict
        gen.pop("prime_mover")
        gen.pop("is_chp")

        # Temp conversions until extend input structure changes to julia
        # convert efficiency to slope/intercept in gen dict
        fuel_burn_full_load = 1.0 / gen.pop("electric_efficiency_full_load")
        fuel_burn_half_load = 0.5 / gen.pop("electric_efficiency_half_load")
        gen["fuel_burn_rate_per_kwh"] = (fuel_burn_full_load - fuel_burn_half_load) / (1.0 - 0.5)  # [kWht/kWhe]
        gen["fuel_intercept_per_hr"] = fuel_burn_full_load - gen["fuel_burn_rate_per_kwh"] * 1.0  # [kWht/hr]
        # add fuel_limit
        gen["fuel_limit"] = 1e9
        gen["fuel_limit_is_per_generator"] = True
    
        gen_dicts.append(gen)
    except AttributeError: pass
    if gen_dicts != []:
        d.update(add_tech_prefixes(filter_none_and_empty_array(merge_generator_inputs(gen_dicts)), "generator"))

    # TODO: do this instead once extend input structure changes to julia (and do conversion of effic to slope/intercept in julia using existing util function)
    # d["Generator"] = filter_none_and_empty_array(meta.ERPGeneratorInputs.dict)
    # d["PrimeGenerator"] = filter_none_and_empty_array(meta.ERPPrimeGeneratorInputs.dict)
    # d["ElectricStorage"] = filter_none_and_empty_array(meta.ERPElectricStorageInputs.dict)
    # d["PV"] = filter_none_and_empty_array(meta.ERPPVInputs.dict)
    # d["Outage"] = filter_none_and_empty_array(meta.ERPOutageInputs.dict)

    return d