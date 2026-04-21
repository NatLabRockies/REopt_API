# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NREL/REopt_API/blob/master/LICENSE.
import requests
import json
import keys_env
import logging
from reo.exceptions import PVWattsDownloadError
log = logging.getLogger(__name__)


def check_pvwatts_response_data(resp):
    """
    If we can load the response data then return it,
    else raise an exception
    :param resp: requests.get result
    :return: dict of resp.text
    """
    try:
        data = json.loads(resp.text)
    except:
        message = ("Error parsing PVWatts response. "
                   "Status code: {}. Text: {}".format(resp.status_code, resp.text))
        raise_pvwatts_exception(message)
    else:
        return data


def raise_pvwatts_exception(message):
    """
    Raise PVWattsDownloadError
    :param message: str
    :return: None
    """
    log.error("pvwatts.py raising error: " + message)
    pvwatts_error = PVWattsDownloadError(task="pvwatts.py", message=message)
    raise pvwatts_error


class PVWatts:

    def __init__(self,
                 url_base="https://developer.nrel.gov/api/pvwatts/v6.json",
                 key=keys_env.developer_nrel_gov_key,
                 azimuth=180,
                 system_capacity=1,
                 losses=0.14,
                 array_type=0,
                 module_type=0,
                 timeframe='hourly',
                 gcr=0.4,
                 dc_ac_ratio=1.2,
                 inv_eff=0.96,
                 radius=100,
                 dataset="nsrdb",
                 latitude=None,
                 longitude=None,
                 tilt=None,
                 time_steps_per_hour=1,
                 offline=False,
                 verify=True,
                 **kwargs):
        """
        WARNING: the __init__ method calls PVWatts API
        :param url_base: str
        :param key: str
        :param azimuth: float
        :param system_capacity: float
        :param losses: float
        :param array_type: int
        :param module_type: int
        :param timeframe: str
        :param gcr: float
        :param dc_ac_ratio: float
        :param inv_eff: float
        :param radius: float
        :param dataset: str
        :param latitude: float
        :param longitude: float
        :param tilt: float
        :param time_steps_per_hour: int
        :param offline: bool
        :param verify: bool
        :param kwargs: dict
        """
        self.url_base = url_base
        self.key = key
        self.azimuth = azimuth
        self.system_capacity = system_capacity
        self.losses = losses
        self.array_type = array_type
        self.module_type = module_type
        self.timeframe = timeframe
        self.gcr = gcr
        self.dc_ac_ratio = dc_ac_ratio
        self.inv_eff = inv_eff
        self.radius = radius
        self.dataset = dataset
        self.latitude = latitude
        self.longitude = longitude
        self.tilt = tilt
        self.time_steps_per_hour = time_steps_per_hour
        self.offline = offline  # used for testing
        self.verify = verify  # used for testing
        self.response = None
        self.response = self.data  # store response so don't hit API multiple times

    @property
    def url(self):
        url = self.url_base + "?api_key=" + self.key + "&azimuth=" + str(self.azimuth) + \
              "&system_capacity=" + str(self.system_capacity) + "&losses=" + str(self.losses*100) + \
              "&array_type=" + str(self.array_type) + "&module_type=" + str(self.module_type) + \
              "&timeframe=" + self.timeframe + "&gcr=" + str(self.gcr) +  "&dc_ac_ratio=" + str(self.dc_ac_ratio) + \
              "&inv_eff=" + str(self.inv_eff*100) + "&radius=" + str(int(self.radius)) + "&dataset=" + self.dataset + \
              "&lat=" + str(self.latitude) + "&lon=" + str(self.longitude) + "&tilt=" + str(self.tilt)
        return url

    @property
    def data(self):
        if self.response is None:
            # Check if point is beyond the bounds of the NRSDB dataset, if so use the international dataset and double the radius
            if self.longitude < -179.5 or self.longitude > -21.0 or self.latitude < -21.5 or self.latitude > 60.0: 
                if self.longitude < 81.5 or self.longitude > 179.5 or self.latitude < -43.8 or self.latitude > 60.0 :
                    if self.longitude < 67.0 or self.longitude > 81.5 or self.latitude < -43.8 or self.latitude > 38.0: 
                        self.dataset = 'intl'
                        self.radius = self.radius *2
            resp = requests.get(self.url, verify=self.verify)
            log.info("PVWatts API query successful.")
            data = check_pvwatts_response_data(resp)
            self.response = data
        return self.response

    @property
    def pv_prod_factor(self):

        if not self.offline:

            outputs = self.response['outputs']
            ac_hourly = outputs.get('ac')

            if ac_hourly is None:
                ac_hourly = [0] * 8760

            dc_nameplate = self.system_capacity * 1000  # W
            prod_factor = []

            # subhourly (i.e 15 minute data)
            if self.time_steps_per_hour >= 1:
                timesteps = []
                timesteps_base = range(0, 8760)
                for ts_b in timesteps_base:
                    for step in range(0, self.time_steps_per_hour):
                       timesteps.append(ts_b)

            # downscaled run (i.e 288 steps per year)
            else:
                timesteps = range(0, 8760, int(1 / self.time_steps_per_hour))

            for hour in timesteps:
                # degradation (levelization factor) applied in mosel model
                prod_factor.append(round(ac_hourly[hour]/ dc_nameplate, 4))

        else:
            prod_factor_original = list()
            import os
            with open(os.path.join('reo', 'tests', 'offline_pv_prod_factor.txt'), 'r') as f:
                for line in f:
                    prod_factor_original.append(float(line.strip('\n')))

            # offline_pv_prod_factor.txt has 8760 rows, thus modifying prod_factor list
            # to have 8760 * time_steps_per_hour values
            prod_factor = [val for val in prod_factor_original for _ in range(self.time_steps_per_hour)]

        return prod_factor
