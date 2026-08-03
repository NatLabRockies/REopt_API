# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import sys
import traceback
import os
import time
import requests
from celery import shared_task, Task
from reo.exceptions import REoptError, OptimizationTimeout, UnexpectedError, NotOptimal, REoptFailedToStartError
from reoptjl.models import APIMeta, Message, get_input_dict_from_run_uuid
from reo.src.profiler import Profiler
from reoptjl.src.process_results import process_results, update_inputs_in_database
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


class RunJumpModelTask(Task):
    """
    Used to define custom Error handling for celery task
    """
    name = 'run_jump_model'
    max_retries = 0

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        log a bunch of stuff for debugging
        save message: error and outputs: APIMeta: status
        :param exc: The exception raised by the task.
        :param task_id: Unique id of the failed task. (not the run_uuid)
        :param args: Original arguments for the task that failed.
        :param kwargs: Original keyword arguments for the task that failed.
        :param einfo: ExceptionInfo instance, containing the traceback.
        :return: None, The return value of this handler is ignored.
        """
        if isinstance(exc, REoptError):
            exc.save_to_db()
            msg = exc.message
            meta = APIMeta.objects.get(run_uuid=exc.run_uuid)
            meta.status = "An error occurred. See messages for more."
            meta.save(update_fields=["status"])
            Message.create(meta=meta, message_type="error", message=msg).save()

        # TODO is it possible for non-REoptErrors to get here? if so what do we do?

        self.request.chain = None  # stop the chain
        self.request.callback = None
        self.request.chord = None  # this seems to stop the infinite chord_unlock call


@shared_task(base=RunJumpModelTask)
def run_jump_model(run_uuid):
    profiler = Profiler()  # TODO? are we still using the Profile?
    time_dict = dict()
    name = 'run_jump_model'
    data = get_input_dict_from_run_uuid(run_uuid)
    user_uuid = data.get('user_uuid')
    
    data.pop('user_uuid',None) # Remove user uuid from inputs dict to avoid downstream errors

    # can uncomment for debugging
    # import json
    # json.dump(data, open("debug_inputs.json", "w"))

    logger.info("Running JuMP model ...")
    try:
        t_start = time.time()
        julia_host = os.environ.get('JULIA_HOST', "julia")
        response = requests.post("http://" + julia_host + ":8081/reopt/", json=data)
        response_json = response.json()
        if response.status_code == 500:
            raise REoptFailedToStartError(task=name, message=response_json["error"], run_uuid=run_uuid, user_uuid=user_uuid)
        results = response_json["results"]
        reopt_version = response_json["reopt_version"]
        if results["status"].strip().lower() != "error":
            inputs_with_defaults_set_in_julia = response_json["inputs_with_defaults_set_in_julia"]
        time_dict["pyjulia_run_reopt_seconds"] = time.time() - t_start
        results.update(time_dict)

    except Exception as e:
        if isinstance(e, REoptFailedToStartError):
            raise e

        if isinstance(e, requests.exceptions.ConnectionError):  # Julia server down
            raise REoptFailedToStartError(task=name, message="Julia server is down.", run_uuid=run_uuid, user_uuid=user_uuid)

        if "DimensionMismatch" in e.args[0]:  # JuMP may mishandle a timeout when no feasible solution is returned
            msg = "Optimization exceeded timeout: {} seconds.".format(data["Settings"]["timeout_seconds"])
            logger.info(msg)
            raise OptimizationTimeout(task=name, message=msg, run_uuid=run_uuid, user_uuid=user_uuid)

        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error("REopt.jl raised an unexpected error: UUID: " + str(run_uuid))
        raise UnexpectedError(exc_type, exc_value, traceback.format_tb(exc_traceback), task=name, run_uuid=run_uuid,
                              user_uuid=user_uuid)
    else:
        status = results["status"]
        logger.info("REopt run completed with status {}".format(status))

        if status.strip().lower() == 'timed-out':
            msg = "Optimization exceeded timeout: {} seconds.".format(data["Settings"]["timeout_seconds"])
            logger.info(msg)
            raise OptimizationTimeout(task=name, message=msg, run_uuid=run_uuid, user_uuid=user_uuid)
        elif status.strip().lower() == 'error':
            msg = "Optimization did not complete due to an error."
            logger.info(msg)
        elif status.strip().lower() != 'optimal':
            logger.error("REopt status not optimal. Raising NotOptimal Exception.")
            raise NotOptimal(task=name, run_uuid=run_uuid, status=status.strip(), user_uuid=user_uuid)

    profiler.profileEnd()
    # TODO save profile times
    APIMeta.objects.filter(run_uuid=run_uuid).update(reopt_version=reopt_version)
    if status.strip().lower() != 'error':
        update_inputs_in_database(inputs_with_defaults_set_in_julia, run_uuid)
    process_results(results, run_uuid)
    return True
