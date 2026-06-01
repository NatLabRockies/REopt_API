# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import json
import os
from django.test import TestCase
from tastypie.test import ResourceTestCaseMixin


class TestLoadBuilder(ResourceTestCaseMixin, TestCase):

    def setUp(self):
        super(TestLoadBuilder, self).setUp()
        test_path = os.path.join('load_builder', 'tests')
        self.submit_url = '/v2/load_builder/'
        self.test_path = test_path

    def test_load_builder_endpoint(self):

        # try JSON
        post = json.load(open(os.path.join(self.test_path, 'load_table.json'), 'r'))
        r = self.api_client.post(self.submit_url, format='json', data=post)
        json_resp = json.loads(r.content)
        self.assertEqual(list(json_resp.keys())[0], 'critical_loads_kw')

        # try CSV
        post = open(os.path.join(self.test_path, 'load_table.csv'), 'r').read()
        r = self.api_client.post(self.submit_url, data=post)
        csv_resp = json.loads(r.content)
        self.assertEqual(list(csv_resp.keys())[0], 'critical_loads_kw')

        # Check that we get same result
        self.assertEqual(json_resp, csv_resp)