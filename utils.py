import time

from logging import getLogger, StreamHandler, Formatter, getLoggerClass, DEBUG
import logging

class Timer():
    """
    Simple class to measure time of execution
    """

    def __enter__(self):
        self.start_time = time.clock()
        return self

    def __exit__(self, type, value, traceback):
        self.end_time = time.clock()
#        raise traceback

    def miliseconds(self):
        return int((self.end_time - self.start_time) * 1000)


def init_logging(app, debug = False):

    loggers = [app.logger, getLogger('sqlalchemy')] #, getLogger('sqlalchemy.engine')]

    handler = StreamHandler()
    handler.setFormatter(Formatter('%(asctime)s %(levelname)s\t%(filename)s:%(lineno)d: %(message)s'))

    if debug:
        handler.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)

    for l in loggers:
        del l.handlers[:]
        l.setLevel(logging.DEBUG)
        l.addHandler(handler)

    app.logger.debug("Logging initialized") # with %s level", handler.getLevel())

def reading_to_dict(t, v, l = None):
    """
    Converts the tempareature reading to a ditionary.
    Usefull when returning JSON
    """

    return {"timestamp": t, "value": v, "location": l}
