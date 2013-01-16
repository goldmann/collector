import unittest

from flask import json
from test_utils import TestCollector

class TestTemperatureSave(unittest.TestCase):

  def setUp(self):
    self.collector = TestCollector()
    self.app = self.collector.start()

  def tearDown(self):
    self.collector.stop()

  def test_no_data(self):
    r = self.app.post('/temperature')
    d = json.loads(r.data)

    assert r.status_code == 400

    assert d['code'] == 400
    assert d['message'] == "Invalid data"
    assert d['description'] == "Invalid parameters or no value for reading; forgot 'reading' parameter?"

  def test_save(self):
    r = self.app.post('/temperature', data = '{"reading": 12}', content_type = 'application/json')
    d = json.loads(r.data)


    assert r.status_code == 200

    assert d['value'] == 12
    assert d['location'] == None

  def test_save_with_location(self):
    r = self.app.post('/temperature', data = '{"reading": 12.2, "location": "balcony"}', content_type = 'application/json')
    d = json.loads(r.data)

    assert r.status_code == 200

    assert d['value'] == 12.2
    assert d['location'] == "balcony"

if __name__ == '__main__':
  unittest.main()
