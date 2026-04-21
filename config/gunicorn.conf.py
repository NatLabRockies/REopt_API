import os
import multiprocessing

# Bind to unix socket that nginx will proxy to.
if os.environ.get('TEST') is None:
    if os.environ.get('K8S_DEPLOY') is None:
        bind = 'unix:' + os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'tmp/gunicorn.sock')
    else:
        bind = "0.0.0.0:8000"
else:
    bind = "127.0.0.1:8000"

# Based the number of workers on the number of CPU cores.
if os.environ.get('K8S_DEPLOY') is None:
    workers = multiprocessing.cpu_count()
else:
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
# (defined in reo/models.py), and the nginx timeout (defined in
# config/deploy/templates/nginx/proxy_settings.conf.erb).
#
# This timeout should be greater than the xpress timeout, but less than the
# nginx timeout, to give the app an opportunity to handle timeouts more
# gracefully.
timeout = 435

# Set the appropriate DJANGO_SETTINGS_MODULE environment variable based on the
# current environment.
raw_env = ['DJANGO_SETTINGS_MODULE=reopt_api.settings']
