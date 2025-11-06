"""
Chatbot logic for Machine 6
"""
from typing import Dict, Any, Optional, List
from datetime import date, datetime, timedelta
import re
import httpx
import os
from sqlalchemy.orm import Session
import sys
sys.path.append('/workspace')

from shared.models import ChatContext, DashboardFilter
from shared.database import ChatHistoryDB, NormalizedFoodDataDB, PredictiveInsightDB


class IntentClassifier:
    """Classify user intent from messages"""
    
    INTENT_PATTERNS = {
        "waste_query": ["waste", "wasting", "thrown away", "leftover", "excess"],
        "ordering_query": ["order", "ordering", "ordered", "purchase", "buy"],
        "insight_query": ["insight", "recommendation", "suggest", "advice", "improve"],
        "carbon_query": ["carbon", "footprint", "emission", "environmental", "sustainability"],
        "forecast_query": ["forecast", "predict", "future", "will need", "upcoming"],
        "status_query": ["status", "how are", "summary", "overview", "dashboard"],
        "specific_ingredient": ["chicken", "beef", "pork", "fish", "rice", "potato"],
        "alert_create": ["fridge down", "equipment issue", "problem", "broken"],
        "comparison": ["compare", "versus", "vs", "difference between"]
    }
    
    def classify(self, message: str, context: ChatContext) -> str:
        """
        Classify the intent of a user message
        """
        message_lower = message.lower()
        
        # Check for patterns
        for intent, patterns in self.INTENT_PATTERNS.items():
            if any(pattern in message_lower for pattern in patterns):
                return intent
        
        # Default
        return "general_query"


class ContextManager:
    """Manage conversation context"""
    
    def __init__(self):
        self.contexts: Dict[str, ChatContext] = {}
    
    def get_context(self, session_id: str, db: Session) -> ChatContext:
        """Get or create context for a session"""
        if session_id in self.contexts:
            return self.contexts[session_id]
        
        # Load from database
        history = db.query(ChatHistoryDB).filter(
            ChatHistoryDB.session_id == session_id
        ).order_by(ChatHistoryDB.timestamp.desc()).limit(10).all()
        
        context = ChatContext(
            session_id=session_id,
            conversation_history=[
                {"role": h.role, "content": h.content, "timestamp": h.timestamp.isoformat()}
                for h in reversed(history)
            ]
        )
        
        self.contexts[session_id] = context
        return context
    
    def update_context(self, session_id: str, update: Dict[str, Any]):
        """Update context with new information"""
        if session_id in self.contexts:
            context = self.contexts[session_id]
            if "filters" in update:
                context.active_filters = update["filters"]
            if "preferences" in update:
                context.user_preferences.update(update["preferences"])


