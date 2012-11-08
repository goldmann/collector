from database import Base
from sqlalchemy import Column, Integer, Float, String

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

