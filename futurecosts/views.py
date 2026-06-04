# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import uuid
import sys
import traceback as tb
from reo.views import make_error_resp
from django.http import JsonResponse
from reo.exceptions import UnexpectedError
from futurecosts.models import FutureCostsJob


def results(request, run_uuid):
    try:
        uuid.UUID(run_uuid)  # raises ValueError if not valid uuid

    except ValueError as e:
        if e.args[0] == "badly formed hexadecimal UUID string":
            resp = make_error_resp(e.args[0])
            return JsonResponse(resp, status=400)
        else:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err = UnexpectedError(exc_type, exc_value.args[0], tb.format_tb(exc_traceback), task='futurecosts_results',
                                  run_uuid=run_uuid)
            err.save_to_db()
            return JsonResponse({"Error": str(err.args[0])}, status=400)

    try:
        fcjob = FutureCostsJob.objects.get(run_uuid=run_uuid)
        fcjob.update_status()
        resp_dict = fcjob.dict
        resp_dict["messages"] = [
            "GET the detailed results for each future_scenarioX_id at developer.nlr.gov/stable/job/<id>/results."
        ]
        return JsonResponse(resp_dict)

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err = UnexpectedError(exc_type, exc_value.args[0], tb.format_tb(exc_traceback), task='reo.futurecosts.results',
                              run_uuid=run_uuid)
        err.save_to_db()
        resp = make_error_resp(err.message)
        return JsonResponse(resp, status=500)