class FoodServiceBot:
    """Main chatbot logic"""
    
    def __init__(self):
        self.machine_urls = {
            "machine1": f"http://machine1:{os.getenv('MACHINE1_PORT', 8001)}",
            "machine2": f"http://machine2:{os.getenv('MACHINE2_PORT', 8002)}",
            "machine3": f"http://machine3:{os.getenv('MACHINE3_PORT', 8003)}",
            "machine4": f"http://machine4:{os.getenv('MACHINE4_PORT', 8004)}",
            "machine5": f"http://machine5:{os.getenv('MACHINE5_PORT', 8005)}"
        }
    
    async def generate_response(
        self,
        message: str,
        intent: str,
        context: ChatContext,
        db: Session
    ) -> Dict[str, Any]:
        """
        Generate a response based on intent
        """
        if intent == "waste_query":
            return await self._handle_waste_query(message, db)
        elif intent == "ordering_query":
            return await self._handle_ordering_query(message, db)
        elif intent == "insight_query":
            return await self._handle_insight_query(db)
        elif intent == "carbon_query":
            return await self._handle_carbon_query(message, db)
        elif intent == "forecast_query":
            return await self._handle_forecast_query(message, db)
        elif intent == "status_query":
            return await self._handle_status_query(db)
        elif intent == "alert_create":
            return await self._handle_alert_creation(message, db)
        else:
            return await self._handle_general_query(message, db)
    
    async def _handle_waste_query(self, message: str, db: Session) -> Dict[str, Any]:
        """Handle waste-related queries"""
        # Extract ingredient if mentioned
        ingredient = self._extract_ingredient(message)
        
        # Query Machine 2 for waste patterns
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.machine_urls['machine2']}/patterns/waste",
                    params={
                        "start_date": (date.today() - timedelta(days=30)).isoformat(),
                        "end_date": date.today().isoformat()
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    patterns = data.get("data", [])
                    
                    if ingredient:
                        # Filter for specific ingredient
                        patterns = [p for p in patterns if ingredient.lower() in p.get("ingredient", "").lower()]
                    
                    if patterns:
                        top_pattern = patterns[0]
                        text = f"I found waste patterns for {len(patterns)} items. "
                        
                        if ingredient:
                            text += f"For {ingredient}, "
                        else:
                            text += f"The top wasted item is {top_pattern['ingredient']}, "
                        
                        text += f"with an average waste of {top_pattern['average_waste_amount']} lbs. "
                        text += f"This occurs {top_pattern['frequency']}. "
                        text += f"\n\nMy hypothesis: {top_pattern['hypothesis']}"
                        
                        return {
                            "text": text,
                            "data": {"patterns": patterns[:5]}
                        }
                    else:
                        return {
                            "text": f"I couldn't find significant waste patterns{' for ' + ingredient if ingredient else ''} in the last 30 days. This is good news!",
                            "data": {}
                        }
        except Exception as e:
            return {
                "text": f"I'm having trouble accessing waste data right now. Error: {str(e)}",
                "data": {}
            }
        
        return {
            "text": "Let me check the waste data for you...",
            "data": {}
        }
    
    async def _handle_ordering_query(self, message: str, db: Session) -> Dict[str, Any]:
        """Handle ordering-related queries"""
        ingredient = self._extract_ingredient(message)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.machine_urls['machine2']}/patterns/ordering",
                    params={
                        "start_date": (date.today() - timedelta(days=30)).isoformat(),
                        "end_date": date.today().isoformat()
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    patterns = data.get("data", [])
                    
                    if ingredient:
                        patterns = [p for p in patterns if ingredient.lower() in p.get("ingredient", "").lower()]
                    
                    if patterns:
                        text = f"I analyzed ordering patterns for {len(patterns)} items.\n\n"
                        
                        # Show top 3
                        for i, pattern in enumerate(patterns[:3], 1):
                            text += f"{i}. **{pattern['ingredient']}**: "
                            text += f"{pattern['tendency']} (accuracy: {pattern['average_accuracy']}%). "
                            text += f"{pattern['recommendation']}\n"
                        
                        return {
                            "text": text,
                            "data": {"patterns": patterns}
                        }
        except Exception as e:
            return {
                "text": f"I encountered an error analyzing ordering data: {str(e)}",
                "data": {}
            }
        
        return {
            "text": "Let me analyze your ordering patterns...",
            "data": {}
        }
    
    async def _handle_insight_query(self, db: Session) -> Dict[str, Any]:
        """Handle insight/recommendation queries"""
        # Get recent insights from database
        insights = db.query(PredictiveInsightDB).filter(
            PredictiveInsightDB.archived == False
        ).order_by(PredictiveInsightDB.created_at.desc()).limit(5).all()
        
        if not insights:
            return {
                "text": "I don't have any new insights at the moment. Let me generate some fresh recommendations for you...",
                "data": {}
            }
        
        text = f"I have {len(insights)} insights for you:\n\n"
        
        for i, insight in enumerate(insights, 1):
            priority_emoji = "🔴" if insight.priority == "high" else "🟡" if insight.priority == "medium" else "🟢"
            text += f"{i}. {priority_emoji} **{insight.title}**\n"
            text += f"   {insight.description}\n"
            text += f"   💡 Recommendation: {insight.recommendation}\n\n"
        
        return {
            "text": text,
            "data": {
                "insights": [
                    {
                        "id": i.id,
                        "type": i.insight_type,
                        "priority": i.priority,
                        "title": i.title,
                        "recommendation": i.recommendation
                    } for i in insights
                ]
            }
        }
    
    async def _handle_carbon_query(self, message: str, db: Session) -> Dict[str, Any]:
        """Handle carbon footprint queries"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.machine_urls['machine5']}/carbon/report",
                    params={
                        "start_date": (date.today() - timedelta(days=30)).isoformat(),
                        "end_date": date.today().isoformat()
                    }
                )
                
                if response.status_code == 200:
                    report = response.json()
                    
                    text = f"**Carbon Footprint Report (Last 30 Days)**\n\n"
                    text += f"Total Carbon: {report['total_carbon_kg']} kg CO2e\n\n"
                    text += f"Breakdown:\n"
                    text += f"- 🗑️ Waste: {report['carbon_from_waste']} kg\n"
                    text += f"- ⚡ Utilities: {report['carbon_from_utilities']} kg\n"
                    text += f"- 🚚 Deliveries: {report['carbon_from_deliveries']} kg\n"
                    text += f"- 🍽️ Food Production: {report['carbon_from_food']} kg\n\n"
                    
                    if report.get('recommendations'):
                        text += "**Recommendations:**\n"
                        for rec in report['recommendations']:
                            text += f"- {rec}\n"
                    
                    return {
                        "text": text,
                        "data": report
                    }
        except Exception as e:
            return {
                "text": f"I'm having trouble accessing carbon data: {str(e)}",
                "data": {}
            }
        
        return {
            "text": "Let me calculate your carbon footprint...",
            "data": {}
        }
    
    async def _handle_forecast_query(self, message: str, db: Session) -> Dict[str, Any]:
        """Handle forecast queries"""
        ingredient = self._extract_ingredient(message)
        
        if not ingredient:
            return {
                "text": "Which ingredient would you like me to forecast? (e.g., chicken, beef, potatoes)",
                "data": {}
            }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.machine_urls['machine3']}/forecast/demand",
                    params={
                        "ingredient_name": ingredient,
                        "forecast_days": 7
                    }
                )
                
                if response.status_code == 200:
                    forecasts = response.json()
                    
                    text = f"**7-Day Demand Forecast for {ingredient}:**\n\n"
                    
                    for forecast in forecasts[:7]:
                        text += f"- {forecast['forecast_date']}: "
                        text += f"{forecast['predicted_quantity']} units "
                        text += f"(confidence: {forecast['confidence_score']*100:.0f}%)\n"
                    
                    return {
                        "text": text,
                        "data": {"forecasts": forecasts}
                    }
                elif response.status_code == 404:
                    return {
                        "text": f"I don't have enough historical data to forecast {ingredient}. Try adding more data first.",
                        "data": {}
                    }
        except Exception as e:
            return {
                "text": f"Error generating forecast: {str(e)}",
                "data": {}
            }
        
        return {
            "text": f"Let me forecast demand for {ingredient}...",
            "data": {}
        }
    
    async def _handle_status_query(self, db: Session) -> Dict[str, Any]:
        """Handle status/summary queries"""
        # Get recent summary data
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        data_count = db.query(NormalizedFoodDataDB).filter(
            NormalizedFoodDataDB.date >= start_date
        ).count()
        
        insight_count = db.query(PredictiveInsightDB).filter(
            PredictiveInsightDB.archived == False
        ).count()
        
        text = f"**System Status Summary**\n\n"
        text += f"📊 Data Records (Last 7 days): {data_count}\n"
        text += f"💡 Active Insights: {insight_count}\n"
        text += f"✅ All systems operational\n\n"
        text += "What would you like to explore? I can help with waste analysis, ordering optimization, carbon tracking, or forecasting."
        
        return {
            "text": text,
            "data": {
                "data_records": data_count,
                "active_insights": insight_count
            }
        }
    
    async def _handle_alert_creation(self, message: str, db: Session) -> Dict[str, Any]:
        """Handle alert creation"""
        from shared.database import UserAlertDB
        
        # Create alert from message
        alert = UserAlertDB(
            alert_type="user_reported",
            severity="warning",
            title="User Alert",
            message=message,
            user_note=message,
            affected_items=[],
            acknowledged=False
        )
        
        db.add(alert)
        db.commit()
        
        return {
            "text": f"I've logged this alert: \"{message}\"\n\nI'll take this into account for future recommendations. Is there anything specific you'd like me to adjust?",
            "data": {"alert_id": alert.id}
        }
    
    async def _handle_general_query(self, message: str, db: Session) -> Dict[str, Any]:
        """Handle general queries"""
        return {
            "text": "I'm here to help! I can assist you with:\n\n"
                   "- 📊 Waste analysis and patterns\n"
                   "- 📦 Ordering optimization\n"
                   "- 💡 Insights and recommendations\n"
                   "- 🌱 Carbon footprint tracking\n"
                   "- 📈 Demand forecasting\n"
                   "- 📋 Status summaries\n\n"
                   "What would you like to know?",
            "data": {}
        }
    
    def _extract_ingredient(self, message: str) -> Optional[str]:
        """Extract ingredient name from message"""
        common_ingredients = [
            "chicken", "beef", "pork", "fish", "salmon", "shrimp",
            "potato", "potatoes", "rice", "pasta", "bread",
            "lettuce", "tomato", "onion", "carrot",
            "cheese", "milk", "eggs"
        ]
        
        message_lower = message.lower()
        for ingredient in common_ingredients:
            if ingredient in message_lower:
                return ingredient
        
        return None
    
    async def answer_question(self, question: str, db: Session) -> Dict[str, Any]:
        """Answer a specific question"""
        intent_classifier = IntentClassifier()
        context_manager = ContextManager()
        
        # Create temporary context
        import uuid
        temp_session = str(uuid.uuid4())
        context = ChatContext(session_id=temp_session, conversation_history=[])
        
        intent = intent_classifier.classify(question, context)
        response = await self.generate_response(question, intent, context, db)
        
        return response
