# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from django.test import TestCase
from tastypie.test import ResourceTestCaseMixin
import json
import uuid
import logging
logging.disable(logging.CRITICAL)


class SummaryResourceTest(ResourceTestCaseMixin, TestCase):

    # mimic user passing in info
    def setUp(self):
        super(SummaryResourceTest, self).setUp()
        self.reopt_base_job_url = '/v1/job/'
        self.summary_url = '/v1/user/{}/summary'
        self.unlink_url = '/v1/user/{}/unlink/{}'
        self.test_user_uuid = '501d1dd9-9779-470b-a631-01c5fbdee570'
        self.test_alt_user_uuid = '701d1dd9-9779-470b-a631-01c5fbdee570'
        self.test_run_uuid = None

    def test_summary_and_unlink(self):
        self.test_run_uuid = self.send_valid_nested_post(self.test_user_uuid)
        summary_response = self.get_summary()
        self.assertTrue(self.test_run_uuid in str(summary_response.content))
        self.unlink_record()
        self.unlink_messages()

    def unlink_record(self):
        unlink_response = self.get_unlink(self.test_user_uuid, self.test_run_uuid)
        self.assertTrue(unlink_response.status_code == 201)
        summary_response = self.get_summary()
        self.assertFalse(self.test_run_uuid in str(summary_response.content))

    def unlink_messages(self):

      bad_uuid = str(uuid.uuid4())
      unlink_response = self.get_unlink(bad_uuid, self.test_run_uuid)
      self.assertTrue("User {} does not exist".format(bad_uuid) in str(unlink_response.content))

      unlink_response = self.get_unlink(self.test_user_uuid, bad_uuid)
      self.assertTrue("Run {} does not exist".format(bad_uuid) in str(unlink_response.content))

      test_alt_run_uuid = self.send_valid_nested_post(self.test_alt_user_uuid)
      self.assertTrue("Run {} is not associated with user {}".format(test_alt_run_uuid, self.test_user_uuid))

    def get_unlink(self,user_uuid, run_uuid):
        return self.api_client.get(self.unlink_url.format(user_uuid, run_uuid))

    def get_summary(self):
        return self.api_client.get(self.summary_url.format(self.test_user_uuid))

    def post_job(self, data):
        return self.api_client.post(self.reopt_base_job_url, format='json', data=data)

    def send_valid_nested_post(self,user_uuid):
        nested_data = {"Scenario": {
                        "Site": {
                            "latitude": -31.9505,
                            "longitude": 115.8605,
                            "ElectricTariff":
                                {"blended_annual_rates_us_dollars_per_kwh": 0.10,
                                 "blended_annual_demand_charges_us_dollars_per_kw": 0},
                            "LoadProfile": {"doe_reference_name": "Hospital",
                                            "annual_kwh": 100},
                            "Wind": {"max_kw": 0},
                            "PV": {"max_kw": 0},
                            "Storage": {"max_kw": 0}
                            }
                        }}
        nested_data['Scenario']['user_uuid'] = user_uuid
        resp = self.post_job(data=nested_data)
        r = json.loads(resp.content)
        return r.get('run_uuid')
