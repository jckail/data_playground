from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class RequestResponseLog(Base):
    __tablename__ = 'request_response_logs'
    id = Column(Integer, primary_key=True, index=True)
    method = Column(String, index=True)
    url = Column(String, index=True)
    request_body = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    status_code = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())