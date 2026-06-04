# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import os
import sys
import traceback as tb
import uuid
import copy
import csv
import json
import pandas as pd
import requests
import logging
from django.http import JsonResponse
from django.http import HttpResponse
from django.template import  loader
from django.views.decorators.csrf import csrf_exempt
from ghpghx.resources import UUIDFilter
from ghpghx.models import ModelManager, GHPGHXInputs

log = logging.getLogger(__name__)


def make_error_resp(msg):
        resp = dict()
        resp['messages'] = {'error': msg}
        resp['outputs'] = dict()
        resp['status'] = 'error'
        return resp


def health(request):
    return HttpResponse("OK")


def errors(request, page_uuid):

    template= loader.get_template("errors.html")
    return HttpResponse(template.render())


def help(request):

    try:
        # TODO response = SOME FORM GENERATED FROM MODELS.PY?
        # Somehow recreate nested_inputs_definitions from models.py models?
        #response = copy.deepcopy(nested_input_definitions)
        response = {}
        return JsonResponse(response)

    except Exception as e:
        return JsonResponse({"Error": "Unexpected error in help endpoint: {}".format(e.args[0])}, status=500)


def results(request, ghp_uuid):
    try:
        uuid.UUID(ghp_uuid)  # raises ValueError if not valid uuid

    except ValueError as e:
        if e.args[0] == "badly formed hexadecimal UUID string":
            resp = make_error_resp(e.args[0])
            return JsonResponse(resp, status=400)
        else:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            resp = make_error_resp("Error when trying to process ghp_uuid")
            return JsonResponse(resp, status=400)

    try:
        d = ModelManager.make_response(ghp_uuid)  # ModelManager has some internal exception handling

        response = JsonResponse(d)
        return response

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        resp = make_error_resp("Error when trying to make_response")
        return JsonResponse(resp, status=500)

def ground_conductivity(request):
    """
    GET ground thermal conductivity based on the climate zone from the lat/long input
    param: latitude: latitude of the site location
    param: longitude: longitude of the site location
    return: climate_zone: climate zone of the site location
    return: thermal_conductivity [Btu/(hr-ft-degF)]: thermal conductivity of the ground in climate zone
    """
    try:
        latitude = float(request.GET['latitude'])  # need float to convert unicode
        longitude = float(request.GET['longitude'])

        inputs_dict = {"latitude": latitude,
                        "longitude": longitude}

        julia_host = os.environ.get('JULIA_HOST', "julia")
        http_jl_response = requests.get("http://" + julia_host + ":8081/ground_conductivity/", json=inputs_dict)
        
        response = JsonResponse(
            http_jl_response.json()
        )
        return response

    except ValueError as e:
        return JsonResponse({"Error": str(e.args[0])}, status=400)

    except KeyError as e:
        return JsonResponse({"Error. Missing": str(e.args[0])}, status=400)

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        debug_msg = "exc_type: {}; exc_value: {}; exc_traceback: {}".format(exc_type, exc_value.args[0],
                                                                            tb.format_tb(exc_traceback))
        log.debug(debug_msg)
        return JsonResponse({"Error": "Unexpected error in ground_conductivity endpoint. Check log for more."}, status=500)