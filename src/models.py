from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class CSVData(Base):
    """Generic table for CSV data - will be dynamically created based on CSV structure"""
    __tablename__ = 'csv_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Dynamic columns will be added based on CSV structure
    # This is a flexible approach that can handle any CSV structure

def get_database_engine():
    """Get database engine from environment"""
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    return create_engine(DATABASE_URL)

def get_session():
    """Get database session"""
    engine = get_database_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def create_tables():
    """Create all tables"""
    engine = get_database_engine()
    Base.metadata.create_all(bind=engine)
