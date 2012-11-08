from sqlalchemy import Column, Integer, Float

from database1 import db

class Reading(db.Model):
    __tablename__ = 'readings'
    date = db.Column(db.Integer, primary_key=True, unique=True)
    value = db.Column(db.Float, unique=False)

    def __init__(self, date, value):
        self.date = date
        self.value = value

    def __repr__(self):
        return '<Reading %i : %f >' % self.date, self.value
