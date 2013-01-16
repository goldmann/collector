
class CollectorException(Exception):
    def __init__(self, message, description = None, code = 500):
        Exception.__init__(self, message)

        self.description = description
        self.code = code

class DataException(CollectorException):
    def __init__(self, message, description = None, code = 500):
        CollectorException.__init__(self, message, description, code)

