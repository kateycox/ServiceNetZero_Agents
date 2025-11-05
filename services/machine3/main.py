"""
Machine 3: Predictive Insights & Recommendations Service

Draws insights from findings to make recommendations.
Looks for patterns to predict what will happen based on past data.
Provides actionable recommendations over time.
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import date, datetime, timedelta
import sys
import os

sys.path.append('/workspace')

from shared.models import (
    PredictiveInsight, DemandForecast, WastePattern,
    HealthCheck, APIResponse
)
from shared.database import get_db, NormalizedFoodDataDB, PredictiveInsightDB
from services.machine3.predictors import (
    DemandPredictor, WastePredictor, InsightGenerator, RecommendationEngine
)

app = FastAPI(title="Machine 3: Predictive Insights & Recommendations", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize predictors
demand_predictor = DemandPredictor()
waste_predictor = WastePredictor()
insight_generator = InsightGenerator()
recommendation_engine = RecommendationEngine()


@app.on_event("startup")
async def startup_event():
    print("Machine 3: Predictive Insights & Recommendations Service started")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    return HealthCheck(service="Machine 3: Predictive Insights & Recommendations", status="healthy")


@app.post("/forecast/demand", response_model=List[DemandForecast])
async def forecast_demand(
    ingredient_name: str,
    forecast_days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Forecast demand for an ingredient for the next N days
    """
    try:
        # Get historical data (last 90 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=90)
        
        historical_data = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.food_item_name == ingredient_name,
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        ).all()
        
        if not historical_data:
            raise HTTPException(status_code=404, detail=f"No historical data found for {ingredient_name}")
        
        forecasts = demand_predictor.forecast(ingredient_name, historical_data, forecast_days)
        
        return forecasts
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/insights/generate", response_model=APIResponse)
async def generate_insights(
    days_to_analyze: int = 30,
    force_regenerate: bool = False,
    db: Session = Depends(get_db)
):
    """
    Generate insights based on recent data
    """
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days_to_analyze)
        
        # Get data
        data = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        ).all()
        
        if not data:
            return APIResponse(
                success=False,
                message="No data available for generating insights",
                errors=["Insufficient data"]
            )
        
        # Generate insights
        insights = insight_generator.generate(data)
        
        # Save insights to database
        saved_insights = []
        for insight in insights:
            db_insight = PredictiveInsightDB(**insight.dict(exclude={'id'}))
            db.add(db_insight)
            saved_insights.append(db_insight)
        
        db.commit()
        
        return APIResponse(
            success=True,
            message=f"Generated {len(saved_insights)} insights",
            data={"insights_count": len(saved_insights)}
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/insights", response_model=List[PredictiveInsight])
async def get_insights(
    priority: Optional[str] = None,
    insight_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get all generated insights
    """
    try:
        query = db.query(PredictiveInsightDB).filter(
            PredictiveInsightDB.archived == False
        )
        
        if priority:
            query = query.filter(PredictiveInsightDB.priority == priority)
        
        if insight_type:
            query = query.filter(PredictiveInsightDB.insight_type == insight_type)
        
        query = query.order_by(PredictiveInsightDB.created_at.desc())
        
        insights = query.offset(skip).limit(limit).all()
        
        return [PredictiveInsight.from_orm(insight) for insight in insights]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/insights/{insight_id}/archive", response_model=APIResponse)
async def archive_insight(
    insight_id: int,
    db: Session = Depends(get_db)
):
    """
    Archive an insight (mark as no longer relevant)
    """
    try:
        insight = db.query(PredictiveInsightDB).filter(
            PredictiveInsightDB.id == insight_id
        ).first()
        
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")
        
        insight.archived = True
        db.commit()
        
        return APIResponse(
            success=True,
            message="Insight archived successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommendations/waste-reduction", response_model=APIResponse)
async def get_waste_reduction_recommendations(
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get recommendations for reducing waste
    """
    try:
        # Get recent data
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        query = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        )
        
        if location:
            query = query.filter(NormalizedFoodDataDB.location == location)
        
        data = query.all()
        
        recommendations = recommendation_engine.generate_waste_recommendations(data)
        
        return APIResponse(
            success=True,
            message=f"Generated {len(recommendations)} waste reduction recommendations",
            data=recommendations
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommendations/ordering-optimization", response_model=APIResponse)
async def get_ordering_recommendations(
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get recommendations for optimizing ordering
    """
    try:
        # Get recent data
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        query = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        )
        
        if location:
            query = query.filter(NormalizedFoodDataDB.location == location)
        
        data = query.all()
        
        recommendations = recommendation_engine.generate_ordering_recommendations(data)
        
        return APIResponse(
            success=True,
            message=f"Generated {len(recommendations)} ordering optimization recommendations",
            data=recommendations
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/predict/waste-risk", response_model=APIResponse)
async def predict_waste_risk(
    ingredient_name: Optional[str] = None,
    days_ahead: int = 7,
    db: Session = Depends(get_db)
):
    """
    Predict waste risk for upcoming period
    """
    try:
        # Get historical data
        end_date = date.today()
        start_date = end_date - timedelta(days=60)
        
        query = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        )
        
        if ingredient_name:
            query = query.filter(NormalizedFoodDataDB.food_item_name == ingredient_name)
        
        data = query.all()
        
        predictions = waste_predictor.predict_waste_risk(data, days_ahead)
        
        return APIResponse(
            success=True,
            message=f"Predicted waste risk for next {days_ahead} days",
            data=predictions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trends/analysis", response_model=APIResponse)
async def analyze_trends(
    ingredient_name: Optional[str] = None,
    days_to_analyze: int = 90,
    db: Session = Depends(get_db)
):
    """
    Analyze trends over time
    """
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days_to_analyze)
        
        query = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        )
        
        if ingredient_name:
            query = query.filter(NormalizedFoodDataDB.food_item_name == ingredient_name)
        
        data = query.all()
        
        trends = insight_generator.analyze_trends(data)
        
        return APIResponse(
            success=True,
            message="Trend analysis completed",
            data=trends
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MACHINE3_PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)
