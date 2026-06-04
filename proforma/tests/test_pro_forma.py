# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import tzlocal
import json
import datetime
from django.test import TestCase
from tastypie.test import ResourceTestCaseMixin


def now():
    return tzlocal.get_localzone().localize(datetime.datetime.now())


class CashFlowTest(ResourceTestCaseMixin, TestCase):
    """
    These tests just ensure that input cells in Proforma are filled in with the appropriate values.
    Unfortunately, we cannot automatically validate calculated values in the spreadsheet. So, the only way to truely
    validate the Proforma is to visually compare the Proforma LCC's and NPV against the API's results.

    200415 nlaws: removing the tests for input cells vs. database. No reason to maintain these tests now that the
    proforma rows are created dynamically in the proforma_generator. As mentioned above, the only way to test the
    proforma is visually comparing the NPV, LCC's, etc. between the API response and the Excel workbook.
    """

    REopt_tol = 5e-5

    def setUp(self):
        super(CashFlowTest, self).setUp()
        self.example_reopt_request_data = json.loads(open('proforma/tests/test_data.json').read())
        self.submit_url = '/v1/job/'
        self.results_url = '/v1/job/<run_uuid>/results/'
        self.proforma_url = '/v1/job/<run_uuid>/proforma/'

    def get_response(self, data):
        initial_post = self.api_client.post(self.submit_url, format='json', data=data)
        uuid = json.loads(initial_post.content)['run_uuid']
        response = json.loads(self.api_client.get(self.results_url.replace('<run_uuid>', str(uuid))).content)
        return response

    def test_bad_run_uuid(self):
        run_uuid = "5"
        response = json.loads(self.api_client.get(self.results_url.replace('<run_uuid>', str(run_uuid))).content)
        # status = response['outputs']['Scenario']['status']
        self.assertDictEqual(response,
                             {u'outputs': {u'Scenario': {u'status': u'error'}},
                              u'messages': {u'error': u'badly formed hexadecimal UUID string'}})