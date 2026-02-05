from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base


class Sensor(Base):
    __tablename__ = "sensors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    type = Column(String, default="water")
    last_service = Column(DateTime, default=datetime.utcnow)

    readings = relationship("Reading", back_populates="sensor")
    alerts = relationship("Alert", back_populates="sensor")


class Reading(Base):
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    pH = Column(Float)
    DO2 = Column("DO", Float)
    BOD = Column(Float)
    COD = Column(Float)
    turbidity = Column(Float)
    ammonia = Column(Float)
    temperature = Column(Float)
    conductivity = Column(Float)

    sensor = relationship("Sensor", back_populates="readings")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    severity = Column(String, default="medium")
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)

    sensor = relationship("Sensor", back_populates="alerts")


class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, default="open")
    created_by = Column(String, default="anonymous")
    created_at = Column(DateTime, default=datetime.utcnow)
