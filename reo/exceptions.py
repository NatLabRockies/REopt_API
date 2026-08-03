# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from reo.models import ErrorModel
import logging
log = logging.getLogger(__name__)
import rollbar
import traceback as tb


class REoptError(Exception):
    """
    Base class for exceptions in reo app.
    """

    def __init__(self, task='', name='', run_uuid='', message='', traceback='', user_uuid=''):
        """

        :param task: task where error occurred, e.g. scenario_setup, reopt, process_results
        :param name: name of error class, e.g. SubprocessTimeout
        :param run_uuid:
        :param user_uuid:
        :param message: message that is sent back to user in messages: errors
        :param traceback: sys.exc_info()[2]
        """
        if message == "Wind Dataset Timed Out":
            msg_with_email = (" Please try again later or email reopt@nlr.gov for support or un-check the wind option "
            "to take wind out of the analysis")
        elif message.startswith("PV Watts could not locate a dataset station"):
            msg_with_email = (" Please increase your PV search radius parameter, or choose an alternate "
            "location with similar solar irradiance and weather trends closer to the continental US. "
            "You can also use a search radius of 0 to return PV Watts results regardless of distance "
            "to the nearest station.")
        elif run_uuid:
            msg_with_email = (" Please visit https://github.com/NatLabRockies/REopt-Analysis-Scripts/discussions for support with "
            "common API usage issues. You can also email reopt@nlr.gov with your run_uuid ({}) for support.".format(run_uuid))
        elif user_uuid:
            msg_with_email = (" Please visit https://github.com/NatLabRockies/REopt-Analysis-Scripts/discussions for support with "
            "common API usage issues. You can also email reopt@nlr.gov with your user_uuid ({}) for support.".format(user_uuid))
        else:
            msg_with_email = (" Please visit https://github.com/NatLabRockies/REopt-Analysis-Scripts/discussions for support with "
            "common API usage issues. You can also email reopt@nlr.gov for support.")
            
        if 'infeasible' not in traceback:
            self.message = message + msg_with_email  # msg_with_email included in messages: error response, but not in error table
        else:
            self.message = message
        self.task = task
        self.run_uuid = run_uuid
        self.user_uuid = user_uuid
        self.traceback = traceback
        self.name = name
        log.error(traceback)

    def save_to_db(self):
        """
        ErrorModel(django.db.models.Model)
            task = models.TextField(blank=True, default='')
            name = models.TextField(blank=True, default='')
            run_uuid = models.TextField(blank=True, default='')
            user_uuid = models.TextField(blank=True, default='')
            message = models.TextField(blank=True, default='')
            traceback = models.TextField(blank=True, default='')
        """
        extra_data = {'task': self.task,
                      'name': self.name,
                      'run_uuid': self.run_uuid,
                      'user_uuid': self.user_uuid,
                      'message': self.message,
                      'traceback': self.traceback,
                      }

        rollbar.report_message(self.name, 'error', extra_data=extra_data)
        try:
        
            em = ErrorModel(task=self.task or '', name=self.name or '', run_uuid=self.run_uuid or '',
                            user_uuid=self.user_uuid or '', message=self.message or '', traceback=self.traceback or '')
            em.save()
        except:
            message = 'Could not save {} for run_uuid {} to database: \n {}'.format(self.__name__, self.run_uuid, self.traceback)
            log.debug(message)


class OptimizationTimeout(REoptError):
    """
    Exception raised when a subprocess times out

    """
    __name__ = 'SubprocessTimeout'

    def __init__(self, task='reopt', run_uuid='', message='', traceback='', user_uuid=''):
        """

        :param task: task where error occurred
        :param run_uuid:
        :param message: message that is sent back to user in messages: errors
        :param traceback: saved to database for debugging
        """
        super(OptimizationTimeout, self).__init__(task, self.__name__, run_uuid, message, traceback, user_uuid=user_uuid)


class NotOptimal(REoptError):
    """
    Exception raised when a subprocess times out

    """
    __name__ = 'NotOptimal'

    def __init__(self, task='reopt', run_uuid='', status='', user_uuid=''):

        msg = "REopt could not find an optimal solution for these inputs."
        if status == 'infeasible':
            msg += " For resilience runs, an 'infeasible' status is likely due to system size constraints that prevent the load from being met during a grid outage. "\
                    + "For off-grid runs, an 'infeasible' status may be due to load operating reserve, PV operating reserve, or minimum load met requirements that are infeasible with the selected technologies and system size constraints."\
                    + "Please adjust these inputs and try again."
        super(NotOptimal, self).__init__(task, self.__name__, run_uuid, message=msg, traceback="status: " + status, user_uuid=user_uuid)


