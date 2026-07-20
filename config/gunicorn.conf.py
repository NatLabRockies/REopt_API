import os
import multiprocessing

if os.environ.get('TEST') is None:
    bind = "0.0.0.0:8000"
else:
    bind = "127.0.0.1:8000"

# Based the number of workers on the number of CPU cores.
workers = 4

# Note that the app currently has threading issues, so we explicitly want a
# non-thread worker process model.
worker_class = "sync"
threads = 1

# Log access log details to stdout.
accesslog = '-'

# Increase timeout for longer response times.
#
# This value should be be kept in sync with the xpress/mosel run timeout
# (defined in reo/models.py).
#
# This timeout should be greater than the xpress timeout to give the app an
# opportunity to handle timeouts more gracefully.
timeout = 435

# Set the appropriate DJANGO_SETTINGS_MODULE environment variable based on the
# current environment.
raw_env = ['DJANGO_SETTINGS_MODULE=reopt_api.settings']
