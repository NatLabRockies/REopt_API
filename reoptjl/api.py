# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import json
import uuid
import sys
import traceback
import logging
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.bundle import Bundle
from tastypie.serializers import Serializer
from tastypie.exceptions import ImmediateHttpResponse, HttpResponse
from tastypie.resources import ModelResource
from tastypie.validation import Validation
from reoptjl.validators import InputValidator
# from reo.src.profiler import Profiler  # TODO use Profiler?
from reoptjl.src.run_jump_model import run_jump_model
from reo.exceptions import UnexpectedError, REoptError
from ghpghx.models import GHPGHXInputs
from django.core.exceptions import ValidationError
from reoptjl.models import APIMeta
import keys
log = logging.getLogger(__name__)
 

def return400(data: dict, validator: InputValidator):
    data["status"] = (
        'Invalid inputs. No optimization task has been created. See messages for details.'
    )
    data["run_uuid"] = ""
    # TODO save BadInputs ?
    data["messages"] = dict()
    data["messages"]["error"] = "Invalid inputs. See input_errors."
    data["messages"]["input_errors"] = validator.validation_errors
    raise ImmediateHttpResponse(HttpResponse(json.dumps(data), content_type='application/json', status=400))


class UUIDFilter(logging.Filter):

    def __init__(self, uuidstr):
        self.uuidstr = uuidstr

    def filter(self, record):
        record.uuidstr = self.uuidstr
        return True