class REoptFailedToStartError(REoptError):
    """
    Exception raised when REopt fails to start (subprocess.CalledProcessError)

    """
    __name__ = 'REoptFailedToStartError'

    def __init__(self, task='reopt', run_uuid='', message='', traceback='', user_uuid=''):
        """

        :param task: task where error occurred
        :param run_uuid:
        :param message: message that is sent back to user in messages: errors
        :param traceback: saved to database for debugging
        """
        super(REoptFailedToStartError, self).__init__(task, self.__name__, run_uuid, message, traceback, user_uuid=user_uuid)


class RequestError(REoptError):
    """
    Exception class for reo.views.results
    """
    __name__ = "RequestError"

    def __init__(self, task='reo.views.results', run_uuid='', message='', traceback='', user_uuid=''):
        """

        :param task: task where error occurred
        :param run_uuid:
        :param message: message that is sent back to user in messages: errors
        :param traceback: saved to database for debugging
        """
        super(RequestError, self).__init__(task, self.__name__, run_uuid, message, traceback, user_uuid=user_uuid)


class UnexpectedError(REoptError):
    """
    REopt catch-all exception class

    Attributes:
        message - explanation of the error
    """

    __name__ = 'UnexpectedError'

    def __init__(self, exc_type, exc_value, exc_traceback, task='', run_uuid='', user_uuid='', portfolio_uuid='', message=None):
        debug_msg = "exc_type: {}; exc_value: {}; exc_traceback: {}".format(exc_type, exc_value, exc_traceback)
        if message is None:
            message = "Unexpected Error."
        super(UnexpectedError, self).__init__(task=task, name=self.__name__, run_uuid=run_uuid, user_uuid=user_uuid, portfolio_uuid=portfolio_uuid,
                                              message=message, traceback=debug_msg)


class WindDownloadError(REoptError):
    """
    REopt catch-all exception class

    Attributes:
        message - explanation of the error
    """

    __name__ = 'WindDownloadError'

    def __init__(self, task='', run_uuid='', user_uuid=''):
        message = "Unable to download wind data"
        super(WindDownloadError, self).__init__(task=task, name=self.__name__, run_uuid=run_uuid, user_uuid=user_uuid,
                                                message=message, traceback='')


class LoadProfileError(REoptError):
    """
    Exception class for errors that occur during LoadProfile class instantiation in reo.scenario
    """

    __name__ = 'LoadProfileError'

    def __init__(self, exc_value=None, exc_traceback=None, task='', run_uuid='', user_uuid='',message=None):
        debug_msg = 'Error in Load Profile'
        if (not exc_value is None) and (not exc_traceback is None):
            debug_msg = "exc_value: {}; exc_traceback: {}".format(exc_value, tb.format_tb(exc_traceback))
        message = message or "Problem parsing load data."
        super(LoadProfileError, self).__init__(task=task, name=self.__name__, run_uuid=run_uuid, user_uuid=user_uuid,
                                               message=message, traceback=debug_msg)


class PVWattsDownloadError(REoptError):
    """
    Catches case where PVWatts does not return data because the location is too far away from an nsrdb station (100 miles) or intl station (200 miles)

    Attributes:
        message - explanation of the error
    """

    __name__ = 'PVWattsDownloadError'

    def __init__(self, task='', run_uuid='', user_uuid='', message='',traceback=''):
        super(PVWattsDownloadError, self).__init__(task=task, name=self.__name__, run_uuid=run_uuid, user_uuid=user_uuid,
                                                message=message, traceback=traceback)

class SaveToDatabase(REoptError):
    """
    Catches case where a model cannot be saved to the database

    Attributes:
        message - explanation of the error
    """

    __name__ = 'SaveToDatabase'

    def __init__(self, exc_type, exc_value, exc_traceback, task='', run_uuid='', user_uuid='', message=None):
        debug_msg = "exc_type: {}; exc_value: {}; exc_traceback: {}".format(exc_type, exc_value, tb.format_tb(exc_traceback))
        if message is None:
            message = "Error saving to database."
        super(SaveToDatabase, self).__init__(task=task, name=self.__name__, run_uuid=run_uuid, user_uuid=user_uuid,
                                              message=message, traceback=debug_msg)

class GHXMaxIterationsError(REoptError):
    """
    Catches the case where GHX sizing hits the maximum number of iterations indicating GHP solution may not have converged

    Attributes:
        message - explanation of the error
    """

    __name__ = 'GHXMaxIterationsError'

    def __init__(self, task='', run_uuid='', user_uuid=''):
        message = "The GHX sizing solution did not converge. This particular scenario may be difficult or impossible for the current REopt model to solve. Try adjusting the 'GHX simulation solver initial guess (ft/ton)' variable."
        super(GHXMaxIterationsError, self).__init__(task=task, name=self.__name__, run_uuid=run_uuid, user_uuid=user_uuid,
                                                message=message, traceback='')
