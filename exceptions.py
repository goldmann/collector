
class DataException(Exception):
    def __init__(self, message, description = None):
        Exception.__init__(self, message)

        self.code = 500
        self.description = description

