"""
Machine 2: Statistical Analysis & Pattern Detection Service

Calculates patterns on data: orders per week, events, ingredient usage per event.
Compares before/after BEOs, multiple invoices against production sheets.
Performs mathematical and statistical analysis on food service data.
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
import sys
import os

sys.path.append('/workspace')

from shared.models import (
    EventStatistics, IngredientUsagePattern, BEOComparisonAnalysis,
    HealthCheck, APIResponse, DashboardFilter
)
from shared.database import get_db, NormalizedFoodDataDB
from services.machine2.analyzers import (
    EventAnalyzer, IngredientAnalyzer, BEOComparator, PatternDetector
)

app = FastAPI(title="Machine 2: Statistical Analysis & Pattern Detection", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize analyzers
event_analyzer = EventAnalyzer()
ingredient_analyzer = IngredientAnalyzer()
beo_comparator = BEOComparator()
pattern_detector = PatternDetector()


@app.on_event("startup")
async def startup_event():
    print("Machine 2: Statistical Analysis & Pattern Detection Service started")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    return HealthCheck(service="Machine 2: Statistical Analysis & Pattern Detection", status="healthy")


@app.get("/analyze/events", response_model=EventStatistics)
async def analyze_events(
    start_date: date,
    end_date: date,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Analyze events within a date range
    Returns statistics on orders, guests, food prepared, used, and wasted
    """
    try:
        query = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        )
        
        if location:
            query = query.filter(NormalizedFoodDataDB.location == location)
        
        data = query.all()
        statistics = event_analyzer.analyze(data, start_date, end_date)
        
        return statistics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/ingredient/{ingredient_name}", response_model=IngredientUsagePattern)
async def analyze_ingredient(
    ingredient_name: str,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Analyze usage patterns for a specific ingredient
    """
    try:
        data = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.food_item_name == ingredient_name,
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        ).all()
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No data found for ingredient: {ingredient_name}")
        
        pattern = ingredient_analyzer.analyze(ingredient_name, data, start_date, end_date)
        
        return pattern
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/ingredients/all", response_model=List[IngredientUsagePattern])
async def analyze_all_ingredients(
    start_date: date,
    end_date: date,
    location: Optional[str] = None,
    min_usage: float = 0,
    db: Session = Depends(get_db)
):
    """
    Analyze usage patterns for all ingredients
    """
    try:
        query = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        )
        
        if location:
            query = query.filter(NormalizedFoodDataDB.location == location)
        
        # Get all unique ingredients
        ingredients = db.query(NormalizedFoodDataDB.food_item_name).distinct().all()
        
        patterns = []
        for (ingredient_name,) in ingredients:
            ingredient_data = query.filter(
                NormalizedFoodDataDB.food_item_name == ingredient_name
            ).all()
            
            if ingredient_data:
                pattern = ingredient_analyzer.analyze(ingredient_name, ingredient_data, start_date, end_date)
                if pattern.total_used >= min_usage:
                    patterns.append(pattern)
        
        # Sort by total usage
        patterns.sort(key=lambda x: x.total_used, reverse=True)
        
        return patterns
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/compare/beo", response_model=List[BEOComparisonAnalysis])
async def compare_beos(
    event_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Compare before and after BEOs to identify changes
    """
    try:
        query = db.query(NormalizedFoodDataDB).filter(
            NormalizedFoodDataDB.source == 'beo'
        )
        
        if event_name:
            query = query.filter(NormalizedFoodDataDB.event_name == event_name)
        if start_date:
            query = query.filter(NormalizedFoodDataDB.date >= start_date)
        if end_date:
            query = query.filter(NormalizedFoodDataDB.date <= end_date)
        
        data = query.all()
        comparisons = beo_comparator.compare(data)
        
        return comparisons
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/patterns/waste", response_model=APIResponse)
async def detect_waste_patterns(
    start_date: date,
    end_date: date,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Detect waste patterns across time periods
    """
    try:
        query = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        )
        
        if location:
            query = query.filter(NormalizedFoodDataDB.location == location)
        
        data = query.all()
        patterns = pattern_detector.detect_waste_patterns(data)
        
        return APIResponse(
            success=True,
            message=f"Found {len(patterns)} waste patterns",
            data=patterns
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/patterns/ordering", response_model=APIResponse)
async def detect_ordering_patterns(
    start_date: date,
    end_date: date,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Detect ordering patterns and accuracy
    """
    try:
        query = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        )
        
        if location:
            query = query.filter(NormalizedFoodDataDB.location == location)
        
        data = query.all()
        patterns = pattern_detector.detect_ordering_patterns(data)
        
        return APIResponse(
            success=True,
            message=f"Analyzed ordering patterns for {len(patterns)} ingredients",
            data=patterns
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/patterns/seasonal", response_model=APIResponse)
async def detect_seasonal_patterns(
    ingredient_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Detect seasonal usage patterns
    """
    try:
        query = db.query(NormalizedFoodDataDB)
        
        if ingredient_name:
            query = query.filter(NormalizedFoodDataDB.food_item_name == ingredient_name)
        
        data = query.all()
        patterns = pattern_detector.detect_seasonal_patterns(data)
        
        return APIResponse(
            success=True,
            message=f"Detected seasonal patterns",
            data=patterns
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/statistics/weekly-summary", response_model=APIResponse)
async def weekly_summary(
    week_start: date,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get a weekly summary of all statistics
    """
    try:
        week_end = week_start + timedelta(days=6)
        
        query = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= week_start,
                NormalizedFoodDataDB.date <= week_end
            )
        )
        
        if location:
            query = query.filter(NormalizedFoodDataDB.location == location)
        
        data = query.all()
        
        # Calculate various metrics
        total_events = len(set(d.event_name for d in data if d.event_name))
        total_orders = len(data)
        total_guests = sum(d.final_guest_count or 0 for d in data)
        
        # Food metrics
        total_prepared = sum(float(d.food_prepared or 0) for d in data)
        total_used = sum(float(d.food_used or 0) for d in data)
        total_wasted = sum(float(d.food_wasted_boh or 0) + float(d.food_wasted_foh or 0) for d in data)
        
        waste_percentage = (total_wasted / total_prepared * 100) if total_prepared > 0 else 0
        
        summary = {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "total_events": total_events,
            "total_orders": total_orders,
            "total_guests": total_guests,
            "total_prepared_lb": round(total_prepared, 2),
            "total_used_lb": round(total_used, 2),
            "total_wasted_lb": round(total_wasted, 2),
            "waste_percentage": round(waste_percentage, 2)
        }
        
        return APIResponse(
            success=True,
            message="Weekly summary generated",
            data=summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MACHINE2_PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
