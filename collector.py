import re

from flask import Flask
from flask import request
from flask import jsonify
from flask import abort, redirect, url_for

from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import NotFound

from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool
from sqlalchemy import Column, Integer, Float, String, create_engine, desc

from graph import Graph
from utils import Timer, init_logging
from temperature import Temperature

from errors import CollectorException

class Collector(Flask):
    def __init__(self):
        Flask.__init__(self, __name__)

        # Read configuration from file
        # If settings.py is founds, use it
        # If settings.py doesn't exists, use default_settings.py
        # If COLLECTOR_SETTINGS env variable is set use specified file it
        #
        # http://flask.pocoo.org/docs/config/#configuring-from-files
        try:
            self.config.from_object('settings')
        except:
            self.config.from_object('default_settings')

        try:
          self.config.from_envvar('COLLECTOR_SETTINGS')
        except:
          pass

        self.define_routes()
        self.register_error_handlers()

        init_logging(self)

    def define_routes(self):
        @self.route("/")
        def hello():
            return "Hello World!"

        """
        Adds a new reading to the database.
        There can be several locations attached to the reading.
        """
        @self.route("/temperature", methods=['GET', 'POST'])
        def temperature():
            # TODO request shouldn't be forwarded to application code
            temp = Temperature(request)

            if request.args.get("accuracy"):
                temp.set_accuracy(int(request.args.get("accuracy")))

            # TODO db_session is temporary here
            if request.method == 'GET':
                return temp.process_get(self.db_session)
            elif request.method == 'POST':
                return temp.process_post(self.db_session)

        @self.route("/temperature/last", methods=['GET'])
        def last():
            return Temperature(request).last()

        @self.teardown_request
        def shutdown_session(exception=None):
            self.db_session.remove()


    def rule_the_world(self):
        self.run(self.config['HOST'], self.config['PORT'], self.config['DEBUG'])

    def register_error_handlers(self):
        def prepare_error(message, description, code = None):

            if not code:
                code = 500

            response = jsonify(
                code = code,
                message = message,
                description = description
            )

            response.status_code = code

            return response

        @self.errorhandler(HTTPException)
        def http_error(ex):
            return prepare_error(ex.message, re.sub('<[^<]+?>', '', ex.description), ex.code)

        @self.errorhandler(CollectorException)
        def application_error(ex):
            self.logger.warn("%s: %s [%s]", ex.__class__.__name__, ex.message, ex.description)
            return prepare_error(ex.message, ex.description, ex.code)

        @self.errorhandler(Exception)
        def error(ex):
            return prepare_error(ex.message, None)

        for code in default_exceptions.iterkeys():
            self.error_handler_spec[None][code] = http_error


    def init_db(self):
        engine = create_engine("sqlite:///" + self.config['DATABASE'] , convert_unicode=True)
        self.db_session = scoped_session(sessionmaker(autocommit=False,
                                          autoflush=False,
                                          bind=engine))
        Base = declarative_base()
        Base.query = self.db_session.query_property()

        class Reading(Base):
            __tablename__ = 'readings'

            timestamp = Column(Integer, primary_key=True, unique=True)
            value = Column(Float, unique=False, nullable=False)
            location = Column(String, unique=False, nullable=True)

            def __init__(self, timestamp, value, location = None):
                self.timestamp = timestamp
                self.value = value
                self.location = location

            def __repr__(self):
                return "[Reading %s %s %s ]" % (self.timestamp, self.value, self.location)

        Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    collector = Collector()
    collector.init_db()
    collector.rule_the_world()
 
