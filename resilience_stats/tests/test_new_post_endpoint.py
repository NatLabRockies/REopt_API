# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import json
import os
from tastypie.test import ResourceTestCaseMixin
from django.test import TestCase


class OutageSimTests(ResourceTestCaseMixin, TestCase):
    REopt_tol = 1e-2

    def setUp(self):
        super(OutageSimTests, self).setUp()

        # for optimization module
        self.reopt_base_opt = '/v2/job/'
        self.post_opt = os.path.join('resilience_stats', 'tests', 'optPOST.json')
        self.run_uuid = None

        #for simulation module
        self.reopt_base_sim = '/v2/outagesimjob/'


    def get_response_opt(self, data):
        return self.api_client.post(self.reopt_base_opt, format='json', data=data)

    def get_response_sim(self, data_sim):
        return self.api_client.post(self.reopt_base_sim, format='json',
                                    data=data_sim)

    def test_both_modules(self):
        """
        temporary test setup for running an optimizatin problem that precedes the following test for new endpoint for outage simulation module.
        :return:
        """
        data = json.load(open(self.post_opt, 'rb'))
        resp = self.get_response_opt(data)
        self.assertHttpCreated(resp)
        r_opt = json.loads(resp.content)
        run_uuid = r_opt.get('run_uuid')

        assert(run_uuid is not None)
        post_sim = {"run_uuid": run_uuid, "bau": True}
        resp = self.get_response_sim(data_sim=post_sim)
        self.assertHttpCreated(resp)
        r_sim = json.loads(resp.content)
        # print("Response from outagesimjob:", r_sim)
