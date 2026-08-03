# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NREL/REopt_API/blob/master/LICENSE.
import time
import h5pyd
from pyproj import Proj
import numpy as np
import pandas as pd
import os
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import json

from keys_env import developer_nrel_gov_key
import logging
log = logging.getLogger(__name__)
"""
References: 
- https://www.nrel.gov/grid/wind-toolkit.html
- https://github.com/NREL/hsds-examples/

Requires a configuration file at ~/.hscfg with contents like so:

# HDFCloud configuration file
-hs_endpoint = https://developer.nrel.gov/api/hsds/ +v
-hs_username = None 
-hs_password = None 
-hs_api_key = <YOUR-API-KEY>  # from developer.nrel.gov


The h5pyd Files is indexed on [t, y, x], where:
    t is the integer hours since midnight on January 1st, 2007 up to 61368 for December 31st, 2013 (7 years of data) <- check this
    y, x are modified lambert conic coordinates
    
We use t values for 2012, since it is the closest year to the AMY data from AWS True Power, where:
    January 1st, 2012, 00:00:00 = 43824
    December 31st, 2012, 23:00:00 = 52608
However, since 2012 was a leap year, we only take the values through December 30th to get 8,760 values (52,584)
"""

hub_height_strings = {  # unused values included for potential future use
    10: "_10m",  # residential? - yes it is currently being used for residential
    40: "_40m",  # commercial
    60: "_60m",  # medium
    80: "_80m",  # large
    100: "_100m",
    120: "_120m",
    140: "_140m",
    160: "_160m",
    200: "_200m",
}
frequency_map = {  # time_steps_per_hour to pandas sampling frequency string
    2: '30T',
    3: '20T',
    4: '15T',
}

WTK_ORIGIN = (19.624062, -123.30661)
WTK_SHAPE = (1602, 2976)

def get_conic_coords(lat, lng):
    """
    Convert latitude, longitude into integer values for wind tool kit database.
    Modified from "indicesForCoord" in https://github.com/NREL/hsds-examples/blob/master/notebooks/01_introduction.ipynb
    Questions? Perr-Sauer, Jordan <Jordan.Perr-Sauer@nrel.gov>
    :param db_conn: h5pyd.File, database connection
    :param latitude:
    :param longitude:
    :return: (y, x) values to index into db_conn
    """
    #dset = h5pyd.File("/nrel/wtk-us.h5", 'r')['coordinates']
    projstring = """+proj=lcc +lat_1=30 +lat_2=60 
                    +lat_0=38.47240422490422 +lon_0=-96.0 
                    +x_0=0 +y_0=0 +ellps=sphere 
                    +units=m +no_defs """
    projectLcc = Proj(projstring)
    origin_ll = reversed(WTK_ORIGIN)  # origin_ll = reversed(dset[0][0])  to grab origin directly from database
    origin = projectLcc(*origin_ll)
    point = projectLcc(lng, lat)
    delta = np.subtract(point, origin)
    x,y = [int(round(x / 2000)) for x in delta]
    y_max, x_max = WTK_SHAPE # dset.shape to grab shape directly  from database
    if (x<0) or (y<0) or (x>=x_max) or (y>=y_max):
        raise ValueError("Latitude/Longitude is outside of wind resource dataset bounds.")
    return y,x


def get_data(url, filename):
    """
    Parameters
    ---------
    url: string
        The API endpoint to return data from
    filename: string
        The filename where data should be written
    """
    s = requests.Session()
    n_max_tries = 5
    retries = Retry(total=n_max_tries,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])

    s.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        r = s.get(url)
    
        if r and r.status_code != requests.codes.ok:
            log.error("Wind Toolkit returned invalid data, HTTP " + str(r.status_code))
            raise ValueError('Wind Toolkit returned invalid data, HTTP ' + str(r.status_code))
        elif r and r.status_code == requests.codes.ok:
            localfile = open(filename, mode='w+')
            localfile.write(r.text)
        if os.path.isfile(filename):
            return True
    
    except:
        log.error("Wind data download timed out " + str(n_max_tries) + "times")
        raise ValueError('Wind Dataset Timed Out')


def get_wind_resource_developer_api(filename, year, latitude, longitude, hub_height_meters):

    url = 'https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-srw-download?year={year}&lat={lat}&lon={lon}&hubheight={hubheight}&api_key={api_key}'.format(
        year=year, lat=latitude, lon=longitude, hubheight=hub_height_meters, api_key=developer_nrel_gov_key)

    success = get_data(url, filename=filename)
    return success
