"""
Shared data models used across all machines
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from decimal import Decimal


class MealPeriod(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    BRUNCH = "brunch"
    SNACK = "snack"
    RECEPTION = "reception"


class DataSource(str, Enum):
    BEO = "beo"
    INVOICE = "invoice"
    HANDWRITTEN_NOTE = "handwritten_note"
    INVENTORY_SYSTEM = "inventory_system"
    SYSCO = "sysco"
    VENDOR_INVOICE = "vendor_invoice"
    ACCOUNTING_SYSTEM = "accounting_system"
    CATERING_SYSTEM = "catering_system"
    POS_SYSTEM = "pos_system"
    PRODUCTION_SHEET = "production_sheet"


class WasteType(str, Enum):
    COMPOST = "compost"
    RECYCLING = "recycling"
    REGULAR_WASTE = "regular_waste"


class UnitOfMeasure(str, Enum):
    LB = "lb"
    OZ = "oz"
    KG = "kg"
    G = "g"
    PIECE = "piece"
    SERVING = "serving"
    CUP = "cup"
    GALLON = "gallon"
    LITER = "liter"


# Machine 1 Models - Data Ingestion
class RawDataInput(BaseModel):
    """Raw data from any source"""
    source: DataSource
    file_path: Optional[str] = None
    raw_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class NormalizedFoodData(BaseModel):
    """Normalized food service data output from Machine 1"""
    id: Optional[int] = None
    date: date
    event_name: Optional[str] = None
    location: str
    meal_period: MealPeriod
    original_guest_count: Optional[int] = None
    guest_count_change: Optional[int] = None
    final_guest_count: Optional[int] = None
    transaction_volume: Optional[Decimal] = None
    food_item_name: str
    food_ordered: Optional[Decimal] = None
    food_prepared: Optional[Decimal] = None
    food_used: Optional[Decimal] = None
    additional_food_prepared: Optional[Decimal] = None
    food_wasted_boh: Optional[Decimal] = None
    food_wasted_foh: Optional[Decimal] = None
    unit_of_measure: UnitOfMeasure
    source: DataSource
    source_document_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IngredientMapping(BaseModel):
    """Mapping for normalized ingredient names"""
    raw_name: str
    normalized_name: str
    confidence_score: float
    aliases: List[str] = Field(default_factory=list)


# Machine 2 Models - Statistical Analysis
class EventStatistics(BaseModel):
    """Statistical analysis for events"""
    date_range_start: date
    date_range_end: date
    total_events: int
    total_orders: int
    total_guests: int
    average_guests_per_event: float
    total_food_prepared: Dict[str, Decimal]
    total_food_used: Dict[str, Decimal]
    total_food_wasted: Dict[str, Decimal]
    waste_percentage: float
    accuracy_rate: float  # comparison of ordered vs used


class IngredientUsagePattern(BaseModel):
    """Patterns for ingredient usage"""
    ingredient_name: str
    time_period: str
    total_ordered: Decimal
    total_prepared: Decimal
    total_used: Decimal
    total_wasted: Decimal
    waste_percentage: float
    usage_by_meal_period: Dict[MealPeriod, Decimal]
    usage_by_location: Dict[str, Decimal]
    peak_usage_days: List[str]


class BEOComparisonAnalysis(BaseModel):
    """Analysis comparing before/after BEOs"""
    event_id: str
    original_beo_date: datetime
    revised_beo_date: datetime
    guest_count_variance: int
    food_item_changes: Dict[str, Dict[str, Any]]
    impact_on_waste: Optional[Decimal] = None
    cost_impact: Optional[Decimal] = None


# Machine 3 Models - Predictive Insights
class PredictiveInsight(BaseModel):
    """Insights and recommendations"""
    id: Optional[int] = None
    insight_type: str  # e.g., "waste_reduction", "ordering_optimization", "demand_forecast"
    priority: str  # high, medium, low
    title: str
    description: str
    recommendation: str
    expected_impact: Dict[str, Any]
    confidence_score: float
    based_on_data_points: int
    relevant_ingredients: List[str] = Field(default_factory=list)
    relevant_locations: List[str] = Field(default_factory=list)
    relevant_meal_periods: List[MealPeriod] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DemandForecast(BaseModel):
    """Forecast for future demand"""
    ingredient_name: str
    forecast_date: date
    predicted_quantity: Decimal
    confidence_interval_lower: Decimal
    confidence_interval_upper: Decimal
    confidence_score: float
    factors: List[str]  # factors influencing the forecast


class WastePattern(BaseModel):
    """Identified waste patterns"""
    pattern_type: str
    frequency: str
    affected_items: List[str]
    average_waste_amount: Decimal
    cost_impact: Decimal
    root_cause_hypothesis: str
    recommendation: str


# Machine 4 Models - Visualization
class DashboardFilter(BaseModel):
    """Filters for the dashboard"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    event_name: Optional[str] = None
    ingredient: Optional[str] = None
    menu_item: Optional[str] = None
    meal_period: Optional[MealPeriod] = None
    location: Optional[str] = None


class ChartData(BaseModel):
    """Data structure for charts"""
    chart_type: str  # line, bar, pie, scatter, heatmap
    title: str
    data: Dict[str, Any]
    options: Dict[str, Any] = Field(default_factory=dict)


# Machine 5 Models - Carbon Footprint
class WasteData(BaseModel):
    """Waste tracking data"""
    date: date
    location: str
    waste_type: WasteType
    weight: Decimal
    unit: UnitOfMeasure
    food_items: List[str] = Field(default_factory=list)


class UtilityData(BaseModel):
    """Utility usage data"""
    date: date
    location: str
    electricity_kwh: Optional[Decimal] = None
    gas_therms: Optional[Decimal] = None
    water_gallons: Optional[Decimal] = None


class DeliveryData(BaseModel):
    """Delivery tracking for carbon calculation"""
    date: date
    location: str
    number_of_deliveries: int
    total_distance_miles: Optional[Decimal] = None
    vehicle_type: Optional[str] = None


class MenuItemCarbon(BaseModel):
    """Carbon footprint per menu item"""
    menu_item: str
    ingredient_breakdown: Dict[str, Decimal]
    total_carbon_kg: Decimal
    carbon_by_category: Dict[str, Decimal]  # protein, vegetables, dairy, etc.


class CarbonFootprintReport(BaseModel):
    """Complete carbon footprint report"""
    date_range_start: date
    date_range_end: date
    total_carbon_kg: Decimal
    carbon_from_waste: Decimal
    carbon_from_utilities: Decimal
    carbon_from_deliveries: Decimal
    carbon_from_food: Decimal
    breakdown_by_location: Dict[str, Decimal]
    breakdown_by_category: Dict[str, Decimal]
    recommendations: List[str]


# Machine 6 Models - Chatbot
class ChatMessage(BaseModel):
    """Chat message"""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatContext(BaseModel):
    """Context for chatbot conversations"""
    session_id: str
    user_id: Optional[str] = None
    conversation_history: List[ChatMessage] = Field(default_factory=list)
    active_filters: Optional[DashboardFilter] = None
    user_preferences: Dict[str, Any] = Field(default_factory=dict)


class UserAlert(BaseModel):
    """Alerts and notifications"""
    id: Optional[int] = None
    alert_type: str
    severity: str  # info, warning, critical
    title: str
    message: str
    affected_items: List[str] = Field(default_factory=list)
    user_note: Optional[str] = None  # e.g., "walk-in fridge is down"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False


# Response Models
class HealthCheck(BaseModel):
    """Health check response"""
    service: str
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"


class APIResponse(BaseModel):
    """Generic API response"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
