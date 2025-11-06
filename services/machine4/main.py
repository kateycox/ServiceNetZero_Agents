"""
Machine 4: Visualization Dashboard Service

Visualizes data and insights from Machine 2 and 3.
Dashboard can be filtered by date, event, ingredient, menu item, meal period, location.
Provides interactive charts and reports.
"""
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
import sys
import os
import httpx

sys.path.append('/workspace')

from shared.models import (
    ChartData, DashboardFilter, HealthCheck, APIResponse
)
from shared.database import get_db, NormalizedFoodDataDB, PredictiveInsightDB
from services.machine4.visualizers import ChartGenerator, ReportGenerator

app = FastAPI(title="Machine 4: Visualization Dashboard", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
chart_generator = ChartGenerator()
report_generator = ReportGenerator()

# Setup templates (for HTML dashboard)
templates = Jinja2Templates(directory="/workspace/services/machine4/templates")


@app.on_event("startup")
async def startup_event():
    print("Machine 4: Visualization Dashboard Service started")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    return HealthCheck(service="Machine 4: Visualization Dashboard", status="healthy")


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """
    Serve the main dashboard HTML page
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.post("/charts/waste-overview", response_model=ChartData)
async def get_waste_overview_chart(
    filters: DashboardFilter,
    db: Session = Depends(get_db)
):
    """
    Get waste overview chart data
    """
    try:
        query = db.query(NormalizedFoodDataDB)
        
        if filters.start_date:
            query = query.filter(NormalizedFoodDataDB.date >= filters.start_date)
        if filters.end_date:
            query = query.filter(NormalizedFoodDataDB.date <= filters.end_date)
        if filters.location:
            query = query.filter(NormalizedFoodDataDB.location == filters.location)
        if filters.ingredient:
            query = query.filter(NormalizedFoodDataDB.food_item_name == filters.ingredient)
        if filters.meal_period:
            query = query.filter(NormalizedFoodDataDB.meal_period == filters.meal_period.value)
        
        data = query.all()
        chart = chart_generator.generate_waste_overview(data)
        
        return chart
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/charts/ingredient-usage", response_model=ChartData)
async def get_ingredient_usage_chart(
    filters: DashboardFilter,
    db: Session = Depends(get_db)
):
    """
    Get ingredient usage chart data
    """
    try:
        query = db.query(NormalizedFoodDataDB)
        
        if filters.start_date:
            query = query.filter(NormalizedFoodDataDB.date >= filters.start_date)
        if filters.end_date:
            query = query.filter(NormalizedFoodDataDB.date <= filters.end_date)
        if filters.location:
            query = query.filter(NormalizedFoodDataDB.location == filters.location)
        if filters.ingredient:
            query = query.filter(NormalizedFoodDataDB.food_item_name == filters.ingredient)
        
        data = query.all()
        chart = chart_generator.generate_ingredient_usage(data)
        
        return chart
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/charts/timeline", response_model=ChartData)
async def get_timeline_chart(
    filters: DashboardFilter,
    db: Session = Depends(get_db)
):
    """
    Get timeline chart showing trends over time
    """
    try:
        query = db.query(NormalizedFoodDataDB)
        
        if filters.start_date:
            query = query.filter(NormalizedFoodDataDB.date >= filters.start_date)
        if filters.end_date:
            query = query.filter(NormalizedFoodDataDB.date <= filters.end_date)
        if filters.location:
            query = query.filter(NormalizedFoodDataDB.location == filters.location)
        
        data = query.all()
        chart = chart_generator.generate_timeline(data)
        
        return chart
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/charts/location-comparison", response_model=ChartData)
async def get_location_comparison_chart(
    filters: DashboardFilter,
    db: Session = Depends(get_db)
):
    """
    Compare metrics across locations
    """
    try:
        query = db.query(NormalizedFoodDataDB)
        
        if filters.start_date:
            query = query.filter(NormalizedFoodDataDB.date >= filters.start_date)
        if filters.end_date:
            query = query.filter(NormalizedFoodDataDB.date <= filters.end_date)
        
        data = query.all()
        chart = chart_generator.generate_location_comparison(data)
        
        return chart
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/charts/meal-period-breakdown", response_model=ChartData)
async def get_meal_period_breakdown_chart(
    filters: DashboardFilter,
    db: Session = Depends(get_db)
):
    """
    Break down usage by meal period
    """
    try:
        query = db.query(NormalizedFoodDataDB)
        
        if filters.start_date:
            query = query.filter(NormalizedFoodDataDB.date >= filters.start_date)
        if filters.end_date:
            query = query.filter(NormalizedFoodDataDB.date <= filters.end_date)
        if filters.location:
            query = query.filter(NormalizedFoodDataDB.location == filters.location)
        
        data = query.all()
        chart = chart_generator.generate_meal_period_breakdown(data)
        
        return chart
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/charts/accuracy-rate", response_model=ChartData)
async def get_accuracy_rate_chart(
    filters: DashboardFilter,
    db: Session = Depends(get_db)
):
    """
    Show ordering accuracy over time
    """
    try:
        query = db.query(NormalizedFoodDataDB)
        
        if filters.start_date:
            query = query.filter(NormalizedFoodDataDB.date >= filters.start_date)
        if filters.end_date:
            query = query.filter(NormalizedFoodDataDB.date <= filters.end_date)
        if filters.location:
            query = query.filter(NormalizedFoodDataDB.location == filters.location)
        
        data = query.filter(
            and_(
                NormalizedFoodDataDB.food_ordered.isnot(None),
                NormalizedFoodDataDB.food_used.isnot(None)
            )
        ).all()
        
        chart = chart_generator.generate_accuracy_chart(data)
        
        return chart
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dashboard/summary", response_model=APIResponse)
async def get_dashboard_summary(
    filters: DashboardFilter,
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for dashboard
    """
    try:
        query = db.query(NormalizedFoodDataDB)
        
        if filters.start_date:
            query = query.filter(NormalizedFoodDataDB.date >= filters.start_date)
        if filters.end_date:
            query = query.filter(NormalizedFoodDataDB.date <= filters.end_date)
        if filters.location:
            query = query.filter(NormalizedFoodDataDB.location == filters.location)
        if filters.ingredient:
            query = query.filter(NormalizedFoodDataDB.food_item_name == filters.ingredient)
        if filters.meal_period:
            query = query.filter(NormalizedFoodDataDB.meal_period == filters.meal_period.value)
        
        data = query.all()
        
        # Calculate summary statistics
        total_events = len(set(f"{d.date}_{d.event_name}" for d in data if d.event_name))
        total_guests = sum(d.final_guest_count or 0 for d in data)
        
        total_prepared = sum(float(d.food_prepared or 0) for d in data)
        total_used = sum(float(d.food_used or 0) for d in data)
        total_wasted = sum(float((d.food_wasted_boh or 0) + (d.food_wasted_foh or 0)) for d in data)
        
        waste_percentage = (total_wasted / total_prepared * 100) if total_prepared > 0 else 0
        
        # Get recent insights
        insights_query = db.query(PredictiveInsightDB).filter(
            PredictiveInsightDB.archived == False
        ).order_by(PredictiveInsightDB.created_at.desc()).limit(5)
        
        insights = insights_query.all()
        
        summary = {
            "total_events": total_events,
            "total_guests": total_guests,
            "total_prepared_lb": round(total_prepared, 2),
            "total_used_lb": round(total_used, 2),
            "total_wasted_lb": round(total_wasted, 2),
            "waste_percentage": round(waste_percentage, 2),
            "recent_insights": [
                {
                    "title": i.title,
                    "priority": i.priority,
                    "type": i.insight_type
                } for i in insights
            ]
        }
        
        return APIResponse(
            success=True,
            message="Dashboard summary generated",
            data=summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reports/generate", response_model=APIResponse)
async def generate_report(
    filters: DashboardFilter,
    report_type: str = "comprehensive",
    db: Session = Depends(get_db)
):
    """
    Generate a comprehensive report
    """
    try:
        query = db.query(NormalizedFoodDataDB)
        
        if filters.start_date:
            query = query.filter(NormalizedFoodDataDB.date >= filters.start_date)
        if filters.end_date:
            query = query.filter(NormalizedFoodDataDB.date <= filters.end_date)
        if filters.location:
            query = query.filter(NormalizedFoodDataDB.location == filters.location)
        
        data = query.all()
        
        report = report_generator.generate_report(data, report_type, filters)
        
        return APIResponse(
            success=True,
            message=f"{report_type.capitalize()} report generated",
            data=report
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/filters/options", response_model=APIResponse)
async def get_filter_options(db: Session = Depends(get_db)):
    """
    Get available filter options (locations, ingredients, etc.)
    """
    try:
        locations = db.query(NormalizedFoodDataDB.location).distinct().all()
        ingredients = db.query(NormalizedFoodDataDB.food_item_name).distinct().all()
        events = db.query(NormalizedFoodDataDB.event_name).distinct().filter(
            NormalizedFoodDataDB.event_name.isnot(None)
        ).all()
        
        options = {
            "locations": [loc[0] for loc in locations],
            "ingredients": [ing[0] for ing in ingredients],
            "events": [evt[0] for evt in events],
            "meal_periods": ["breakfast", "lunch", "dinner", "brunch", "snack", "reception"]
        }
        
        return APIResponse(
            success=True,
            message="Filter options retrieved",
            data=options
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MACHINE4_PORT", 8004))
    uvicorn.run(app, host="0.0.0.0", port=port)
