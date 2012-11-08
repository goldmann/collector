import datetime as dt
import time
import re

from flask import Flask
from flask import request
from flask import jsonify
from flask import make_response
from flask import abort, redirect, url_for

from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import NotFound

from sqlalchemy import desc

from database import init_db
from database import db_session
from reading import Reading
from graph import Graph
from utils import Timer, init_logging
from temperature import Temperature

DEBUG = False

def create_app(host = "0.0.0.0", port = 8080):
    app = Flask(__name__)

    """
    Creates a JSON-oriented Flask app.

    All error responses that you don't specifically
    manage yourself will have application/json content
    type, and will contain JSON
    """
    @app.errorhandler(Exception)
    def make_json_error(ex):
        if not isinstance(ex, HTTPException):
            app.logger.exception(ex)

        if isinstance(ex, ValueError):
            return jsonify(
                code = 400,
                message = "Invalid data",
                description = ex.message
            )

        try:
            response = jsonify(
                code = ex.code,
                message = ex.message,
                description = re.sub('<[^<]+?>', '', ex.description)
            )

            response.status_code = ex.code
        except AttributeError:
            response = jsonify(
                code = 500,
                message = "500 Internal server error",
                description = "Internal error occurred, please try again later and/or report it to the administrator"
            )

            response.status_code = 500

        return response

    init_logging(app, DEBUG)
    init_db()

    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    # Define the routes available in the application
    define_routes(app)

    app.logger.info("Application is ready")

    app.run(host, port, DEBUG)

def define_routes(app):
    @app.route("/")
    def hello():

        return "Hello World!"

    """
        if request.args.get("start") and request.args.get("end"):

#                start = int(request.args.get("start"))
#                end = int(request.args.get("end"))

        else:
            reading = Reading.query.order_by(desc(Reading.date)).limit(1).all()

            if not reading:
                raise NotFound(description = "No single reading found, please wait for measures")
            else:
                reading = reading.pop()
                return jsonify(date = reading.date, value = reading.value)
    """
    """
    Adds a new reading to the database.

    There can be several locations attached to the reading.
    
    """
    @app.route("/temperature", methods=['GET', 'POST'])
    def temperature():
        temp = Temperature(request)

        if request.args.get("accuracy"):
            temp.set_accuracy(int(request.args.get("accuracy")))

        if request.method == 'GET':
            return temp.process_get()
        elif request.method == 'POST':
            return temp.process_post()
    
    @app.teardown_request
    def shutdown_session(exception=None):
        db_session.remove()
 
create_app()
