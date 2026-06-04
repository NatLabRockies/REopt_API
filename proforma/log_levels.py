# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
import logging
import inspect


# logging utility
def log(level, message):
    func = inspect.currentframe().f_back.f_code
    if level == "DEBUG":
        logging.debug("%s: %s in %s" % (
            message,
            func.co_name,
            func.co_filename
        ))
    elif level == "INFO":
        logging.info("%s: %s in %s" % (
            message,
            func.co_name,
            func.co_filename
        ))
    elif level == "WARNING":
        logging.warning("%s: %s in %s" % (
            message,
            func.co_name,
            func.co_filename
        ))
    elif level == "ERROR":
        logging.error("%s: %s in %s" % (
            message,
            func.co_name,
            func.co_filename
        ))
    elif level == "CRITICAL":
        logging.critical("%s: %s in %s" % (
            message,
            func.co_name,
            func.co_filename
        ))
