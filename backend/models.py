# coding: utf-8
from sqlalchemy import Column, Float, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class DataHistory(Base):
    __tablename__ = 'data_history'

    sID = Column(Text, primary_key=True)
    name = Column(Text)
    obs_date = Column(Integer, primary_key=True)
    Temperature = Column(Float)
    Tmax = Column(Float)
    Tmin = Column(Float)
    Precp = Column(Float)
    PrecpHour = Column(Float)
    RH = Column(Float)
    StnPres = Column(Float)
    SeaPres = Column(Float)
    WS = Column(Float)
    WD = Column(Integer)
    WSmax = Column(Float)
    WDmax = Column(Integer)
    CloudAmount = Column(Float)
    SunShineHour = Column(Float)
    SunshineRate = Column(Float)
    GloblRad = Column(Float)
    UVImax = Column(Integer)


class DataRealtime(Base):
    __tablename__ = 'data_realtime'

    sID = Column(Text, primary_key=True)
    name = Column(Text)
    obs_time = Column(Integer)
    Precp = Column(Float)
    WD = Column(Float)
    WS = Column(Float)
    Temperature = Column(Float)
    RH = Column(Integer)
    UVI = Column(Float)


class StationList(Base):
    __tablename__ = 'station_list'

    sID = Column(Text, primary_key=True)
    name = Column(Text)
    alt = Column(Float)
    lon = Column(Float)
    lat = Column(Float)
    county = Column(Text)
    addr = Column(Text)
