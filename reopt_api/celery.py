# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from __future__ import absolute_import, unicode_literals  # recommended by celery documentation
import os
import logging
from celery import Celery
from celery.signals import after_setup_logger
from keys import *

# set the default Django settings module for the 'celery' program.
try:
    env = os.environ['APP_ENV']

    if env == 'internal_c110p':
        raw_env = 'reopt_api.internal_c110p_settings'
        redis_host = ':' + dev_redis_password + '@localhost'
    elif env == 'development':
        raw_env = 'reopt_api.dev_settings'
        if os.environ.get('K8S_DEPLOY') is None:
            redis_host = ':' + dev_redis_password + '@' + dev_database_host
        else:
            redis_host = ':' + dev_redis_password + '@' + dev_redis_host
    elif env == 'staging':
        raw_env = 'reopt_api.staging_settings'
        if os.environ.get('K8S_DEPLOY') is None:
            redis_host = ':' + staging_redis_password + '@' + staging_database_host
        else:
            redis_host = ':' + staging_redis_password + '@' + staging_redis_host
    elif env == 'production':
        raw_env = 'reopt_api.production_settings'
        if os.environ.get('K8S_DEPLOY') is None:
            redis_host = ':' + production_redis_password + '@' + prod_database_host
        else:
            redis_host = ':' + production_redis_password + '@' + production_redis_host
    else:
        raw_env = 'reopt_api.dev_settings'
        redis_host = os.environ.get('REDIS_HOST', 'localhost')

except KeyError:
    """
    This catch is necessary for running celery from command line when testing/developing locally.
    APP_ENV is defined in config/deploy/[development, production, staging].rb files for servers.
    For testing and local development, APP_ENV *can* be defined in .env file (see README.md),
    which `honcho` or `foreman` loads before running Procfile.
    """
    raw_env = 'reopt_api.dev_settings'
    redis_host = os.environ.get('REDIS_HOST', 'localhost')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', raw_env)

app = Celery('reopt_api')

# # Example of killing celery task:
# app.control.revoke('a879bf13-6689-41bc-bd23-ad6a05920f24', terminate=True)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.broker_url = 'redis://' + redis_host + ':6379/0'

# Create separate queues for each server (naming each queue after the server's
# hostname). Since the worker jobs currently all have to be processes on the
# same server (so the input/output files can be shared across jobs), having
# server-specific queues is a simplistic way to ensure processing remains on a
# single server.
app.conf.task_default_queue = os.environ.get('APP_QUEUE_NAME', 'localhost')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    # file_formatter = logging.Formatter(
    #     '%(asctime)s %(name)-12s %(levelname)-8s %(filename)s::%(funcName)s line %(lineno)s %(message)s')
    console_formatter = logging.Formatter(
        '%(name)-12s %(levelname)-8s %(filename)s::%(funcName)s line %(lineno)s %(message)s')

    # logfile = os.path.join(os.getcwd(), "log", "reopt_api.log")
    #
    # file_handler = logging.FileHandler(filename=logfile, mode='a')
    # file_handler.setFormatter(file_formatter)
    # file_handler.setLevel(logging.INFO)
    # logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
