"""
Machine 6: Orchestration Chatbot Service

Orchestrates all other machines and interfaces with users.
Provides conversational interface to make data better and insights more valuable.
Handles user alerts and contextual information.
"""
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import sys
import os
import httpx
import json

sys.path.append('/workspace')

from shared.models import (
    ChatMessage, ChatContext, UserAlert, HealthCheck, APIResponse
)
from shared.database import get_db, ChatHistoryDB, UserAlertDB
from services.machine6.bot import FoodServiceBot, IntentClassifier, ContextManager

app = FastAPI(title="Machine 6: Orchestration Chatbot", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize bot components
intent_classifier = IntentClassifier()
context_manager = ContextManager()
food_service_bot = FoodServiceBot()

# Service URLs
MACHINE1_URL = f"http://machine1:{os.getenv('MACHINE1_PORT', 8001)}"
MACHINE2_URL = f"http://machine2:{os.getenv('MACHINE2_PORT', 8002)}"
MACHINE3_URL = f"http://machine3:{os.getenv('MACHINE3_PORT', 8003)}"
MACHINE4_URL = f"http://machine4:{os.getenv('MACHINE4_PORT', 8004)}"
MACHINE5_URL = f"http://machine5:{os.getenv('MACHINE5_PORT', 8005)}"


@app.on_event("startup")
async def startup_event():
    print("Machine 6: Orchestration Chatbot Service started")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    return HealthCheck(service="Machine 6: Orchestration Chatbot", status="healthy")


@app.post("/chat/message", response_model=APIResponse)
async def send_message(
    message: str,
    session_id: str,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Send a message to the chatbot
    """
    try:
        # Get context
        context = context_manager.get_context(session_id, db)
        
        # Save user message
        user_msg = ChatHistoryDB(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=message,
            metadata={}
        )
        db.add(user_msg)
        db.commit()
        
        # Classify intent
        intent = intent_classifier.classify(message, context)
        
        # Generate response
        response = await food_service_bot.generate_response(message, intent, context, db)
        
        # Save bot message
        bot_msg = ChatHistoryDB(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=response["text"],
            metadata=response.get("data", {})
        )
        db.add(bot_msg)
        db.commit()
        
        return APIResponse(
            success=True,
            message="Response generated",
            data=response
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/session", response_model=APIResponse)
async def create_session(
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create a new chat session
    """
    try:
        import uuid
        session_id = str(uuid.uuid4())
        
        # Initialize with greeting
        greeting = ChatHistoryDB(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content="Hello! I'm your food service assistant. I can help you with waste analysis, ordering optimization, carbon footprint tracking, and much more. How can I assist you today?",
            metadata={}
        )
        db.add(greeting)
        db.commit()
        
        return APIResponse(
            success=True,
            message="Chat session created",
            data={"session_id": session_id}
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/history/{session_id}", response_model=List[ChatMessage])
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get chat history for a session
    """
    try:
        history = db.query(ChatHistoryDB).filter(
            ChatHistoryDB.session_id == session_id
        ).order_by(ChatHistoryDB.timestamp.asc()).limit(limit).all()
        
        return [
            ChatMessage(
                role=h.role,
                content=h.content,
                timestamp=h.timestamp,
                metadata=h.metadata or {}
            ) for h in history
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/create", response_model=APIResponse)
async def create_alert(
    alert: UserAlert,
    db: Session = Depends(get_db)
):
    """
    Create a user alert (e.g., "walk-in fridge is down")
    """
    try:
        db_alert = UserAlertDB(**alert.dict(exclude={'id'}))
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        
        return APIResponse(
            success=True,
            message="Alert created successfully",
            data={"alert_id": db_alert.id}
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts", response_model=List[UserAlert])
async def get_alerts(
    unacknowledged_only: bool = False,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get user alerts
    """
    try:
        query = db.query(UserAlertDB)
        
        if unacknowledged_only:
            query = query.filter(UserAlertDB.acknowledged == False)
        
        alerts = query.order_by(UserAlertDB.created_at.desc()).offset(skip).limit(limit).all()
        
        return [UserAlert.from_orm(alert) for alert in alerts]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/{alert_id}/acknowledge", response_model=APIResponse)
async def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Acknowledge an alert
    """
    try:
        alert = db.query(UserAlertDB).filter(UserAlertDB.id == alert_id).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert.acknowledged = True
        db.commit()
        
        return APIResponse(
            success=True,
            message="Alert acknowledged"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orchestrate/analyze-and-recommend", response_model=APIResponse)
async def orchestrate_full_analysis(
    location: Optional[str] = None,
    days_back: int = 30,
    db: Session = Depends(get_db)
):
    """
    Orchestrate a full analysis across all machines
    """
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        results = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get event statistics from Machine 2
            try:
                response = await client.get(
                    f"{MACHINE2_URL}/analyze/events",
                    params={
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "location": location
                    }
                )
                if response.status_code == 200:
                    results["event_statistics"] = response.json()
            except Exception as e:
                results["event_statistics"] = {"error": str(e)}
            
            # Generate insights from Machine 3
            try:
                response = await client.post(
                    f"{MACHINE3_URL}/insights/generate",
                    params={"days_to_analyze": days_back}
                )
                if response.status_code == 200:
                    results["insights"] = response.json()
            except Exception as e:
                results["insights"] = {"error": str(e)}
            
            # Get carbon report from Machine 5
            try:
                response = await client.get(
                    f"{MACHINE5_URL}/carbon/report",
                    params={
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "location": location
                    }
                )
                if response.status_code == 200:
                    results["carbon_report"] = response.json()
            except Exception as e:
                results["carbon_report"] = {"error": str(e)}
        
        return APIResponse(
            success=True,
            message="Full analysis completed",
            data=results
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orchestrate/quick-insights", response_model=APIResponse)
async def get_quick_insights(
    question: str,
    db: Session = Depends(get_db)
):
    """
    Get quick insights based on a natural language question
    """
    try:
        # Parse the question and route to appropriate machine
        insights = await food_service_bot.answer_question(question, db)
        
        return APIResponse(
            success=True,
            message="Insights generated",
            data=insights
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MACHINE6_PORT", 8006))
    uvicorn.run(app, host="0.0.0.0", port=port)
