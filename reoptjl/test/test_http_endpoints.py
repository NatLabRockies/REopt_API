
import json
from tastypie.test import ResourceTestCaseMixin
from django.test import TestCase  # have to use unittest.TestCase to get tests to store to database, django.test.TestCase flushes db
import logging
import os
import requests
logging.disable(logging.CRITICAL)

class TestHTTPEndpoints(ResourceTestCaseMixin, TestCase):

    def test_chp_defaults(self):

        inputs = {"hot_water_or_steam": "hot_water",
                "avg_boiler_fuel_load_mmbtu_per_hour": 28.0
        }

        # Direct call of the http.jl endpoint /chp_defaults
        julia_host = os.environ.get('JULIA_HOST', "julia")
        response = requests.get("http://" + julia_host + ":8081/chp_defaults/", json=inputs)
        http_response = response.json()

        # Call to the django view endpoint /chp_defaults which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/chp_defaults', data=inputs)
        view_response = json.loads(resp.content)

        mismatch = []
        for k, v in http_response["default_inputs"].items():
            if v != view_response["default_inputs"][k]:
                mismatch.append(k)
        
        self.assertEqual(mismatch, [])

        # Check the endpoint logic with the expected selection
        self.assertEqual(http_response["prime_mover"], "combustion_turbine")
        self.assertEqual(http_response["size_class"], 2)
        self.assertGreater(http_response["chp_elec_size_heuristic_kw"], 3500.0)

        inputs = {
            "prime_mover": "micro_turbine",
            "avg_electric_load_kw": 885.0247784246575,
            "max_electric_load_kw": 1427.334,
            "is_electric_only": "true"
        }

        # Direct call of the http.jl endpoint /chp_defaults
        julia_host = os.environ.get('JULIA_HOST', "julia")
        response = requests.get("http://" + julia_host + ":8081/chp_defaults/", json=inputs)
        http_response = response.json()

        # Check the endpoint logic with the expected selection
        self.assertEqual(http_response["size_class"], 3)
    
    def test_steamturbine_defaults(self):

        inputs = {
            "prime_mover": "steam_turbine",
            "avg_boiler_fuel_load_mmbtu_per_hour": 28.0
        }

        # Direct call of the http.jl endpoint /chp_defaults
        julia_host = os.environ.get('JULIA_HOST', "julia")
        response = requests.get("http://" + julia_host + ":8081/chp_defaults/", json=inputs)
        http_response = response.json()

        # Call to the django view endpoint /chp_defaults which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/chp_defaults', data=inputs)
        view_response = json.loads(resp.content)

        mismatch = []
        for k, v in http_response["default_inputs"].items():
            if v != view_response["default_inputs"][k]:
                mismatch.append(k)
        
        self.assertEqual(mismatch, [])

        # Check the endpoint logic with the expected selection
        self.assertEqual(http_response["prime_mover"], "steam_turbine")
        self.assertEqual(http_response["size_class"], 2)
        self.assertGreater(http_response["chp_elec_size_heuristic_kw"], 400.0)
        self.assertLess(http_response["chp_elec_size_heuristic_kw"], 1000.0)

    def test_absorption_chiller_defaults(self):

        inputs = {"thermal_consumption_hot_water_or_steam": "hot_water",
                "load_max_tons": 50
        }

        # Direct call of the http.jl endpoint /absorption_chiller_defaults
        julia_host = os.environ.get('JULIA_HOST', "julia")
        response = requests.get("http://" + julia_host + ":8081/absorption_chiller_defaults/", json=inputs)
        http_response = response.json()

        # Call to the django view endpoint /absorption_chiller_defaults which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/absorption_chiller_defaults', data=inputs)
        view_response = json.loads(resp.content)

        mismatch = []
        for k, v in http_response["default_inputs"].items():
            if v != view_response["default_inputs"][k]:
                mismatch.append(k)
        
        self.assertEqual(mismatch, [])

        # Check the endpoint logic with the expected selection
        self.assertEqual(http_response["thermal_consumption_hot_water_or_steam"], "hot_water")
        self.assertEqual(http_response["default_inputs"]["om_cost_per_ton"], 150.0)
        self.assertEqual(http_response["default_inputs"]["installed_cost_per_ton"], 4500.0)
        self.assertEqual(http_response["default_inputs"]["cop_thermal"], 0.74)
        self.assertNotIn("thermal_consumption_hot_water_or_steam", http_response["default_inputs"].keys())
    
    def test_simulated_load(self):

        # Test heating load because REopt.jl separates SpaceHeating and DHW, so had to aggregate for this endpoint
        inputs = {"load_type": "heating",
                "doe_reference_name": "Hospital",
                "latitude": 36.12,
                "longitude": -115.5
        }

        # The /v3/simulated_load endpoint calls the http.jl /simulated_load endpoint
        response = self.api_client.get(f'/v3/simulated_load', data=inputs)
        http_response = json.loads(response.content)

        # Call to the v2 /simulated_load to check for consistency
        resp = self.api_client.get(f'/v2/simulated_load', data=inputs)
        v2_response = json.loads(resp.content)     
        self.assertAlmostEqual(http_response["annual_mmbtu"], v2_response["annual_mmbtu"], delta=1.0)

        # Test blended/hybrid buildings
        inputs["load_type"] = "electric"
        inputs["annual_kwh"] = 1.5E7
        inputs["doe_reference_name[0]"] = "Hospital"
        inputs["doe_reference_name[1]"] = "LargeOffice"
        inputs["percent_share[0]"] = 0.25
        inputs["percent_share[1]"] = 1.0 - inputs["percent_share[0]"]
        
        # The /v3/simulated_load endpoint calls the http.jl /simulated_load endpoint
        response = self.api_client.get(f'/v3/simulated_load', data=inputs)
        http_response = json.loads(response.content)

        # Call to the v2 /simulated_load to check for consistency
        resp = self.api_client.get(f'/v2/simulated_load', data=inputs)
        v2_response = json.loads(resp.content)     
        self.assertAlmostEqual(http_response["annual_kwh"], v2_response["annual_kwh"], delta=1.0)        

        # Test bad inputs
        inputs["invalid_key"] = "invalid_val"
        resp = self.api_client.get(f'/v2/simulated_load', data=inputs)
        v2_response = json.loads(resp.content)   
        assert("Error" in v2_response.keys())

    def test_simulated_load_post(self):

        # Test 1: POST with normalize_and_scale_load_profile_input and load_profile
        load_profile = [100.0] * 8760  # Simple 8760 hourly load profile
        monthly_totals = [450000.0, 420000.0, 480000.0, 510000.0, 550000.0, 600000.0, 
                          620000.0, 610000.0, 570000.0, 520000.0, 470000.0, 440000.0]  # 12 monthly totals in kWh to scale to
        inputs = {
            "normalize_and_scale_load_profile_input": True,
            "load_profile": load_profile,
            "year": 2021,
            "monthly_totals_kwh": monthly_totals
        }
        resp = self.api_client.post(f'/stable/simulated_load', format='json', data=inputs)
        self.assertHttpOK(resp)
        post_response = json.loads(resp.content)
        self.assertAlmostEqual(post_response["annual_kwh"], sum(monthly_totals), delta=10.0)

        # Test 2: POST with doe_reference_name and monthly_totals_kwh, monthly_peaks_kw
        monthly_peaks = [900.0, 850.0, 950.0, 1000.0, 1100.0, 1200.0, 
                         1300.0, 1250.0, 1150.0, 1050.0, 950.0, 900.0]  # 12 monthly peaks in kW (+/- 30%)
        inputs = {
            "doe_reference_name": "Hospital",
            "latitude": 36.12,
            "longitude": -115.5,
            "load_type": "electric",
            "monthly_totals_kwh": monthly_totals,
            "monthly_peaks_kw": monthly_peaks,
            "year": 2021
        }
        resp = self.api_client.post(f'/stable/simulated_load', format='json', data=inputs)
        self.assertHttpOK(resp)
        post_response = json.loads(resp.content)
        self.assertIn("loads_kw", post_response.keys())
        self.assertEqual(len(post_response["loads_kw"]), 8760)
        self.assertIn("annual_kwh", post_response.keys())

        # Test 3: POST with doe_reference_name only (no monthly data and no load_type, defaults to electric)
        #   and check consistency with GET request
        inputs = {
            "doe_reference_name": "LargeOffice",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "annual_kwh": 1000000.0
        }
        resp = self.api_client.post(f'/stable/simulated_load', format='json', data=inputs)
        self.assertHttpOK(resp)
        post_response = json.loads(resp.content)
        self.assertAlmostEqual(post_response["annual_kwh"], 1000000.0, delta=1.0)

        get_resp = self.api_client.get(f'/stable/simulated_load', data=inputs)
        self.assertHttpOK(get_resp)
        get_response = json.loads(get_resp.content)
        self.assertEqual(post_response["loads_kw"][:3], get_response["loads_kw"][:3])

        # Test 4: POST with blended/hybrid buildings using arrays for doe_reference_name and percent_share
        inputs = {
            "doe_reference_name": ["LargeOffice", "FlatLoad"],
            "percent_share": [0.60, 0.40],
            "latitude": 36.12,
            "longitude": -115.5,
            "load_type": "electric",
            "annual_kwh": 1.5e7,
            "year": 2021
        }
        resp = self.api_client.post(f'/stable/simulated_load', format='json', data=inputs)
        self.assertHttpOK(resp)
        post_response = json.loads(resp.content)
        self.assertIn("loads_kw", post_response.keys())
        self.assertEqual(len(post_response["loads_kw"]), 8760)
        self.assertAlmostEqual(post_response["annual_kwh"], 1.5e7, delta=1.0)

        # Test 5: Validation - Missing both normalize_and_scale_load_profile_input and doe_reference_name
        inputs = {
            "latitude": 36.12,
            "longitude": -115.5,
            "year": 2021,
            "monthly_totals_kwh": monthly_totals
        }
        resp = self.api_client.post(f'/stable/simulated_load', format='json', data=inputs)
        self.assertHttpBadRequest(resp)
        post_response = json.loads(resp.content)
        self.assertIn("Error", post_response.keys())
        self.assertIn("Missing either of", post_response["Error"])

        # Test 6: Validation - normalize_and_scale_load_profile_input without year
        inputs = {
            "normalize_and_scale_load_profile_input": True,
            "load_profile": load_profile
        }
        resp = self.api_client.post(f'/stable/simulated_load', format='json', data=inputs)
        self.assertHttpBadRequest(resp)
        post_response = json.loads(resp.content)
        self.assertIn("Error", post_response.keys())
        self.assertIn("year is required", post_response["Error"])

        # Test 7: Validation - doe_reference_name without latitude
        inputs = {
            "doe_reference_name": "Hospital",
            "longitude": -115.5,
            "year": 2021
        }
        resp = self.api_client.post(f'/stable/simulated_load', format='json', data=inputs)
        self.assertHttpBadRequest(resp)
        post_response = json.loads(resp.content)
        self.assertIn("Error", post_response.keys())
        self.assertIn("latitude and longitude are required", post_response["Error"])

        # Test 8: POST with non-8760 load_profile and time_steps_per_hour
        load_profile_15min = [100.0] * 35040  # 8760 * 4 for 15-minute intervals
        inputs = {
            "normalize_and_scale_load_profile_input": True,
            "load_profile": load_profile_15min,
            "monthly_totals_kwh": monthly_totals,
            "year": 2021,
            "time_steps_per_hour": 4
        }
        resp = self.api_client.post(f'/stable/simulated_load', format='json', data=inputs)
        self.assertHttpOK(resp)
        post_response = json.loads(resp.content)
        self.assertAlmostEqual(post_response["annual_kwh"], sum(monthly_totals), delta=10.0)


    def test_avert_emissions_profile_endpoint(self):
        # Call to the django view endpoint dev/avert_emissions_profile which calls the http.jl endpoint
        #case 1: location in CONUS (Seattle, WA)
        inputs = {
            "latitude": 47.606211,
            "longitude": -122.336052,
            "load_year": 2021
        }
        resp = self.api_client.get(f'/v3/avert_emissions_profile', data=inputs)
        self.assertHttpOK(resp)
        view_response = json.loads(resp.content)
        self.assertEqual(view_response["avert_meters_to_region"], 0.0)
        self.assertEqual(view_response["avert_region"], "Northwest")
        self.assertEqual(len(view_response["emissions_factor_series_lb_NOx_per_kwh"]), 8760)
        #case 2: location off shore of NJ (works for AVERT, not Cambium)
        inputs = {
            "latitude": 39.034417, 
            "longitude": -74.759292,
            "load_year": 2021
        }
        resp = self.api_client.get(f'/v3/avert_emissions_profile', data=inputs)
        self.assertHttpOK(resp)
        view_response = json.loads(resp.content)
        self.assertAlmostEqual(view_response["avert_meters_to_region"], 760.62, delta=1.0)
        self.assertEqual(view_response["avert_region"], "Mid-Atlantic")
        self.assertEqual(len(view_response["emissions_factor_series_lb_NOx_per_kwh"]), 8760)
        #case 3: Honolulu, HI (works for AVERT but not Cambium)
        inputs = {
            "latitude": 21.3099, 
            "longitude": -157.8581,
            "load_year": 2021
        }
        resp = self.api_client.get(f'/v3/avert_emissions_profile', data=inputs)
        self.assertHttpOK(resp)
        view_response = json.loads(resp.content)
        self.assertEqual(view_response["avert_meters_to_region"], 0.0)
        self.assertEqual(view_response["avert_region"], "Hawaii (Oahu)")
        self.assertEqual(len(view_response["emissions_factor_series_lb_NOx_per_kwh"]), 8760)
        #case 4: location well outside of US (does not work)
        inputs = {
            "latitude": 0.0,
            "longitude": 0.0,
            "load_year": 2022
        }
        resp = self.api_client.get(f'/v3/avert_emissions_profile', data=inputs)
        self.assertHttpBadRequest(resp)
        view_response = json.loads(resp.content)
        self.assertTrue("error" in view_response)
        
    def test_cambium_profile_endpoint(self):
        # Call to the django view endpoint v3/cambium_profile which calls the http.jl endpoint
        #case 1: location in CONUS (Seattle, WA)
        inputs = {
            "load_year": 2021,
            "scenario": "Mid-case",
            "location_type": "GEA Regions 2023", 
            "latitude": 47.606211, # Seattle 
            "longitude": -122.336052, # Seattle 
            "start_year": 2024,
            "lifetime": 25,
            "metric_col": "lrmer_co2e",
            "grid_level": "enduse"
        }
        resp = self.api_client.get(f'/v3/cambium_profile', data=inputs) 
        self.assertHttpOK(resp)
        view_response = json.loads(resp.content)
        self.assertEqual(view_response["metric_col"], "lrmer_co2e")
        self.assertEqual(view_response["location"], "Northern Grid West") 
        self.assertEqual(len(view_response["data_series"]), 8760)
        #case 2: location off shore of NJ (works for AVERT, not Cambium)
        inputs["latitude"] = 39.034417
        inputs["longitude"] = -74.759292
        resp = self.api_client.get(f'/v3/cambium_profile', data=inputs) 
        self.assertHttpBadRequest(resp)
        view_response = json.loads(resp.content)
        self.assertTrue("error" in view_response)
        #case 3: Honolulu, HI (works for AVERT but not Cambium)
        inputs["latitude"] = 21.3099
        inputs["longitude"] = -157.8581
        resp = self.api_client.get(f'/v3/cambium_profile', data=inputs)
        self.assertHttpBadRequest(resp) 
        view_response = json.loads(resp.content)
        self.assertTrue("error" in view_response)
        #case 4: location well outside of US (does not work)
        inputs["latitude"] = 0.0
        inputs["longitude"] = 0.0
        resp = self.api_client.get(f'/v3/cambium_profile', data=inputs)
        self.assertHttpBadRequest(resp) 
        view_response = json.loads(resp.content)
        self.assertTrue("error" in view_response)

    def test_easiur_endpoint(self):
        # Call to the django view endpoint dev/easiur_costs which calls the http.jl endpoint
        inputs = {
            "latitude": 47.606211,
            "longitude": -122.336052,
            "inflation": 0.025
        }
        resp = self.api_client.get(f'/v3/easiur_costs', data=inputs)
        self.assertHttpOK(resp)
        view_response = json.loads(resp.content)
        for ekey in ["NOx", "SO2", "PM25"]:
            for key_format in ["{}_grid_cost_per_tonne", "{}_onsite_fuelburn_cost_per_tonne", "{}_cost_escalation_rate_fraction"]:
                self.assertTrue(type(view_response[key_format.format(ekey)]) == float)
        inputs = {
            "latitude": 47.606211,
            "longitude": 122.336052,
            "inflation": 0.025
        }
        resp = self.api_client.get(f'/v3/easiur_costs', data=inputs)
        self.assertHttpBadRequest(resp)
        view_response = json.loads(resp.content)
        self.assertTrue("error" in view_response)
    
    def test_sector_defaults_endpoint(self):
        # Call to the django view endpoint dev/sector_defaults which calls the http.jl endpoint
        inputs = {
            "sector": "federal",
            "federal_procurement_type": "fedowned_dirpurch",
            "federal_sector_state": "CA"
        }
        resp = self.api_client.get(f'/v3/sector_defaults', data=inputs)
        self.assertHttpOK(resp)
        view_response = json.loads(resp.content)
        for tech in ["GHP", "Wind", "PV", "CHP"]:
            self.assertTrue(view_response.get(tech) is not None)
            for key in ["macrs_option_years", "macrs_bonus_fraction", "federal_itc_fraction"]:
                self.assertTrue(view_response[tech].get(key) is not None)
        self.assertTrue(view_response.get("SteamTurbine") is not None)
        for key in ["macrs_option_years", "macrs_bonus_fraction"]:
            self.assertTrue(view_response["SteamTurbine"].get(key) is not None)
        self.assertTrue(view_response.get("Storage") is not None)
        for key in ["macrs_option_years", "macrs_bonus_fraction", "total_itc_fraction"]:
            self.assertTrue(view_response["Storage"].get(key) is not None)
        self.assertTrue(view_response.get("Financial") is not None)
        for key in ["elec_cost_escalation_rate_fraction", "existing_boiler_fuel_cost_escalation_rate_fraction", "boiler_fuel_cost_escalation_rate_fraction", "chp_fuel_cost_escalation_rate_fraction", "generator_fuel_cost_escalation_rate_fraction"]:
            self.assertTrue(view_response["Financial"].get(key) is not None)
        inputs = {
            "sector": "badsector",
            "federal_procurement_type": "fedowned_dirpurch",
            "federal_sector_state": "CA"
        }
        resp = self.api_client.get(f'/v3/sector_defaults', data=inputs)
        self.assertHttpBadRequest(resp)
        view_response = json.loads(resp.content)
        self.assertTrue("error" in view_response)

    def test_ghp_endpoints(self):
        # Test /ghp_efficiency_thermal_factors
        inputs_dict = {"latitude": 37.78,
                        "longitude": -122.45,
                        "doe_reference_name": "MediumOffice"}

        # Call to the django view endpoint /ghp_efficiency_thermal_factors which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/ghp_efficiency_thermal_factors', data=inputs_dict)
        view_response = json.loads(resp.content)

        self.assertEqual(view_response["cooling_efficiency_thermal_factor"], 0.43)
        self.assertEqual(view_response["space_heating_efficiency_thermal_factor"], 0.46)

        # Test /ghpghx/ground_conductivity
        inputs_dict = {"latitude": 37.78,
                        "longitude": -122.45}

        # Call to the django view endpoint /ghpghx/ground_conductivity which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/ghpghx/ground_conductivity', data=inputs_dict)
        view_response = json.loads(resp.content)

        self.assertEqual(view_response["thermal_conductivity"], 1.117)

    def test_default_existing_chiller_cop(self):
        # Test 1: full dictionary
        inputs_dict = {
            "existing_chiller_max_thermal_factor_on_peak_load":1.25,
            "max_load_kw": 50,
            "max_load_ton":10
        }

        # Call to the django view endpoint /get_existing_chiller_default_cop which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/get_existing_chiller_default_cop', data=inputs_dict)
        view_response = json.loads(resp.content)

        self.assertEqual(view_response["existing_chiller_cop"], 4.4)

        # Test 2: empty dictionary, which should return unknown value
        inputs_dict = {}

        # Call to the django view endpoint /get_existing_chiller_default_cop which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/get_existing_chiller_default_cop', data=inputs_dict)
        view_response = json.loads(resp.content)

        self.assertEqual(view_response["existing_chiller_cop"], 4.545)

        # Test 3: Check that "existing_chiller_max_thermal_factor_on_peak_load" can influence the COP; accept max_load_ton empty string
        inputs_dict = {
            "existing_chiller_max_thermal_factor_on_peak_load":1000,
            "max_load_kw": 5,
            "max_load_ton":""
        }

        # Call to the django view endpoint /get_existing_chiller_default_cop which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/get_existing_chiller_default_cop', data=inputs_dict)
        view_response = json.loads(resp.content)

        self.assertEqual(view_response["existing_chiller_cop"], 4.69)

        # Test 4: max_load_ton empty string 
        inputs_dict = {
            "max_load_ton":90,
            "max_load_kw":""
        }

        # Call to the django view endpoint /get_existing_chiller_default_cop which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/get_existing_chiller_default_cop', data=inputs_dict)
        view_response = json.loads(resp.content)

        self.assertEqual(view_response["existing_chiller_cop"], 4.69)

        #Test 5: max_load_kw only, small value yields low COP
        inputs_dict = {
            "max_load_kw":1
        }

        # Call to the django view endpoint /get_existing_chiller_default_cop which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/get_existing_chiller_default_cop', data=inputs_dict)
        view_response = json.loads(resp.content)

        self.assertEqual(view_response["existing_chiller_cop"], 4.4)

    def test_get_ashp_defaults(self):
        inputs_dict = {
            "load_served": "SpaceHeating",
            "force_into_system": "true"
        }

        # Call to the django view endpoint /get_existing_chiller_default_cop which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/get_ashp_defaults', data=inputs_dict)
        view_response = json.loads(resp.content)

        self.assertEqual(view_response["installed_cost_per_ton"], 2250)
        self.assertEqual(view_response["om_cost_per_ton"], 0.0)
        self.assertEqual(view_response["sizing_factor"], 1.1)

        inputs_dict = {
            "load_served": "DomesticHotWater",
            "force_into_system": "false"
        }

        # Call to the django view endpoint /get_existing_chiller_default_cop which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/get_ashp_defaults', data=inputs_dict)
        view_response = json.loads(resp.content)

        self.assertNotIn("cooling_cf_reference", view_response.keys())
        self.assertEqual(view_response["sizing_factor"], 1.0)

    def test_pv_cost_defaults(self):
        inputs_dict = {
            "electric_load_annual_kwh": 2000000.0,
            "array_type": 1,
            "site_roof_squarefeet": 50000
        }

        # Call to the django view endpoint /get_existing_chiller_default_cop which calls the http.jl endpoint
        resp = self.api_client.get(f'/v3/pv_cost_defaults', data=inputs_dict)
        view_response = json.loads(resp.content)

        self.assertEqual(view_response["size_class"], 3)   


