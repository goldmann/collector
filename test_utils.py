import os
import tempfile

from application import Collector

class TestCollector:
    def __init__(self):
        self.collector = Collector()

    def start(self):
        self.collector.config['TESTING'] = True
        self.collector.config['LOG_LEVEL'] = 'DEBUG'
        self.db_fd, self.collector.config['DATABASE'] = tempfile.mkstemp()

        self.collector.init_db()

        return self.collector.test_client()

    def stop(self):
        os.close(self.db_fd)
        os.unlink(self.collector.config['DATABASE'])
