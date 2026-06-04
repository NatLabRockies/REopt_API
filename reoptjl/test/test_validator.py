# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import json
import os
import copy
import uuid
from django.test import TestCase
from reoptjl.validators import InputValidator


class InputValidatorTests(TestCase):

    def setUp(self):
        post_file = os.path.join('reoptjl', 'test', 'posts', 'validator_post.json')
        self.post = json.load(open(post_file, 'r'))

    def test_elec_load_profile_length_validation_and_resampling(self):
        """
        try different lengths of load profiles, where the following are valid:
        - 8760 (hourly)
        - 17520 (30 min)
        - 35040 (15 min)
        also confirm that up/down-sampling is working.
        :return: None
        """
        good_lengths = [8760, 17520, 35040]
        bad_lengths = [8759, 17521]

        for length in bad_lengths + good_lengths:
            post = copy.deepcopy(self.post)
            post["APIMeta"]["run_uuid"] = uuid.uuid4()
            post['ElectricLoad']['loads_kw'] = list(range(length))
            post['ElectricLoad']['critical_loads_kw'] = list(range(length))
            validator = InputValidator(post)
            validator.clean()
            validator.clean_fields()
            validator.cross_clean()

            if length in good_lengths:
                self.assertEqual(validator.is_valid, True)

                if length > 8760:  # check downsampling
                    self.assertEqual(len(validator.models["ElectricLoad"].loads_kw), 8760)
                    self.assertEqual(len(validator.models["ElectricLoad"].critical_loads_kw), 8760)
                    assert("resampled inputs" in validator.messages)

            elif length in bad_lengths:
                self.assertEqual(validator.is_valid, False)
                assert('Invalid length' in validator.validation_errors['ElectricLoad']['loads_kw'])
                assert('Invalid length' in validator.validation_errors['ElectricLoad']['critical_loads_kw'])

        # check upsampling
        for time_steps_per_hour in [2, 4]:
            post = copy.deepcopy(self.post)
            post["APIMeta"]["run_uuid"] = uuid.uuid4()
            post['ElectricLoad']['loads_kw'] = list(range(8760))
            post['ElectricLoad']['critical_loads_kw'] = list(range(8760))
            post['Settings']['time_steps_per_hour'] = time_steps_per_hour
            validator = InputValidator(post)
            validator.clean()
            validator.clean_fields()
            validator.cross_clean()
            self.assertEqual(validator.is_valid, True)
            self.assertEqual(len(validator.models["ElectricLoad"].loads_kw), time_steps_per_hour*8760)
            self.assertEqual(len(validator.models["ElectricLoad"].critical_loads_kw), time_steps_per_hour*8760)

    def test_bad_blended_profile_inputs(self):
        post = copy.deepcopy(self.post)
        del(post["ElectricLoad"]["doe_reference_name"])
        post["ElectricLoad"]["blended_doe_reference_names"] = ["badname", "LargeOffice"]
        post["ElectricLoad"]["blended_doe_reference_percents"] = [1.5]
        validator = InputValidator(post)
        validator.clean_fields()

        assert("'badname' is not a valid choice"
               in validator.validation_errors['ElectricLoad']['blended_doe_reference_names'][0])
        assert("Ensure this value is less than or equal to 1.0" in
               validator.validation_errors['ElectricLoad']['blended_doe_reference_percents'][0])

        post["ElectricLoad"]["blended_doe_reference_names"] = ["MediumOffice", "LargeOffice"]
        post["ElectricLoad"]["blended_doe_reference_percents"] = [0.5]
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()

        assert("The number of blended_doe_reference_names must equal the number of blended_doe_reference_percents" in
               validator.validation_errors['ElectricLoad']['blended_doe_reference_names'][0])
        assert("Sum must = 1.0." in
               validator.validation_errors['ElectricLoad']['blended_doe_reference_percents'][0])

    def test_off_grid_defaults_overrides(self):
        post_file = os.path.join('reoptjl', 'test', 'posts', 'off_grid_validations.json')
        post = json.load(open(post_file, 'r'))
        
        post["APIMeta"]["run_uuid"] = uuid.uuid4()

        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        self.assertEqual(validator.is_valid, True)

        self.assertAlmostEqual(validator.models["Wind"].operating_reserve_required_fraction, 0.5)
        self.assertAlmostEqual(validator.models["PV"].operating_reserve_required_fraction, 0.25)
        self.assertEqual(validator.models["Wind"].installed_cost_per_kw, 5776.0) # set based on size_class (commercial)

        self.assertAlmostEqual(validator.models["ElectricLoad"].operating_reserve_required_fraction, 0.1)
        self.assertAlmostEqual(validator.models["ElectricLoad"].critical_load_fraction, 1.0)
        self.assertAlmostEqual(validator.models["ElectricLoad"].min_load_met_annual_fraction, 0.99999)

        self.assertAlmostEqual(validator.models["Generator"].installed_cost_per_kw, 880)
        self.assertAlmostEqual(validator.models["Generator"].om_cost_per_kw, 10)
        self.assertAlmostEqual(validator.models["Generator"].fuel_avail_gal, 1.0e9)
        self.assertAlmostEqual(validator.models["Generator"].min_turn_down_fraction, 0.15)
        self.assertAlmostEqual(validator.models["Generator"].replacement_year, 10)
        self.assertAlmostEqual(validator.models["Generator"].replace_cost_per_kw, validator.models["Generator"].installed_cost_per_kw)

        ## Test that some defaults can be overriden below

        post["ElectricLoad"]["operating_reserve_required_fraction"] = 0.2
        post["ElectricLoad"]["critical_load_fraction"] = 0.95 # cant override
        post["ElectricLoad"]["min_load_met_annual_fraction"] = 0.95
        
        post["Generator"]["om_cost_per_kw"] = 21
        post["Generator"]["fuel_avail_gal"] = 10000
        post["Generator"]["min_turn_down_fraction"] = 0.14
        post["Generator"]["replacement_year"] = 7
        post["Generator"]["replace_cost_per_kw"] = 200

        post["Wind"]["operating_reserve_required_fraction"] = 0.35
        post["PV"]["operating_reserve_required_fraction"] = 0.35
        

        post["APIMeta"]["run_uuid"] = uuid.uuid4()

        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        self.assertEqual(validator.is_valid, True)

        self.assertAlmostEqual(validator.models["PV"].operating_reserve_required_fraction, 0.35)
        self.assertAlmostEqual(validator.models["Wind"].operating_reserve_required_fraction, 0.35)

        self.assertAlmostEqual(validator.models["ElectricLoad"].operating_reserve_required_fraction, 0.2)
        self.assertAlmostEqual(validator.models["ElectricLoad"].critical_load_fraction, 1.0) # cant override
        self.assertAlmostEqual(validator.models["ElectricLoad"].min_load_met_annual_fraction, 0.95)

        self.assertAlmostEqual(validator.models["Generator"].om_cost_per_kw, 21)
        self.assertAlmostEqual(validator.models["Generator"].fuel_avail_gal, 10000)
        self.assertAlmostEqual(validator.models["Generator"].min_turn_down_fraction, 0.14)
        self.assertAlmostEqual(validator.models["Generator"].replacement_year, 7)
        self.assertAlmostEqual(validator.models["Generator"].replace_cost_per_kw, 200.0)

    def existingboiler_boiler_validation(self):

        """
        Validate clean, cross-clean methods are working as expected
        """
        post_file = os.path.join('reoptjl', 'test', 'posts', 'existing_boiler.json')
        post = json.load(open(post_file, 'r'))

        post["APIMeta"]["run_uuid"] = uuid.uuid4()

        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        self.assertEqual(validator.is_valid, True)

        self.assertAlmostEqual(validator.models["ExistingBoiler"].emissions_factor_lb_CO2_per_mmbtu, 117, places=-1)
        self.assertAlmostEqual(len(validator.models["ExistingBoiler"].fuel_cost_per_mmbtu), 8760)
        self.assertAlmostEqual(sum(validator.models["ExistingBoiler"].fuel_cost_per_mmbtu), 8760*0.5)

        self.assertAlmostEqual(len(validator.models["Boiler"].fuel_cost_per_mmbtu), 8760)
        self.assertAlmostEqual(sum(validator.models["Boiler"].fuel_cost_per_mmbtu), 8760*0.25)
        
        # Ensure Hot Thermal Storage System parameter is loaded from json
        self.assertAlmostEqual(validator.models["HotThermalStorage"].max_gal, 2500.0)

        # Validate 12 month fuel cost vector gets scaled correctly

        post["ExistingBoiler"]["fuel_cost_per_mmbtu"] = [1,2,1,1,1,1,1,1,1,1,1,1]
        post["Boiler"]["fuel_cost_per_mmbtu"] = [0.5,1,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5]

        post["APIMeta"]["run_uuid"] = uuid.uuid4()

        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        self.assertEqual(validator.is_valid, True)

        self.assertAlmostEqual(len(validator.models["ExistingBoiler"].fuel_cost_per_mmbtu), 8760)
        self.assertEqual(sum(validator.models["ExistingBoiler"].fuel_cost_per_mmbtu), 9432.0)
        self.assertAlmostEqual(len(validator.models["Boiler"].fuel_cost_per_mmbtu), 8760)
        self.assertEqual(sum(validator.models["Boiler"].fuel_cost_per_mmbtu), 9432.0*0.5)

    def test_missing_required_keys(self):
        #start with on_grid, and keep all keys
        required_ongrid_object_names = [
            "Site", "ElectricLoad", "ElectricTariff"
        ]
        required_offgrid_object_names = [
            "Site", "ElectricLoad"
        ]
        #prior to removal of keys, test lack or errors of validator with full inputs
        post = copy.deepcopy(self.post)
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        post["Settings"]["off_grid_flag"] = False
        validator = InputValidator(post)
        for key in required_ongrid_object_names:
            assert (key not in validator.validation_errors.keys())
        post = copy.deepcopy(self.post)
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        post["Settings"]["off_grid_flag"] = True
        validator = InputValidator(post)
        for key in required_ongrid_object_names:
            assert (key not in validator.validation_errors.keys())
        #test ongrid removal of all ongrid keys, trigger an error for all required ongrid inputs
        post = copy.deepcopy(self.post)
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        post["Settings"]["off_grid_flag"] = False
        for key in required_ongrid_object_names:
            del post[key]
        validator = InputValidator(post)
        for key in required_ongrid_object_names:
            assert("Missing required inputs." in validator.validation_errors[key])
        #test offgrid removal of all offgrid keys, should trigger an error for required offgrid but not ongrid requirements
        post = copy.deepcopy(self.post)
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        post["Settings"]["off_grid_flag"] = True
        for key in required_ongrid_object_names:
            del post[key]
        validator = InputValidator(post)
        for key in required_ongrid_object_names:
            if key in required_offgrid_object_names:
                assert("Missing required inputs." in validator.validation_errors[key])
            else: 
                assert(key not in validator.validation_errors.keys())

        # check for missing CHP inputs
        post = copy.deepcopy(self.post)
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        post["CHP"].pop("fuel_cost_per_mmbtu")
        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        assert("required inputs" in validator.validation_errors["CHP"].keys())

    def test_multiple_outages_validation(self):
        """
        ensure that validation of multiple outages post works as expected and catches errors
        """
        post_file = os.path.join('reoptjl', 'test', 'posts', 'outage.json')
        outage_post = json.load(open(post_file, 'r'))
        outage_post["APIMeta"] = {"run_uuid": uuid.uuid4()}
        outage_post["Meta"] = {
            "description": "test description",
            "address": "test address"
        }
        validator = InputValidator(outage_post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        self.assertEqual(validator.is_valid, True)

        # test mismatched length
        post = copy.deepcopy(outage_post)
        post["ElectricUtility"]["outage_durations"] = [10,20,30,40]
        post["ElectricUtility"]["outage_probabilities"] = [0.8,0.2]
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        validator = InputValidator(post)
        validator.clean()
        assert("mismatched length" in validator.validation_errors["ElectricUtility"].keys())

        # test missing outage_durations
        post = copy.deepcopy(outage_post)
        post["ElectricUtility"].pop("outage_durations")
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        validator = InputValidator(post)
        validator.clean()
        assert("missing required inputs" in validator.validation_errors["ElectricUtility"].keys())

        # test sum of outage_probabilities != 1
        post = copy.deepcopy(outage_post)
        post["ElectricUtility"]["outage_durations"] = [10,20]
        post["ElectricUtility"]["outage_probabilities"] = [0.5,0.6]
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        validator = InputValidator(post)
        validator.clean()
        assert("outage_probabilities" in validator.validation_errors["ElectricUtility"].keys())

        # test missing outage_probabilities
        post = copy.deepcopy(outage_post)
        post["ElectricUtility"]["outage_durations"] = [10,20]
        post["ElectricUtility"].pop("outage_probabilities")
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        self.assertEqual(validator.models["ElectricUtility"].outage_probabilities, [0.5, 0.5])
        self.assertEqual(validator.is_valid, True)

    def test_pv_tilt_defaults(self):
        post = copy.deepcopy(self.post)
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        del(post["ElectricStorage"])
        del(post["CHP"])
        del(post["PV"]["tilt"])
        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        self.assertEqual(validator.models["PV"].tilt, 20)

        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        post["PV"]["array_type"] = 2
        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        self.assertAlmostEqual(validator.models["PV"].tilt, 0)

    def boiler_validation(self):
        """
        Validate clean, cross-clean methods are working as expected
        """
        post_file = os.path.join('job', 'test', 'posts', 'boiler_test.json')
        post = json.load(open(post_file, 'r'))

        post["APIMeta"]["run_uuid"] = uuid.uuid4()

        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        self.assertEqual(validator.is_valid, True)

        # Update with Boiler test fields
        # self.assertAlmostEqual(validator.models["ExistingBoiler"].emissions_factor_lb_CO2_per_mmbtu, 117, places=-1)
        # self.assertAlmostEqual(len(validator.models["ExistingBoiler"].fuel_cost_per_mmbtu), 8760)
        # self.assertAlmostEqual(sum(validator.models["ExistingBoiler"].fuel_cost_per_mmbtu), 8760*0.5)

    def ashp_validation(self):
        """
        Ensure that bad inputs are caught by clean() for ASHP systems.
        """
        post_file = os.path.join('job', 'test', 'posts', 'all_inputs_test.json')
        post = json.load(open(post_file, 'r'))

        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        post["ASHPSpaceHeater"]["cooling_cf_reference"] = []

        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        assert("mismatched length" in validator.validation_errors["ASHPSpaceHeater"].keys())
        
        post = json.load(open(post_file, 'r'))
        post["APIMeta"]["run_uuid"] = uuid.uuid4()
        post["ASHPWaterHeater"]["min_allowable_ton"] = 1000
        post["ASHPWaterHeater"]["min_allowable_peak_capacity_fraction"] = 0.9

        validator = InputValidator(post)
        validator.clean_fields()
        validator.clean()
        validator.cross_clean()
        assert("bad inputs" in validator.validation_errors["ASHPWaterHeater"].keys())
        