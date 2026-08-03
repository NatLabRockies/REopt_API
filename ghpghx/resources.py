# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import json
import uuid
import sys
import traceback
import logging
import copy
import os
import requests
import numpy as np
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.bundle import Bundle
from tastypie.serializers import Serializer
from tastypie.exceptions import ImmediateHttpResponse, HttpResponse
from tastypie.resources import ModelResource
from tastypie.validation import Validation
from django.core.exceptions import ValidationError
from ghpghx.models import GHPGHXInputs, GHPGHXOutputs
from django.forms.models import model_to_dict
from reo.src.pvwatts import PVWatts
log = logging.getLogger(__name__)

api_version = "version 1.0.0"
saveToDb = True

def return400(data: dict, validation_errors: dict):
    data["status"] = (
        'Invalid inputs. No GHPGHX task has been created. See messages for details.'
    )
    data["messages"] = validation_errors
    raise ImmediateHttpResponse(HttpResponse(json.dumps(data), content_type='application/json', status=400))

class UUIDFilter(logging.Filter):

    def __init__(self, uuidstr):
        self.uuidstr = uuidstr

    def filter(self, record):
        record.uuidstr = self.uuidstr
        return True

class GHPGHXJob(ModelResource):

    class Meta:
        resource_name = 'ghpghx'
        allowed_methods = ['post']
        detail_allowed_methods = []
        authorization = ReadOnlyAuthorization()
        serializer = Serializer(formats=['json'])
        always_return_data = True
        validation = Validation()
        object_class = None
        
    def detail_uri_kwargs(self, bundle_or_obj):
        kwargs = {}

        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.id
        else:
            kwargs['pk'] = bundle_or_obj['id']

        return kwargs

    def get_object_list(self, request):
        return [request]

    def obj_get_list(self, bundle, **kwargs):
        return self.get_object_list(bundle.request)

    def obj_create(self, bundle, **kwargs):
        ghp_uuid = str(uuid.uuid4())
        data = dict()
        data["ghp_uuid"] = ghp_uuid

        uuidFilter = UUIDFilter(ghp_uuid)
        log.addFilter(uuidFilter)
        log.info('Beginning run setup')

        # Validate inputs
        try:
            # Instantiate a model class instance, but not yet saved to db
            ghpghxInputsM = GHPGHXInputs(ghp_uuid=ghp_uuid, **bundle.data)
            try:
                # Validate individual model fields
                ghpghxInputsM.clean_fields()
            except ValidationError as ve:
                validation_errors = ve.message_dict
                return400(data, validation_errors)
            # TODO add ghpghxM.clean() for field-to-field validation
            # try:
            #     ghpghxM.clean()
            # except ValidationError as ve:
            #     validation_errors = ve.message_dict
            #     return400(data, validation_errors)
            
            # If **fuel** for heating load is given, convert to thermal
            if ghpghxInputsM.heating_thermal_load_mmbtu_per_hr in [None, []]:
                ghpghxInputsM.heating_thermal_load_mmbtu_per_hr = list(np.array(ghpghxInputsM.heating_fuel_load_mmbtu_per_hr) * \
                                                ghpghxInputsM.existing_boiler_efficiency)
            # Call PVWatts for hourly dry-bulb outdoor air temperature
            if ghpghxInputsM.ambient_temperature_f in [None, []]:
                try:
                    pvwatts_inst = PVWatts(tilt=45, latitude=ghpghxInputsM.latitude, longitude=ghpghxInputsM.longitude)
                    amb_temp_c = pvwatts_inst.response["outputs"]["tamb"]
                    ghpghxInputsM.ambient_temperature_f = list(np.array(amb_temp_c) * 1.8 + 32.0)
                except Exception:
                    return400(data, {"Error": "Error in PVWatts call when getting temperature for GHP model."})
        except ImmediateHttpResponse as e:
            raise e
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            data["status"] = ('Internal Server Error during input validation. No GHPGHX task has been created. '
                              'Please check your POST for bad values.')
            data['inputs'] = bundle.data
            data['messages'] = {}
            data['messages']['error'] = "Unexpected Error."
            log.error("Internal Server error: " + data['messages']['error'])
            raise ImmediateHttpResponse(HttpResponse(json.dumps(data),
                                                     content_type='application/json',
                                                     status=500))  # internal server error

        try:
            # Save the instance of the GHPGHXInputs model to the database
            ghpghxInputsM.save()
        except Exception:
            log.error("Could not create and save ghp_uuid: {}\n Data: {}".format(ghp_uuid, data))
            exc_type, exc_value, exc_traceback = sys.exc_info()
            data["status"] = "Internal Server Error during saving of inputs. Please see messages."
            data['messages'] = "Unexpected Error."
            log.error("Internal Server error: " + data['messages'])
            raise ImmediateHttpResponse(HttpResponse(json.dumps(data),
                                                     content_type='application/json',
                                                     status=500))  # internal server error
        
        data["inputs"] = model_to_dict(ghpghxInputsM)
        # Remove extra inputs used above but not expected in ghpghx_inputs.jl
        data["inputs"].pop("latitude", None)
        data["inputs"].pop("longitude", None)
        data["inputs"].pop("heating_fuel_load_mmbtu_per_hr", None)
        data["inputs"].pop("existing_boiler_efficiency", None)
        data["status"] = 'Solving for GHX Size...'

        try:
            julia_host = os.environ.get('JULIA_HOST', "julia")
            response = requests.post("http://" + julia_host + ":8081/ghpghx/", json=data["inputs"])
            results = response.json()
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            message = "Error running GHPGHX model."
            data["status"] = message
            if 'messages' not in data.keys():
                data['messages'] = {}
            data['messages']['error'] = message
            log.error("Internal Server error: " + message)
            raise ImmediateHttpResponse(HttpResponse(json.dumps(data),
                                                        content_type='application/json',
                                                        status=500))  # internal server error
        
        try:
            #ghpghxOutputsM.objects.filter(ghp_uuid=ghp_uuid).update(**results)
            ghpghxOutputsM = GHPGHXOutputs(ghp_uuid=ghp_uuid, **results)
            ghpghxOutputsM.save()
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            message = "Error saving the results to the database"
            data["status"] = message
            if 'messages' not in data.keys():
                data['messages'] = {}
            data['messages']['error'] = message
            log.error("Internal Server error: " + message)
            raise ImmediateHttpResponse(HttpResponse(json.dumps(data),
                                                        content_type='application/json',
                                                        status=500))  # internal server error

        # Successful if it reaches here
        data["status"] = "Solved"
        raise ImmediateHttpResponse(HttpResponse(json.dumps({'ghp_uuid': ghp_uuid}),
                                                 content_type='application/json', status=201))

