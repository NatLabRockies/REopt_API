# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NREL/REopt_API/blob/master/LICENSE.
import numpy as np
from cProfile import run
import json
from tastypie.test import ResourceTestCaseMixin
from django.test import TransactionTestCase 
# Using TransactionTestCase instead of TestCase b/c this avoids whole test being wrapped in a 
# transaction which leads to a TransactionManagementError when doing a database query in the middle.
# Using django.test flushes database, so if you don't want this use unittest.TestCase.
import logging
import requests
logging.disable(logging.CRITICAL)
import os


class TestJobEndpoint(ResourceTestCaseMixin, TransactionTestCase):

    def test_multiple_outages(self):

        scenario_file = os.path.join('reoptjl', 'test', 'posts', 'outage.json')
        scenario = json.load(open(scenario_file, 'r'))
        resp = self.api_client.post('/v3/job/', format='json', data=scenario)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')
        resp = self.api_client.get(f'/v3/job/{run_uuid}/results')
        r = json.loads(resp.content)
        self.assertIn("reopt_version", r.keys())
        results = r["outputs"]
        self.assertEqual(np.array(results["Outages"]["unserved_load_series_kw"]).shape, (1,2,5))
        self.assertEqual(np.array(results["Outages"]["generator_fuel_used_per_outage_gal"]).shape, (1,2))
        self.assertEqual(np.array(results["Outages"]["chp_fuel_used_per_outage_mmbtu"]).shape, (1,2))
        self.assertAlmostEqual(results["Outages"]["expected_outage_cost"], 0.0, places=-2)
        self.assertAlmostEqual(sum(sum(np.array(results["Outages"]["unserved_load_per_outage_kwh"]))), 0.0, places=0)
        # TODO figure out why microgrid_upgrade_capital_cost is about $3000 different locally than on GitHub Actions
        self.assertAlmostEqual(results["Outages"]["microgrid_upgrade_capital_cost"], 1974429.4, delta=5000.0)
        self.assertAlmostEqual(results["Financial"]["lcc"], 59865240.0, delta=0.01*results["Financial"]["lcc"])

    def test_pv_battery_and_emissions_defaults_from_julia(self):
        """
        Same test post as "Solar and ElectricStorage w/BAU" in the Julia package. Used in development of v3.
        Also tests that inputs with defaults determined in the REopt julia package get updated in the database.
        """
        post_file = os.path.join('reoptjl', 'test', 'posts', 'pv_batt_emissions.json')
        post = json.load(open(post_file, 'r'))

        resp = self.api_client.post('/v3/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')

        resp = self.api_client.get(f'/v3/job/{run_uuid}/results')
        r = json.loads(resp.content)
        results = r["outputs"]

        self.assertAlmostEqual(results["Financial"]["lcc"], 12391786, places=-3)
        self.assertAlmostEqual(results["Financial"]["lcc_bau"], 12766397, places=-3)
        self.assertAlmostEqual(results["PV"]["size_kw"], 216.667, places=1)
        self.assertAlmostEqual(results["ElectricStorage"]["size_kw"], 49.05, places=1)
        self.assertAlmostEqual(results["ElectricStorage"]["size_kwh"], 83.32, places=1)
    
        self.assertIsNotNone(results["Site"]["onsite_renewable_energy_fraction_of_total_load"])
        self.assertIsNotNone(results["Site"]["annual_emissions_tonnes_CO2"])
        self.assertIsNotNone(results["Site"]["lifecycle_emissions_tonnes_NOx"])

        #test that emissions inputs got updated in the database with the defaults determined in REopt julia package
        updated_inputs = r["inputs"]
        self.assertIsNotNone(updated_inputs["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"])
        self.assertIsNotNone(updated_inputs["Financial"]["NOx_grid_cost_per_tonne"])
        self.assertIsNotNone(updated_inputs["Financial"]["SO2_onsite_fuelburn_cost_per_tonne"])
        self.assertIsNotNone(updated_inputs["Financial"]["PM25_cost_escalation_rate_fraction"])

    def test_off_grid_defaults(self):
        """
        Purpose of this test is to validate off-grid functionality and defaults in the API.
        """
        post_file = os.path.join('reoptjl', 'test', 'posts', 'off_grid_defaults.json')
        post = json.load(open(post_file, 'r'))

        resp = self.api_client.post('/v3/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')

        resp = self.api_client.get(f'/v3/job/{run_uuid}/results')
        r = json.loads(resp.content)
        results = r["outputs"]
    
        # Validate that we got off-grid response fields
        self.assertAlmostEqual(results["Financial"]["offgrid_microgrid_lcoe_dollars_per_kwh"], 0.337, places=-3)
        self.assertAlmostEqual(results["ElectricTariff"]["year_one_bill_before_tax"], 0.0)
        self.assertAlmostEqual(results["ElectricLoad"]["offgrid_load_met_fraction"], 0.99999, places=-2)
        self.assertAlmostEqual(sum(results["ElectricLoad"]["offgrid_load_met_series_kw"]), 8760.0, places=-1)
        self.assertAlmostEqual(results["Financial"]["lifecycle_offgrid_other_annual_costs_after_tax"], 0.0, places=-2)
    
    def test_process_reopt_error(self):
        """
        Purpose of this test is to ensure REopt status 400 is returned using the reoptjl endpoint
        """

        post_file = os.path.join('reoptjl', 'test', 'posts', 'handle_reopt_error.json')
        post = json.load(open(post_file, 'r'))

        resp = self.api_client.post('/v3/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')

        resp = self.api_client.get(f'/v3/job/{run_uuid}/results')
        r = json.loads(resp.content)
        assert('errors' in r["messages"].keys())
        assert('warnings' in r["messages"].keys())
        assert(r['messages']['has_stacktrace']==True)
        assert(resp.status_code==400)

    def test_thermal_in_results(self):
        """
        Purpose of this test is to check that the expected thermal loads, techs, and storage are included in the results
        """

        post_file = os.path.join('reoptjl', 'test', 'posts', 'test_thermal_in_results.json') #includes GhpGhx responses
        post = json.load(open(post_file, 'r'))

        resp = self.api_client.post('/v3/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')
        
        resp = self.api_client.get(f'/v3/job/{run_uuid}/results')
        r = json.loads(resp.content)
        inputs = r["inputs"]
        results = r["outputs"]

        self.assertIn("CoolingLoad", list(inputs.keys()))
        self.assertIn("CoolingLoad", list(results.keys()))
        self.assertIn("CHP", list(results.keys()))
        self.assertIn("thermal_to_dhw_load_series_mmbtu_per_hour", list(results["CHP"].keys()))
        self.assertIn("thermal_to_space_heating_load_series_mmbtu_per_hour", list(results["CHP"].keys()))
        self.assertIn("thermal_to_dhw_load_series_mmbtu_per_hour", list(results["CHP"].keys()))
        self.assertIn("ExistingChiller",list(results.keys()))
        self.assertIn("ExistingBoiler", list(results.keys()))
        self.assertIn("HeatingLoad", list(results.keys()))
        self.assertIn("process_heat_thermal_load_series_mmbtu_per_hour", list(results["HeatingLoad"].keys()))
        self.assertIn("process_heat_boiler_fuel_load_series_mmbtu_per_hour", list(results["HeatingLoad"].keys()))
        self.assertIn("HotThermalStorage", list(results.keys()))
        self.assertIn("storage_to_dhw_load_series_mmbtu_per_hour", list(results["HotThermalStorage"].keys()))
        self.assertIn("storage_to_space_heating_load_series_mmbtu_per_hour", list(results["HotThermalStorage"].keys()))
        self.assertIn("storage_to_dhw_load_series_mmbtu_per_hour", list(results["HotThermalStorage"].keys()))
        self.assertIn("ColdThermalStorage", list(results.keys()))      
        self.assertIn("AbsorptionChiller", list(results.keys()))
        self.assertIn("GHP", list(results.keys()))

    def test_sector_defaults_from_julia(self):
        # Test that the inputs_with_defaults_set_in_julia feature worked for sector defaults, consistent with /sector_defaults
        post_file = os.path.join('reoptjl', 'test', 'posts', 'sector_defaults_post.json')
        post = json.load(open(post_file, 'r'))
        resp = self.api_client.post('/v3/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')

        resp = self.api_client.get(f'/v3/job/{run_uuid}/results')
        r = json.loads(resp.content)
        saved_inputs = r["inputs"]

        # Call to the django view endpoint /sector_defaults which calls the http.jl endpoint
        inputs_defaults = post["Site"]
        inputs_defaults.pop("latitude")
        inputs_defaults.pop("longitude")
        resp = self.api_client.get(f'/v3/sector_defaults', data=inputs_defaults)
        defaults_view_response = json.loads(resp.content)

        for model_name, saved_model_inputs in saved_inputs.items():
            model_category = "Storage" if "Storage" in model_name else model_name
            for input_key, default_input_val in defaults_view_response.get(model_category, {}).items():
                if input_key in post[model_name].keys():
                    # Make sure we didn't overwrite user-input
                    self.assertEqual(saved_model_inputs.get(input_key), post[model_name][input_key])
                else:
                    # Check that default got assigned consistent with /sector_defaults
                    self.assertEqual(saved_model_inputs.get(input_key), default_input_val)

    def test_chp_defaults_from_julia(self):
        # Test that the inputs_with_defaults_set_in_julia feature worked for CHP, consistent with /chp_defaults
        post_file = os.path.join('reoptjl', 'test', 'posts', 'chp_defaults_post.json')
        post = json.load(open(post_file, 'r'))
        # Make average MMBtu/hr thermal steam greater than 7 MMBtu/hr threshold for combustion_turbine to be chosen
        # Default ExistingBoiler efficiency for production_type = steam is 0.75
        post["SpaceHeatingLoad"]["annual_mmbtu"] = 8760 * 8 / 0.75
        post["DomesticHotWaterLoad"]["annual_mmbtu"] = 8760 * 8 / 0.75
        resp = self.api_client.post('/v3/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')

        resp = self.api_client.get(f'/v3/job/{run_uuid}/results')
        r = json.loads(resp.content)

        inputs_chp = r["inputs"]["CHP"]

        avg_fuel_load = (post["SpaceHeatingLoad"]["annual_mmbtu"] + 
                            post["DomesticHotWaterLoad"]["annual_mmbtu"]) / 8760.0
        inputs_chp_defaults = {"hot_water_or_steam": post["ExistingBoiler"]["production_type"],
                            "avg_boiler_fuel_load_mmbtu_per_hour": avg_fuel_load
            }

        # Call to the django view endpoint /chp_defaults which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/chp_defaults', data=inputs_chp_defaults)
        view_response = json.loads(resp.content)

        for key in view_response["default_inputs"].keys():
            if post["CHP"].get(key) is None: # Check that default got assigned consistent with /chp_defaults
                if key == "max_kw":
                    self.assertEqual(inputs_chp[key], view_response["chp_max_size_kw"])
                else:
                    self.assertEqual(inputs_chp[key], view_response["default_inputs"][key])
            else:  # Make sure we didn't overwrite user-input
                self.assertEqual(inputs_chp[key], post["CHP"][key])

    def test_peak_load_outage_times(self):
        """
        Purpose of this test is to test the endpoint /peak_load_outage_times 
        """

        load = [100]*8760
        load[40*24] = 200
        load[50*24-1] = 300
        load[70*24+13] = 300
        load[170*24] = 300
        load[243*24] = 400
        outage_inputs = {"seasonal_peaks": True,
                        "outage_duration": 95,
                        "critical_load": load,
                        "start_not_center_on_peaks": False
        }
        expected_time_steps = [50*24-1-47+1, 70*24+13-47+1, 170*24-47+1, 243*24-47+1]
        resp = self.api_client.post(f'/v3/peak_load_outage_times', data=outage_inputs)
        self.assertHttpOK(resp)
        resp = json.loads(resp.content)
        self.assertEqual(resp["outage_start_time_steps"], expected_time_steps)

        outage_inputs["seasonal_peaks"] = False
        outage_inputs["start_not_center_on_peaks"] = True
        expected_time_steps = [243*24+1]
        resp = self.api_client.post(f'/v3/peak_load_outage_times', data=outage_inputs)
        self.assertHttpOK(resp)
        resp = json.loads(resp.content)
        self.assertEqual(resp["outage_start_time_steps"], expected_time_steps)

    def test_superset_input_fields(self):
        """
        Purpose of this test is to test the API's ability to accept all relevant 
        input fields and send to REopt, ensuring name input consistency with REopt.jl.
        Note: Does not currently test CHP inputs
        """
        post_file = os.path.join('reoptjl', 'test', 'posts', 'all_inputs_test.json')
        post = json.load(open(post_file, 'r'))

        resp = self.api_client.post('/v3/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')

        resp = self.api_client.get(f'/v3/job/{run_uuid}/results')
        r = json.loads(resp.content)
        results = r["outputs"]
        self.assertAlmostEqual(results["Financial"]["npv"], -384244.29, delta=0.01*results["Financial"]["lcc"])
        assert(resp.status_code==200)   
        self.assertIn("ElectricHeater", list(results.keys()))
        self.assertIn("ASHPSpaceHeater", list(results.keys()))
        self.assertIn("ASHPWaterHeater", list(results.keys()))


    def test_steamturbine_defaults_from_julia(self):
        # Test that the inputs_with_defaults_set_in_julia feature worked for SteamTurbine, consistent with /chp_defaults
        post_file = os.path.join('reoptjl', 'test', 'posts', 'steamturbine_defaults_post.json')
        post = json.load(open(post_file, 'r'))

        # Call http.jl /reopt to run SteamTurbine scenario and get results for defaults from julia checking
        resp = self.api_client.post('/v3/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')

        resp = self.api_client.get(f'/v3/job/{run_uuid}/results')
        r = json.loads(resp.content)

        inputs_steamturbine = r["inputs"]["SteamTurbine"]

        avg_fuel_load = (post["SpaceHeatingLoad"]["annual_mmbtu"] + 
                            post["DomesticHotWaterLoad"]["annual_mmbtu"]) / 8760.0
        
        inputs_steamturbine_defaults = {
            "prime_mover": "steam_turbine",
            "avg_boiler_fuel_load_mmbtu_per_hour": avg_fuel_load
        }

        # Call to the django view endpoint /chp_defaults which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/chp_defaults', data=inputs_steamturbine_defaults)
        view_response = json.loads(resp.content)

        for key in view_response["default_inputs"].keys():
            # skip this key because its NaN in REoptInputs but is populated in /chp_defaults response.
            if key != "inlet_steam_temperature_degF":
                if post["SteamTurbine"].get(key) is None: # Check that default got assigned consistent with /chp_defaults
                    self.assertEqual(inputs_steamturbine[key], view_response["default_inputs"][key])
                else:  # Make sure we didn't overwrite user-input
                    self.assertEqual(inputs_steamturbine[key], post["SteamTurbine"][key])

    def test_hybridghp(self):
        post_file = os.path.join('reoptjl', 'test', 'posts', 'hybrid_ghp.json')
        post = json.load(open(post_file, 'r'))

        post['GHP']['ghpghx_inputs'][0]['hybrid_ghx_sizing_method'] = 'Automatic'
        post['GHP']['avoided_capex_by_ghp_present_value'] = 1.0e6
        post['GHP']['ghx_useful_life_years'] = 35

        # Call http.jl /reopt to run SteamTurbine scenario and get results for defaults from julia checking
        resp = self.api_client.post('/v3/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')

        resp = self.api_client.get(f'/v3/job/{run_uuid}/results')
        r = json.loads(resp.content)
        
        # TODO: add number_of_boreholes output to API and calculate ghx_residual_value_present_value here
        self.assertAlmostEqual(r["outputs"]["GHP"]["ghpghx_chosen_outputs"]["number_of_boreholes"], 10, delta=.1)
        total_ghx_ft = r["outputs"]["GHP"]["ghpghx_chosen_outputs"]["number_of_boreholes"] * r["outputs"]["GHP"]["ghpghx_chosen_outputs"]["length_boreholes_ft"]
        ghx_only_capital_cost = total_ghx_ft * r["inputs"]["GHP"]["installed_cost_ghx_per_ft"]
        useful_life = post['GHP']['ghx_useful_life_years']
        fin = r["inputs"]["Financial"]
        analysis_years = fin["analysis_years"]
        discount_rate = (1 - 1* fin["third_party_ownership"])*fin["offtaker_discount_rate_fraction"] + fin["third_party_ownership"]*fin["owner_discount_rate_fraction"]
        ghx_residual_value = ghx_only_capital_cost * (
                (useful_life - analysis_years)/useful_life
            )/((1 + discount_rate)**analysis_years)
        # Note: this value is not independently calculated
        self.assertAlmostEqual(r["outputs"]["GHP"]["ghx_residual_value_present_value"], ghx_residual_value, delta=5)

    def test_centralghp(self):
        post_file = os.path.join('reoptjl', 'test', 'posts', 'central_plant_ghp.json')
        post = json.load(open(post_file, 'r'))

        # Call http.jl /reopt to run the central plant GHP scenario and get results for defaults from julia checking
        resp = self.api_client.post('/v3/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')

        resp = self.api_client.get(f'/v3/job/{run_uuid}/results')
        r = json.loads(resp.content)

        self.assertAlmostEqual(r["outputs"]["Financial"]["lifecycle_capital_costs"], 1046066.8, delta=1000)

    def test_ashp_defaults_update_from_julia(self):
        # Test that the inputs_with_defaults_set_in_julia feature worked for ASHPSpaceHeater
        post_file = os.path.join('reoptjl', 'test', 'posts', 'ashp_defaults_update.json')
        post = json.load(open(post_file, 'r'))
        resp = self.api_client.post('/stable/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')

        resp = self.api_client.get(f'/stable/job/{run_uuid}/results')
        r = json.loads(resp.content)
        
        self.assertEqual(r["inputs"]["ASHPSpaceHeater"]["om_cost_per_ton"], 0.0)
        self.assertEqual(r["inputs"]["ASHPSpaceHeater"]["sizing_factor"], 1.1)

    def test_pv_cost_defaults_update_from_julia(self):
        # Test that the inputs_with_defaults_set_in_julia feature worked for PV
        post_file = os.path.join('reoptjl', 'test', 'posts', 'pv_cost_update.json')
        post = json.load(open(post_file, 'r'))
        resp = self.api_client.post('/stable/job/', format='json', data=post)
        self.assertHttpCreated(resp)
        r = json.loads(resp.content)
        run_uuid = r.get('run_uuid')

        resp = self.api_client.get(f'/stable/job/{run_uuid}/results')
        r = json.loads(resp.content)
        
        self.assertEqual(r["inputs"]["PV"]["size_class"], 2)
        self.assertAlmostEqual(r["inputs"]["PV"]["installed_cost_per_kw"], 2914.6, delta=0.05 * 2914.6)