class Job(ModelResource):

    class Meta:
        resource_name = 'job'
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
        run_uuid = str(uuid.uuid4())
        # Attempt to get POSTed api_key assigned to APIMeta.api_key (or try method below for user_uuid)
        api_key = keys.developer_nrel_gov_key #bundle.request.GET.get("api_key", "")
        if 'user_uuid' in bundle.data.keys():

            if type(bundle.data['user_uuid']) == str:
                if len(bundle.data['user_uuid']) == len(run_uuid):
                    user_uuid = bundle.data['user_uuid']
                else:
                    user_uuid = ''
        else:
            user_uuid = None
        
        if 'webtool_uuid' in bundle.data.keys():

            if type(bundle.data['webtool_uuid']) == str:
                if len(bundle.data['webtool_uuid']) == len(run_uuid):
                    webtool_uuid = bundle.data['webtool_uuid']
                else:
                    webtool_uuid = ''
        else:
            webtool_uuid = None
        
        if 'portfolio_uuid' in bundle.data.keys():

            if type(bundle.data['portfolio_uuid']) == str:
                if len(bundle.data['portfolio_uuid']) == len(run_uuid):
                    portfolio_uuid = bundle.data['portfolio_uuid']
                else:
                    portfolio_uuid = ''
        else:
            portfolio_uuid = None
        
        meta = {
            "run_uuid": run_uuid,
            "api_version": 3,
            "status": "Validating..."
        }
        bundle.data.update({"APIMeta": meta})

        if user_uuid is not None:
            bundle.data['APIMeta']['user_uuid'] = user_uuid
        
        if webtool_uuid is not None:
            bundle.data['APIMeta']['webtool_uuid'] = webtool_uuid
        
        if api_key != "":
            bundle.data['APIMeta']['api_key'] = api_key
            
        if portfolio_uuid is not None:
            bundle.data['APIMeta']['portfolio_uuid'] = portfolio_uuid

        log.addFilter(UUIDFilter(run_uuid))

        if bundle.request.META.get('HTTP_X_API_USER_ID', False):
            if bundle.request.META.get('HTTP_X_API_USER_ID', '') == '6f09c972-8414-469b-b3e8-a78398874103':
                bundle.data['APIMeta']['job_type'] = 'REopt Web Tool'
            else:
                bundle.data['APIMeta']['job_type'] = 'developer.nlr.gov'
        else:
            bundle.data['APIMeta']['job_type'] = 'Internal NLR'

        test_case = bundle.request.META.get('HTTP_USER_AGENT') or ''
        if test_case.startswith('check_http/'):
            bundle.data['APIMeta']['job_type'] = 'Monitoring'

        # Validate ghpghx_inputs, if applicable
        ghpghx_inputs_validation_errors = []
        if bundle.data.get("GHP") is not None and \
            bundle.data["GHP"].get("ghpghx_inputs") not in [None, []] and \
            bundle.data["GHP"].get("ghpghx_response_uuids") in [None, []]:
            for ghpghx_inputs in bundle.data["GHP"]["ghpghx_inputs"]:
                ghpghxM = GHPGHXInputs(**ghpghx_inputs)
                try:
                    # Validate individual model fields
                    ghpghxM.clean_fields()
                except ValidationError as ve:
                    ghpghx_inputs_validation_errors += [key + ": " + val[i] + " " for key, val in ve.message_dict.items() for i in range(len(val))]            

        # Validate inputs
        try:
            input_validator = InputValidator(bundle.data, ghpghx_inputs_validation_errors=ghpghx_inputs_validation_errors)
            input_validator.clean_fields()  # step 1 check field values
            if not input_validator.is_valid:
                return400(meta, input_validator)
            input_validator.clean()  # step 2 check requirements that include more than one field (in one model)
            if not input_validator.is_valid:
                return400(meta, input_validator)
            input_validator.cross_clean()  # step 3 check requirements that include more than one model
            if not input_validator.is_valid:
                return400(meta, input_validator)
        except ImmediateHttpResponse as e:
            raise e  # returns the response from return400
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err = UnexpectedError(exc_type, exc_value.args[0], traceback.format_tb(exc_traceback),
                                  task='InputValidator', run_uuid=run_uuid)
            err.save_to_db()
            meta["status"] = ('Internal Server Error during input validation. No optimization task has been created. '
                              'Please check your POST for bad values.')
            meta['messages'] = {}
            meta['messages']['error'] = err.message  # "Unexpected Error."
            log.error("Internal Server error: " + err.message)
            raise ImmediateHttpResponse(HttpResponse(json.dumps(meta),
                                                     content_type='application/json',
                                                     status=500))  # internal server error

        try:
            input_validator.save()
        except Exception:
            log.error("Could not create and save run_uuid: {}\n Data: {}".format(run_uuid, meta))
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err = UnexpectedError(exc_type, exc_value.args[0], traceback.format_tb(exc_traceback),
                                  task='create_and_save',
                                  run_uuid=run_uuid)
            # err.save_to_db()
            meta["status"] = "Internal Server Error during saving of inputs. Please see messages."
            meta['messages'] = err.message  # "Unexpected Error."
            log.error("Internal Server error: " + err.message)
            raise ImmediateHttpResponse(HttpResponse(json.dumps(meta),
                                                     content_type='application/json',
                                                     status=500))  # internal server error

        APIMeta.objects.filter(run_uuid=run_uuid).update(status='Optimizing...')
        try:
            run_jump_model.s(run_uuid).apply_async()
        except Exception as e:
            if isinstance(e, REoptError):
                pass  # handled in each task
            else:  # for every other kind of exception
                exc_type, exc_value, exc_traceback = sys.exc_info()
                err = UnexpectedError(exc_type, exc_value.args[0], traceback.format_tb(exc_traceback), task='api.py',
                                      run_uuid=run_uuid)
                err.save_to_db()
                meta["status"] = 'Internal Server Error. See messages for more.'
                if 'messages' not in meta.keys():
                    meta['messages'] = {}
                meta['messages']['error'] = err.message
                log.error("Internal Server error: " + err.message)
                raise ImmediateHttpResponse(HttpResponse(json.dumps(meta),
                                            content_type='application/json',
                                            status=500))  # internal server error

        raise ImmediateHttpResponse(HttpResponse(json.dumps({'run_uuid': run_uuid}),
                                    content_type='application/json', status=201))


"""
NOTES
1. celery tasks raise exceptions through the .get() method. So, even though we handle exceptions with the
Task.on_failure method, they get raised again! (And again it seems. There are at least two re-raises occurring in
celery.Task).  So for tests, that call the chain synchronously, the intentional Exception that is re-raised through
the chain call causes a test failure.

Another way to solve this problem is to remove FAILURE from PROPAGATE_STATES in line 149 of:
    <where/you/keep/python/packages>/lib/python2.7/site-packages/celery/states.py
But, this may have unintended consequences.

All in all, celery exception handling is very obscure.
"""
