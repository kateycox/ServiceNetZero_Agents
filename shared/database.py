"""
Database configuration and models
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date, Numeric, Boolean, Text, Enum as SQLEnum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/foodservice_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Models
class NormalizedFoodDataDB(Base):
    __tablename__ = "normalized_food_data"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    event_name = Column(String)
    location = Column(String, nullable=False, index=True)
    meal_period = Column(String, nullable=False, index=True)
    original_guest_count = Column(Integer)
    guest_count_change = Column(Integer)
    final_guest_count = Column(Integer)
    transaction_volume = Column(Numeric(10, 2))
    food_item_name = Column(String, nullable=False, index=True)
    food_ordered = Column(Numeric(10, 2))
    food_prepared = Column(Numeric(10, 2))
    food_used = Column(Numeric(10, 2))
    additional_food_prepared = Column(Numeric(10, 2))
    food_wasted_boh = Column(Numeric(10, 2))
    food_wasted_foh = Column(Numeric(10, 2))
    unit_of_measure = Column(String, nullable=False)
    source = Column(String, nullable=False)
    source_document_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IngredientMappingDB(Base):
    __tablename__ = "ingredient_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    raw_name = Column(String, nullable=False, index=True)
    normalized_name = Column(String, nullable=False, index=True)
    confidence_score = Column(Numeric(3, 2))
    aliases = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class PredictiveInsightDB(Base):
    __tablename__ = "predictive_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    insight_type = Column(String, nullable=False, index=True)
    priority = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    recommendation = Column(Text)
    expected_impact = Column(JSON)
    confidence_score = Column(Numeric(3, 2))
    based_on_data_points = Column(Integer)
    relevant_ingredients = Column(JSON)
    relevant_locations = Column(JSON)
    relevant_meal_periods = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    archived = Column(Boolean, default=False)


class WasteDataDB(Base):
    __tablename__ = "waste_data"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    location = Column(String, nullable=False, index=True)
    waste_type = Column(String, nullable=False)
    weight = Column(Numeric(10, 2), nullable=False)
    unit = Column(String, nullable=False)
    food_items = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class UtilityDataDB(Base):
    __tablename__ = "utility_data"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    location = Column(String, nullable=False, index=True)
    electricity_kwh = Column(Numeric(10, 2))
    gas_therms = Column(Numeric(10, 2))
    water_gallons = Column(Numeric(10, 2))
    created_at = Column(DateTime, default=datetime.utcnow)


class DeliveryDataDB(Base):
    __tablename__ = "delivery_data"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    location = Column(String, nullable=False, index=True)
    number_of_deliveries = Column(Integer, nullable=False)
    total_distance_miles = Column(Numeric(10, 2))
    vehicle_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserAlertDB(Base):
    __tablename__ = "user_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    affected_items = Column(JSON)
    user_note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged = Column(Boolean, default=False)


class ChatHistoryDB(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False, index=True)
    user_id = Column(String)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)


class RawDataInputDB(Base):
    __tablename__ = "raw_data_inputs"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    file_path = Column(String)
    raw_text = Column(Text)
    metadata = Column(JSON)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
