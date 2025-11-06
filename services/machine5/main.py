"""
Machine 5: Carbon Footprint Tracking Service

Measures carbon footprint accounting for:
- Waste data (compost, recycling, regular waste)
- Utilities data (electricity, gas, water)
- Number of deliveries
- Menu items carbon footprint (beef vs chicken vs fish vs vegetable)
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
import sys
import os

sys.path.append('/workspace')

from shared.models import (
    WasteData, UtilityData, DeliveryData, MenuItemCarbon, CarbonFootprintReport,
    HealthCheck, APIResponse, WasteType
)
from shared.database import (
    get_db, WasteDataDB, UtilityDataDB, DeliveryDataDB, NormalizedFoodDataDB
)
from services.machine5.calculators import CarbonCalculator, WasteCalculator, MenuItemCarbonCalculator

app = FastAPI(title="Machine 5: Carbon Footprint Tracking", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize calculators
carbon_calculator = CarbonCalculator()
waste_calculator = WasteCalculator()
menu_calculator = MenuItemCarbonCalculator()


@app.on_event("startup")
async def startup_event():
    print("Machine 5: Carbon Footprint Tracking Service started")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    return HealthCheck(service="Machine 5: Carbon Footprint Tracking", status="healthy")


@app.post("/waste/log", response_model=APIResponse)
async def log_waste(
    waste_data: WasteData,
    db: Session = Depends(get_db)
):
    """
    Log waste data
    """
    try:
        db_waste = WasteDataDB(**waste_data.dict())
        db.add(db_waste)
        db.commit()
        db.refresh(db_waste)
        
        return APIResponse(
            success=True,
            message="Waste data logged successfully",
            data={"id": db_waste.id}
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/utilities/log", response_model=APIResponse)
async def log_utilities(
    utility_data: UtilityData,
    db: Session = Depends(get_db)
):
    """
    Log utility usage data
    """
    try:
        db_utility = UtilityDataDB(**utility_data.dict())
        db.add(db_utility)
        db.commit()
        db.refresh(db_utility)
        
        return APIResponse(
            success=True,
            message="Utility data logged successfully",
            data={"id": db_utility.id}
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/deliveries/log", response_model=APIResponse)
async def log_delivery(
    delivery_data: DeliveryData,
    db: Session = Depends(get_db)
):
    """
    Log delivery data
    """
    try:
        db_delivery = DeliveryDataDB(**delivery_data.dict())
        db.add(db_delivery)
        db.commit()
        db.refresh(db_delivery)
        
        return APIResponse(
            success=True,
            message="Delivery data logged successfully",
            data={"id": db_delivery.id}
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/carbon/menu-item/{item_name}", response_model=MenuItemCarbon)
async def get_menu_item_carbon(
    item_name: str,
    db: Session = Depends(get_db)
):
    """
    Calculate carbon footprint for a specific menu item
    """
    try:
        # Get ingredient composition from recent data
        recent_date = date.today() - timedelta(days=30)
        
        ingredient_data = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.food_item_name == item_name,
                NormalizedFoodDataDB.date >= recent_date
            )
        ).all()
        
        if not ingredient_data:
            raise HTTPException(status_code=404, detail=f"No data found for menu item: {item_name}")
        
        carbon_data = menu_calculator.calculate_menu_item_carbon(item_name, ingredient_data)
        
        return carbon_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/carbon/report", response_model=CarbonFootprintReport)
async def get_carbon_report(
    start_date: date,
    end_date: date,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive carbon footprint report
    """
    try:
        # Get waste data
        waste_query = db.query(WasteDataDB).filter(
            and_(
                WasteDataDB.date >= start_date,
                WasteDataDB.date <= end_date
            )
        )
        if location:
            waste_query = waste_query.filter(WasteDataDB.location == location)
        waste_data = waste_query.all()
        
        # Get utility data
        utility_query = db.query(UtilityDataDB).filter(
            and_(
                UtilityDataDB.date >= start_date,
                UtilityDataDB.date <= end_date
            )
        )
        if location:
            utility_query = utility_query.filter(UtilityDataDB.location == location)
        utility_data = utility_query.all()
        
        # Get delivery data
        delivery_query = db.query(DeliveryDataDB).filter(
            and_(
                DeliveryDataDB.date >= start_date,
                DeliveryDataDB.date <= end_date
            )
        )
        if location:
            delivery_query = delivery_query.filter(DeliveryDataDB.location == location)
        delivery_data = delivery_query.all()
        
        # Get food data
        food_query = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        )
        if location:
            food_query = food_query.filter(NormalizedFoodDataDB.location == location)
        food_data = food_query.all()
        
        # Calculate carbon footprint
        report = carbon_calculator.generate_report(
            waste_data, utility_data, delivery_data, food_data,
            start_date, end_date
        )
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/carbon/waste-impact", response_model=APIResponse)
async def get_waste_carbon_impact(
    start_date: date,
    end_date: date,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Calculate carbon impact of waste
    """
    try:
        query = db.query(WasteDataDB).filter(
            and_(
                WasteDataDB.date >= start_date,
                WasteDataDB.date <= end_date
            )
        )
        
        if location:
            query = query.filter(WasteDataDB.location == location)
        
        waste_data = query.all()
        
        impact = waste_calculator.calculate_waste_impact(waste_data)
        
        return APIResponse(
            success=True,
            message="Waste carbon impact calculated",
            data=impact
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/carbon/comparison", response_model=APIResponse)
async def compare_carbon_footprint(
    period1_start: date,
    period1_end: date,
    period2_start: date,
    period2_end: date,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Compare carbon footprint between two periods
    """
    try:
        # Get report for period 1
        report1 = await get_carbon_report(period1_start, period1_end, location, db)
        
        # Get report for period 2
        report2 = await get_carbon_report(period2_start, period2_end, location, db)
        
        comparison = {
            "period1": {
                "start": period1_start.isoformat(),
                "end": period1_end.isoformat(),
                "total_carbon_kg": float(report1.total_carbon_kg)
            },
            "period2": {
                "start": period2_start.isoformat(),
                "end": period2_end.isoformat(),
                "total_carbon_kg": float(report2.total_carbon_kg)
            },
            "difference_kg": float(report2.total_carbon_kg - report1.total_carbon_kg),
            "percent_change": float((report2.total_carbon_kg - report1.total_carbon_kg) / report1.total_carbon_kg * 100) if report1.total_carbon_kg > 0 else 0,
            "improvement": report2.total_carbon_kg < report1.total_carbon_kg
        }
        
        return APIResponse(
            success=True,
            message="Carbon footprint comparison completed",
            data=comparison
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommendations/carbon-reduction", response_model=APIResponse)
async def get_carbon_reduction_recommendations(
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get recommendations for reducing carbon footprint
    """
    try:
        # Get recent data
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        # Get food data to analyze ingredient mix
        food_query = db.query(NormalizedFoodDataDB).filter(
            and_(
                NormalizedFoodDataDB.date >= start_date,
                NormalizedFoodDataDB.date <= end_date
            )
        )
        
        if location:
            food_query = food_query.filter(NormalizedFoodDataDB.location == location)
        
        food_data = food_query.all()
        
        recommendations = carbon_calculator.generate_recommendations(food_data)
        
        return APIResponse(
            success=True,
            message=f"Generated {len(recommendations)} carbon reduction recommendations",
            data=recommendations
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MACHINE5_PORT", 8005))
    uvicorn.run(app, host="0.0.0.0", port=port)
