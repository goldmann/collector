import datetime as dt
import time

from flask import current_app as app
from flask import make_response
from flask import jsonify

from utils import Timer, reading_to_dict
from graph import Graph
from database import db_session
from reading import Reading

from collector.exceptions import *

class Temperature:

    def __init__(self, request):
        self.request = request

        # Default accuracy of the graph.
        # Lower accuracy speeds up generating the graph
        self.accuracy = 3

        # Show recorded data points on graph?
        # Showing them slowes down generating the graph
        self.data_points = False

        # List of supported mime types
        self.mime = {   'image/png': 'png',
                    'image/svg+xml': 'svg',
                 'application/json': 'json',
                  'application/pdf': 'pdf'}

    def set_accuracy(self, accuracy):
        if accuracy <= 0 or accuracy > 5:
            raise DataException("Invalid data", "Provided accuracy value is out of range for accuracy; use value between 1 and 5", 400)

        self.accuracy = accuracy

    def set_maximize(self, maximize):
        pass

    def validate_time_range(self):
        if self.request.args.get("start") and self.request.args.get("end"):
            app.logger.debug("Got both; 'start' and 'end' dates for graph")
            start = int(self.request.args.get("start"))
            end = int(self.request.args.get("end"))
        elif self.request.args.get("start") and not self.request.args.get("end"):
            app.logger.debug("Got only 'start' date for graph, 'end' will be calculated")
            start = int(self.request.args.get("start"))
            end = start + 86400 # 24h later
        elif self.request.args.get("end") and not self.request.args.get("start"):
            app.logger.debug("Got only 'end' date for graph, 'start' will be calculated")
            end = int(self.request.args.get("end"))
            start = end - 86400 # 24h earlier
        else:
            app.logger.debug("No dates specified, both 'start' and 'end' will be calculated")
            end = int(time.mktime(time.localtime()))
            start = end - 86400 # 24h earlier

        if start > end:
            raise DataException("Invalid data range", "Start date is older than end date", 400)

        return start, end

    def negotiate_mime(self):
        """ Returns the ngotiated content type and extension """

        selected_mime = self.request.accept_mimetypes.best_match(self.mime.keys())
        extension = self.mime[selected_mime]

        app.logger.debug("Negotiated response content type: %s; extension: %s", selected_mime, extension)

        return selected_mime, extension

    def accuracy_factor(self, start, end):
        """
        # > month 101 - 200 pow 40 40 - 200
        # > week 11 -  100  pow 20 20 -  80
        # > day  7 - 10     pow 2   2 -  10
        #  2 min  1 - 6     pow 1   1 -   5
        """

        graph_range = end - start

        minute = 60
        hour = 60 * minute
        day = 24 * hour
        week = 7 * day
        month = 30 * week

        factor = 40

        if graph_range < day:
            factor = 1

        if graph_range < week:
            factor = 2

        if graph_range < month:
            factor = 20
 
        app.logger.debug("Factor: %d", factor)
        app.logger.debug("Accuracy: %d", self.accuracy)
        app.logger.debug("Result: %d", factor * (6 - self.accuracy))

        return factor * (6 - self.accuracy)

    def read_data(self, start, end):
        readings = []

        with Timer() as duration:
#            result = db_session.execute("SELECT * FROM readings WHERE (date between :start and :end) AND (rowid - (SELECT rowid FROM readings WHERE (date > :start) ORDER BY date DESC LIMIT 1)) % :accuracy = 0 ORDER BY date DESC", {'start': start, 'end': end, 'accuracy': self.accuracy_factor(start, end)})
            result = db_session.execute("SELECT * FROM readings WHERE (timestamp between :start and :end) ORDER BY timestamp DESC", {'start': start, 'end': end, 'accuracy': self.accuracy_factor(start, end)})
        
        for r in result:
            readings.append([r['timestamp'], r['value'], r['location']])

        if not readings:
            raise DataException("No data", "Requested data range does not have any data; try different range", 400)

        app.logger.info("Reading %d records from database took %d ms", len(readings), duration.miliseconds())

        return readings

    def process_get(self):
        start, end = self.validate_time_range()
        readings = self.read_data(start, end)
        selected_mime, ext = self.negotiate_mime()

        # Add the current timestamp with reading from last one read to generate appropriate graphics
        readings.insert(0, [int(time.mktime(time.localtime())), readings[0][1], None])

        if ext is not 'json':
            graph = Graph(readings)
#            graph.set_maximize(True)

            with Timer() as duration:
                data = graph.build().render(ext)

            app.logger.info("Graph was generated in %d ms", duration.miliseconds())

            response = make_response(data)
        else:
            response = make_response(jsonify(readings = readings))


        if ext == 'svg':
            response.headers['Content-Type'] = 'image/svg+xml'
        elif ext == 'json':
            response.headers['Content-Type'] = 'application/json'
        elif ext == 'pdf':
            response.headers['Content-Disposition'] = 'attachment; filename="temperature.pdf"'
            response.headers['Content-Type'] = 'application/pdf'
        else:
            response.headers['Content-Type'] = 'image/png'

        return response

    def process_post(self):
        app.logger.debug("Processing new reading...")

        j = self.request.json

        if j == None or j['reading'] == None:
            raise DataException("Invalid data", "Invalid parameters or no value for reading; forgot 'reading' parameter?", 400)

        try:
            # current value (in C)
            v = float(j['reading'])
        except ValueError:
            raise DataException("Invalid data", "Parameter 'reading' accepts only float numbers", 400)

        # current time
        t = int(time.mktime(time.localtime()))
        # location of the meter
        l = None
        # only if the difference is bigger than this delta
        # we'll save the value in the database
        delta = 0.08

        result = db_session.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1").first()

        if result:
            difference = abs(result['value'] - v)
            if not difference > delta:
                """
                The value we want to save doesn't differ much from last reading.
                Ommit the value and return last reading
                """

                app.logger.debug("Trying to save too similar reading (difference: " + difference + "), skipping")

                return jsonify(reading_to_dict(result['timestamp'], result['value'], result['location']))
        
#        db_session.begin()

        try:
            db_session.execute("INSERT INTO readings values (:time, :reading, :location)", {'time': t, 'reading': v, 'location': l})
            db_session.commit()
        except:
            db_session.rollback()
            raise

        return jsonify(reading_to_dict(t, v))

    def last(self):
        result = db_session.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1").first()

        if result:
          return make_response("<h1 style=\"font-size: 80px;\">Last reading: " + str(result['value']) + u"\u00B0C</h1><h2 style=\"font-size: 40px\">Updated at " + time.ctime(result['timestamp']) + "</h2>")
        else:
          return make_response("No last reading")
