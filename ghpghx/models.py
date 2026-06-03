# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import logging
from django.db import models
from django.contrib.postgres.fields import *
from django.forms.models import model_to_dict
from picklefield.fields import PickledObjectField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
import pandas as pd
import os

log = logging.getLogger(__name__)


class GHPGHXInputs(models.Model):
    # Inputs

    ghp_uuid = models.UUIDField(primary_key=True, unique=True, editable=False)
    status = models.TextField(blank=True, default="")
    latitude = models.FloatField(null=True, blank=True,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
        help_text="Latitude of the site")
    longitude = models.FloatField(null=True, blank=True,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
        help_text="Longitude of the site")
    
    # Single value inputs
    borehole_depth_ft = models.FloatField(blank=True, 
        default=443.0, validators=[MinValueValidator(10.0), MaxValueValidator(600.0)],
        help_text="Vertical depth of each borehole [ft]")
    ghx_header_depth_ft = models.FloatField(blank=True, 
        default=6.6, validators=[MinValueValidator(0.1), MaxValueValidator(50.0)],
        help_text="Depth under the ground of the GHX header pipe [ft]")
    borehole_spacing_ft = models.FloatField(blank=True, 
        default=20.0, validators=[MinValueValidator(1.0), MaxValueValidator(100.0)],
        help_text="Distance from the centerline of each borehole to the centerline of its adjacent boreholes [ft]")
    borehole_diameter_inch = models.FloatField(blank=True, 
        default=6.0, validators=[MinValueValidator(0.25), MaxValueValidator(24.0)],
        help_text="Diameter of the borehole/well drilled in the ground [in]")
    borehole_choices = [("rectangular", "rectangular"),
                        ("hexagonal", "hexagonal")]
    borehole_spacing_type = models.TextField(blank=True,
        default="rectangular", choices=borehole_choices,
        help_text="Borehole spacing pattern type: rectangular or hexagonal")
    ghx_pipe_outer_diameter_inch = models.FloatField(blank=True, 
        default=1.66, validators=[MinValueValidator(0.25), MaxValueValidator(24.0)],
        help_text="Outer diameter of the GHX pipe [in]")
    ghx_pipe_wall_thickness_inch = models.FloatField(blank=True, 
        default=0.16, validators=[MinValueValidator(0.01), MaxValueValidator(5.0)],
        help_text="Wall thickness of the GHX pipe [in]")
    ghx_pipe_thermal_conductivity_btu_per_hr_ft_f = models.FloatField(blank=True, 
        default=0.23, validators=[MinValueValidator(0.01), MaxValueValidator(10.0)],
        help_text="Thermal conductivity of the GHX pipe [Btu/(hr-ft-degF)]")
    ghx_shank_space_inch = models.FloatField(blank=True, 
        default=1.27, validators=[MinValueValidator(0.5), MaxValueValidator(100.0)],
        help_text="Distance between the centerline of the upwards and downwards u-tube legs [in]")
    # Default for ground_thermal_conductivity_btu_per_hr_ft_f varies by ASHRAE climate zone
    ground_thermal_conductivity_btu_per_hr_ft_f = models.FloatField(blank=True, 
        default=1.18, validators=[MinValueValidator(0.01), MaxValueValidator(15.0)],
        help_text="Thermal conductivity of the ground surrounding the borehole field [Btu/(hr-ft-degF)]")
    ground_mass_density_lb_per_ft3 = models.FloatField(blank=True,
        default=162.3, validators=[MinValueValidator(10.0), MaxValueValidator(500.0)],
        help_text="Mass density of the ground surrounding the borehole field [lb/ft^3]")
    ground_specific_heat_btu_per_lb_f = models.FloatField(blank=True, 
        default=0.211, validators=[MinValueValidator(0.01), MaxValueValidator(5.0)],
        help_text="Specific heat of the ground surrounding the borehole field")
    grout_thermal_conductivity_btu_per_hr_ft_f = models.FloatField(blank=True, 
        default=0.75, validators=[MinValueValidator(0.01), MaxValueValidator(10.0)],
        help_text="Thermal conductivity of the grout material in a borehole [Btu/(hr-ft-degF)]")
    ghx_fluid_specific_heat_btu_per_lb_f = models.FloatField(blank=True, 
        default=1.0, validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        help_text="Specific heat of the fluid in the GHX (nominally water) [Btu/(lb-degF)]")
    ghx_fluid_mass_density_lb_per_ft3 = models.FloatField(blank=True, 
        default=62.4, validators=[MinValueValidator(1.0), MaxValueValidator(200.0)],
        help_text="Mass density of the fluid in the GHX (nominally water) [lb/ft^3]")
    ghx_fluid_thermal_conductivity_btu_per_hr_ft_f = models.FloatField(blank=True, 
        default=0.34, validators=[MinValueValidator(0.01), MaxValueValidator(5.0)],
        help_text="Thermal conductivity of the fluid in the GHX (nominally water) [Btu/(hr-ft-degF)]")
    ghx_fluid_dynamic_viscosity_lbm_per_ft_hr = models.FloatField(blank=True, 
        default=2.75, validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        help_text="Dynamic viscosity of the fluid in the GHX (nominally water) [lb/(ft-hr)]")
    ghx_fluid_flow_rate_gpm_per_ton = models.FloatField(blank=True, 
        default=2.5, validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        help_text="Volumetric flow rate of the fluid in the GHX per peak ton heating/cooling [GPM/ton]")
    ghx_pump_power_watt_per_gpm = models.FloatField(blank=True, 
        default=15.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Pumping power required for a given volumetric flow rate of the fluid in the GHX [Watt/GPM]")
    ghx_pump_min_speed_fraction = models.FloatField(blank=True, 
        default=0.1, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="The minimum turndown fraction of the pump. 1.0 is a constant speed pump.")
    ghx_pump_power_exponent = models.FloatField(blank=True, 
        default=2.2, validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        help_text="The pump power curve exponent")
    max_eft_allowable_f = models.FloatField(blank=True, 
        default=104.0, validators=[MinValueValidator(0.0), MaxValueValidator(150.0)],
        help_text="Maximum allowable entering fluid temperature (EFT) of the heat pump (used in cooling dominated loads) [degF]")
    min_eft_allowable_f = models.FloatField(blank=True, 
        default=23.0, validators=[MinValueValidator(-50.0), MaxValueValidator(100.0)],
        help_text="Minimum allowable entering fluid temperature (EFT) of the heat pump (used in heating dominated loads) [degF]")
    
    # Array/Dict inputs
    heating_thermal_load_mmbtu_per_hr = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly heating thermal load that GHP serves [MMBtu/hr]")
    # Heating **fuel** load and boiler_efficiency may be given instead of **thermal** load
    heating_fuel_load_mmbtu_per_hr = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly heating fuel load that GHP serves [MMBtu/hr]")
    existing_boiler_efficiency = models.FloatField(blank=True,
        default=0.8, validators=[MinValueValidator(0.01), MaxValueValidator(1.0)],
        help_text="Efficiency of the existing boiler/heater serving the heating load")
    cooling_thermal_load_ton = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly cooling thermal load that GHP serves [ton]")
    ambient_temperature_f = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly outdoor air dry bulb temperature, typically TMY3 data [degF]")
    
    def _get_cop_map():
        hp_cop_filepath = os.path.join('ghpghx', 'tests', 'posts', "heatpump_cop_map.csv" )
        heatpump_copmap_df = pd.read_csv(hp_cop_filepath)
        heatpump_copmap_list_of_dict = heatpump_copmap_df.to_dict('records')
        return heatpump_copmap_list_of_dict
        
    cop_map_eft_heating_cooling = ArrayField(
        PickledObjectField(editable=True), null=True,
        default=_get_cop_map,
        help_text="Heat pump coefficient of performance (COP) map: list of dictionaries, each with 3 keys: 1) EFT, 2) HeatingCOP, 3) CoolingCOP")

    def _get_wwhp_heating_cop_map():
        hp_cop_filepath = os.path.join('ghpghx', 'tests', 'posts', "wwhp_heating_heatpump_cop_map.csv" )
        heatpump_copmap_df = pd.read_csv(hp_cop_filepath)
        heatpump_copmap_list_of_dict = heatpump_copmap_df.to_dict('records')
        return heatpump_copmap_list_of_dict

    wwhp_cop_map_eft_heating = ArrayField(
        PickledObjectField(editable=True), null=True,
        default=_get_wwhp_heating_cop_map,
        help_text="WWHP heating heat pump coefficient of performance (COP) map: list of dictionaries, each with the key 'EFT' followed by keys representing temperature setpoints")

    def _get_wwhp_cooling_cop_map():
        hp_cop_filepath = os.path.join('ghpghx', 'tests', 'posts', "wwhp_cooling_heatpump_cop_map.csv" )
        heatpump_copmap_df = pd.read_csv(hp_cop_filepath)
        heatpump_copmap_list_of_dict = heatpump_copmap_df.to_dict('records')
        return heatpump_copmap_list_of_dict
        
    wwhp_cop_map_eft_cooling = ArrayField(
        PickledObjectField(editable=True), null=True,
        default=_get_wwhp_cooling_cop_map,
        help_text="WWHP cooling heat pump coefficient of performance (COP) map: list of dictionaries, each with the key 'EFT' followed by keys representing temperature setpoints")
    
    """
    TODO define custom clean_cop_map()
    def clean_cop_map(self):
        for pt in range(length(cop_map_eft_heating_cooling)):
            # Check that float values are present for each of the expected 3 key entries
            # Check if temps are in ascending order
            # Check min/max values
    
    TODO still have a validators.py that we import from if we want custom validators (might not need for GHPGHX app) 
    that can be reused easily by adding to model fields option validators=[validator1, validator2, etc]
    in that validators.py, we need to "from django.core.exceptions import ValidationError" to raise 
    ValidationError for those custom ones

    TODO define clean() method for validating related fields, such as ghx_pipe_outer_diameter_inch and ghx_shank_space_inch
    def clean(self):
        if ghx_shank_space_inch + 0.0001 < ghx_pipe_outer_diameter_inch
            raise ValidationError("Invalid shank space and ghx pipe diameter - pipes would interfere!)
    """

    # Model Settings
    simulation_years = models.IntegerField(blank=True, 
        default=25, validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="The time span for which GHX is sized to meet the entering fluid temperature constraints [year]")
    solver_eft_tolerance_f = models.FloatField(blank=True, 
        default=2.0, validators=[MinValueValidator(0.001), MaxValueValidator(5.0)],
        help_text="Tolerance for GHX sizing based on the entering fluid temperature limits [degF]")
    ghx_model_choices = [("TESS", "TESS")]#,
                         #("DST", "DST")] # DST is currently not available, pending license agreement
    ghx_model = models.TextField(blank=True,
        default="TESS", choices=ghx_model_choices,
        help_text="GHX model to use in the simulation: 'TESS' is the only option currently") # or DST")
    dst_ghx_timesteps_per_hour = models.IntegerField(blank=True, 
        default=12, validators=[MinValueValidator(1), MaxValueValidator(60)],
        help_text="Time steps per hour to use for the DST GHX model")
    tess_ghx_minimum_timesteps_per_hour = models.IntegerField(blank=True, 
        default=1, validators=[MinValueValidator(1), MaxValueValidator(60)],
        help_text="Minimum time steps per hour to use for the TESS GHX model; the model will decide if more is needed each hour")
    max_sizing_iterations = models.IntegerField(blank=True, 
        default=15, validators=[MinValueValidator(1), MaxValueValidator(15)],
        help_text="Maximum number of sizing iterations before the GHPGHX model times out")
    init_sizing_factor_ft_per_peak_ton = models.FloatField(blank=True, 
        default=75, validators=[MinValueValidator(1.0), MaxValueValidator(5000.0)],
        help_text="Initial guess of total feet of GHX boreholes (total feet = N bores * Length bore) based on peak ton heating/cooling [ft/ton]")
 
    # Hybrid flag
    hybrid_ghx_sizing_method = models.TextField(null=True, blank=True, default="None",
        help_text="Possible values: 'Fractional' (user inputs fraction of full GHX size), 'Automatic' (REopt determines based on the smaller heating or cooling load), 'Heater' (an auxiliary heating unit is sized), 'Cooler' (an auxiliary cooling unit is sized), 'None' (non-hybrid)")
    hybrid_auto_ghx_sizing_flag = models.BooleanField(blank=True, null=True, default=False)
    hybrid_sizing_flag = models.FloatField(null=True, blank=True, default=1.0,
        help_text="Possible values: -2 (size for heating), -1.0 (size for cooling), 1.0 (non-hybrid), value between 0-1 (fraction of full GHX size)") 
    hybrid_ghx_sizing_fraction = models.FloatField(null=True, blank=True, default=0.6,
        validators=[MinValueValidator(0.1), MaxValueValidator(1.0)],
        help_text="Applies fraction to full GHX size for hybrid sizing (value between 0.1 - 1.0)")
    is_heating_electric = models.BooleanField(null=True, blank=True, default=True,
        help_text="Set to True if heating is electric, false otherwise")  
    aux_heater_thermal_efficiency = models.FloatField(null=True, blank=True, 
        default=0.98, validators=[MinValueValidator(0.001), MaxValueValidator(1.0)],
        help_text="The thermal efficiency (thermal_out/fuel_in) of the auxiliary heater")
    aux_cooler_energy_use_intensity_kwe_per_kwt = models.FloatField(null=True, blank=True, 
        default=0.02, validators=[MinValueValidator(0.001), MaxValueValidator(1.0)],
        help_text="The energy use intensity of the auxiliary cooler [kWe/kWt]")
    
    # Central plant variables
    heat_pump_configuration = models.TextField(null=True, blank=True, default="WSHP",
        help_text="Specifies if the GHP system is centralized (WWHP) or decentralized (WSHP)")    
    wwhp_cooling_setpoint_f = models.FloatField(blank=True, 
        default=55.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Setpoint temperature of the chilled water cooling loop [degF]")
    wwhp_heating_setpoint_f = models.FloatField(blank=True, 
        default=140.0, validators=[MinValueValidator(0.0), MaxValueValidator(250.0)],
        help_text="Setpoint temperature of the space heating hot water loop [degF]")
    wwhp_heating_pump_fluid_flow_rate_gpm_per_ton = models.FloatField(blank=True, 
        default=3.0, validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        help_text="Volumetric flow rate of the fluid in the hydronic space heating loop per peak ton heating [GPM/ton]")
    wwhp_cooling_pump_fluid_flow_rate_gpm_per_ton = models.FloatField(blank=True, 
        default=3.0, validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        help_text="Volumetric flow rate of the fluid in the hydronic chilled water cooling loop per peak ton cooling [GPM/ton]")
    wwhp_heating_pump_power_watt_per_gpm = models.FloatField(blank=True, 
        default=15.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Pumping power required for a given volumetric flow rate of the fluid through the heating pump [Watt/GPM]")
    wwhp_cooling_pump_power_watt_per_gpm = models.FloatField(blank=True, 
        default=15.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Pumping power required for a given volumetric flow rate of the fluid through the cooling pump [Watt/GPM]")    
    wwhp_heating_pump_min_speed_fraction = models.FloatField(blank=True, 
        default=0.1, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="The minimum turndown fraction of the WWHP heating pump. 1.0 is a constant speed pump.")
    wwhp_cooling_pump_min_speed_fraction = models.FloatField(blank=True, 
        default=0.1, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="The minimum turndown fraction of the WWHP cooling pump. 1.0 is a constant speed pump.")
    wwhp_heating_pump_power_exponent = models.FloatField(blank=True, 
        default=2.2, validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        help_text="The WWHP heating pump power curve exponent")
    wwhp_cooling_pump_power_exponent = models.FloatField(blank=True, 
        default=2.2, validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        help_text="The WWHP cooling pump power curve exponent")

    
class GHPGHXOutputs(models.Model):
    # Outputs/results

    ghp_uuid = models.UUIDField(primary_key=True, unique=True, editable=False)
    number_of_boreholes = models.FloatField(null=True, blank=True,
        help_text="Minimum required number of boreholes to meet heat pump EWT constraints")
    length_boreholes_ft = models.FloatField(null=True, blank=True,
        help_text="Length of each borehole, drilled vertically in the ground [ft]")
    yearly_heating_heatpump_electric_consumption_series_kw = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly heating heat pump electric consumption, average across simulation years [kW]")
    yearly_cooling_heatpump_electric_consumption_series_kw = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly cooling heat pump electric consumption, average across simulation years [kW]")
    yearly_ghx_pump_electric_consumption_series_kw = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly GHX pump electric consumption, average across simulation years [kW]")
    yearly_total_electric_consumption_series_kw = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly total GHP electric consumption, average across simulation years [kW]")
    yearly_total_electric_consumption_kwh = models.FloatField(null=True, blank=True, 
        help_text="Total yearly electric consumption by GHPGHX system [kWh]")
    peak_heating_heatpump_thermal_ton = models.FloatField(null=True, blank=True, 
        help_text="Peak heating heat pump thermal load served [ton]")
    peak_cooling_heatpump_thermal_ton = models.FloatField(null=True, blank=True, 
        help_text="Peak cooling heat pump thermal load served [ton]")
    peak_combined_heatpump_thermal_ton = models.FloatField(null=True, blank=True, 
        help_text="Peak combined heating/cooling heat pump thermal load served [ton]")
    yearly_heat_pump_eft_series_f = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly heat pump entering fluid temperature (eft), average across simulation years [kW]")    
    max_eft_f = models.FloatField(null=True, blank=True, 
        help_text="Maximum entering fluid temperature (to heat pump, from ghx) throughout the GHPGHX simulation period")
    min_eft_f = models.FloatField(null=True, blank=True, 
        help_text="Minimum entering fluid temperature (to heat pump, from ghx) throughout the GHPGHX simulation period")
    heating_cop_avg = models.FloatField(null=True, blank=True, 
        help_text="Average heating heatpump system coefficient of performance (COP) (includes ghx pump allocation)")
    cooling_cop_avg = models.FloatField(null=True, blank=True, 
        help_text="Average cooling heatpump system coefficient of performance (COP) (includes ghx pump allocation)")
    solved_eft_error_f = models.FloatField(null=True, blank=True,
        help_text="Error between the solved GHPGHX system EFT and the max or min limit for EFT")
    # Hybrid
    yearly_aux_heater_thermal_production_series_mmbtu_per_hour = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly auxiliary heater thermal production, average across simulation years [MMBtu/hr]")
    yearly_aux_cooler_thermal_production_series_kwt = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly auxiliary cooler thermal production, average across simulation years [kW-thermal]")
    yearly_aux_heater_electric_consumption_series_kw = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly auxiliary heater electrical consumption, average across simulation years [kW]")
    yearly_aux_cooler_electric_consumption_series_kw = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly auxiliary cooler electrical consumption, average across simulation years [kW]")    
    peak_aux_heater_thermal_production_mmbtu_per_hour = models.FloatField(null=True, blank=True, 
        help_text="Peak auxiliary heater thermal production for heater sizing [MMBtu/hr]")
    peak_aux_cooler_thermal_production_ton = models.FloatField(null=True, blank=True, 
        help_text="Peak auxiliary cooler thermal production for cooler sizing [ton]")  
    annual_aux_heater_electric_consumption_kwh = models.FloatField(null=True, blank=True, 
        help_text="Annual auxiliary heater electrical consumption [kWh]")
    annual_aux_cooler_electric_consumption_kwh = models.FloatField(null=True, blank=True, 
        help_text="Annual auxiliary cooler electrical consumption [kWh]")      
    end_of_year_ghx_lft_f = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="End of year GHX leaving fluid temperature for all years in the last iteration of GHX sizing [degF]")
    max_yearly_ghx_lft_f = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Maximum GHX leaving fluid temperature for all years in the last iteration of GHX sizing [degF]")
    min_yearly_ghx_lft_f = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Minimum GHX leaving fluid temperature for all years in the last iteration of GHX sizing [degF]")
    aux_heat_exchange_unit_type = models.TextField(null=True, blank=True, 
        help_text="Specifies if the auxiliary heat exchange unit is a heater or cooler")
    yearly_ghx_lft_series_f = ArrayField(models.FloatField(null=True, blank=True), 
        default=list, null=True, blank=True,
        help_text="Hourly GHX leaving fluid temperature (lft), average across simulation years [kW]") 
    ghx_soln_number_of_iterations = models.IntegerField(null=True, blank=True, 
        help_text="The number of iterations taken to get GHX sizing")
    heat_pump_configuration = models.TextField(null=True, blank=True, 
        help_text="Specifies if the auxiliary heat exchange unit is a heater or cooler")
    
class ModelManager(object):

    def __init__(self):
        self.ghpghxInputsM = None
        self.ghpghxOutputsM = None

    @staticmethod
    def make_response(ghp_uuid):
        """
        Reconstruct response dictionary from postgres tables (django models).
        # TODO Make sure the NOTE below is not relevant for ghpghx because it uses primary_key=True for ghp_uuid
        NOTE: postgres column type UUID is not JSON serializable. Work-around is removing those columns and then
              adding back into outputs->Scenario as string.
        :param ghp_uuid:
        :return: nested dictionary matching nested_output_definitions
        """

        resp = dict()
        resp["ghp_uuid"] = str(ghp_uuid)
        resp["outputs"] = dict()
        resp["inputs"] = dict()
        resp["messages"] = dict()

        try:
            ghpghx_inputs_model = GHPGHXInputs.objects.get(ghp_uuid=ghp_uuid)
            ghpghx_outputs_model = GHPGHXOutputs.objects.get(ghp_uuid=ghp_uuid)
        except Exception as e:
            if isinstance(e, models.ObjectDoesNotExist):
                resp['messages']['error'] = (
                    "ghp_uuid {} not in database. "
                    "You may have hit the results endpoint too quickly after POST'ing scenario, "
                    "you may have a typo in your ghp_uuid, or the scenario was deleted.").format(ghp_uuid)
                resp['status'] = 'error'
                return resp
            else:
                raise Exception

        ghpghx_inputs_dict = model_to_dict(ghpghx_inputs_model)
        ghpghx_outputs_dict = model_to_dict(ghpghx_outputs_model)

        resp["inputs"] = ghpghx_inputs_dict
        resp["outputs"] = ghpghx_outputs_dict

        del resp["inputs"]["status"]

        return resp


