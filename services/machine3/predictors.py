"""
Predictive models and insight generators for Machine 3
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from scipy import stats
from collections import defaultdict
from typing import List, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
import sys
sys.path.append('/workspace')

from shared.models import PredictiveInsight, DemandForecast, WastePattern
from shared.database import NormalizedFoodDataDB


class DemandPredictor:
    """Predict future demand for ingredients"""
    
    def forecast(self, ingredient_name: str, historical_data: List[NormalizedFoodDataDB], 
                 forecast_days: int) -> List[DemandForecast]:
        """
        Forecast demand using time series analysis
        """
        # Prepare data
        df_data = []
        for record in historical_data:
            df_data.append({
                'date': record.date,
                'used': float(record.food_used or 0),
                'day_of_week': record.date.weekday(),
                'month': record.date.month
            })
        
        df = pd.DataFrame(df_data)
        df = df.groupby('date')['used'].sum().reset_index()
        df = df.sort_values('date')
        
        if len(df) < 7:
            # Not enough data, use simple average
            avg_usage = df['used'].mean()
            forecasts = []
            
            for i in range(forecast_days):
                forecast_date = date.today() + timedelta(days=i+1)
                forecasts.append(DemandForecast(
                    ingredient_name=ingredient_name,
                    forecast_date=forecast_date,
                    predicted_quantity=Decimal(str(round(avg_usage, 2))),
                    confidence_interval_lower=Decimal(str(round(avg_usage * 0.7, 2))),
                    confidence_interval_upper=Decimal(str(round(avg_usage * 1.3, 2))),
                    confidence_score=0.5,
                    factors=["Limited historical data", "Using average"]
                ))
            
            return forecasts
        
        # Create time-based features
        df['days_since_start'] = (df['date'] - df['date'].min()).dt.days
        df['day_of_week'] = df['date'].dt.dayofweek
        df['month'] = df['date'].dt.month
        
        # Train model
        X = df[['days_since_start', 'day_of_week', 'month']].values
        y = df['used'].values
        
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X, y)
        
        # Generate forecasts
        forecasts = []
        base_date = df['date'].max()
        
        for i in range(forecast_days):
            forecast_date = base_date + timedelta(days=i+1)
            days_since_start = (forecast_date - df['date'].min()).days
            
            features = [[
                days_since_start,
                forecast_date.weekday(),
                forecast_date.month
            ]]
            
            predicted = model.predict(features)[0]
            
            # Calculate confidence interval (simple approach using std)
            std = df['used'].std()
            lower = max(0, predicted - std)
            upper = predicted + std
            
            # Confidence score based on data quantity and variance
            confidence = min(0.9, len(df) / 90 * (1 - df['used'].std() / df['used'].mean()))
            
            # Identify key factors
            factors = []
            if forecast_date.weekday() in [5, 6]:
                factors.append("Weekend")
            else:
                factors.append("Weekday")
            
            # Check if there's a trend
            if len(df) > 14:
                recent_avg = df.tail(14)['used'].mean()
                older_avg = df.head(14)['used'].mean()
                if recent_avg > older_avg * 1.1:
                    factors.append("Increasing trend")
                elif recent_avg < older_avg * 0.9:
                    factors.append("Decreasing trend")
            
            forecasts.append(DemandForecast(
                ingredient_name=ingredient_name,
                forecast_date=forecast_date,
                predicted_quantity=Decimal(str(round(predicted, 2))),
                confidence_interval_lower=Decimal(str(round(lower, 2))),
                confidence_interval_upper=Decimal(str(round(upper, 2))),
                confidence_score=round(confidence, 2),
                factors=factors
            ))
        
        return forecasts


class WastePredictor:
    """Predict waste risk"""
    
    def predict_waste_risk(self, historical_data: List[NormalizedFoodDataDB], 
                          days_ahead: int) -> Dict[str, Any]:
        """
        Predict waste risk for upcoming period
        """
        # Group by ingredient
        ingredient_waste = defaultdict(list)
        
        for record in historical_data:
            total_waste = float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
            if total_waste > 0:
                ingredient_waste[record.food_item_name].append({
                    'date': record.date,
                    'waste': total_waste,
                    'prepared': float(record.food_prepared or 1)
                })
        
        predictions = {}
        
        for ingredient, waste_events in ingredient_waste.items():
            if len(waste_events) < 3:
                continue
            
            # Calculate waste rate
            waste_amounts = [w['waste'] for w in waste_events]
            waste_rates = [w['waste'] / w['prepared'] * 100 for w in waste_events]
            
            avg_waste_rate = np.mean(waste_rates)
            std_waste_rate = np.std(waste_rates)
            
            # Determine risk level
            if avg_waste_rate > 20:
                risk_level = "High"
                risk_score = 0.8
            elif avg_waste_rate > 10:
                risk_level = "Medium"
                risk_score = 0.5
            else:
                risk_level = "Low"
                risk_score = 0.2
            
            # Check if waste is increasing
            if len(waste_events) >= 6:
                recent_waste = np.mean([w['waste'] for w in waste_events[-3:]])
                older_waste = np.mean([w['waste'] for w in waste_events[:3]])
                
                if recent_waste > older_waste * 1.2:
                    trend = "Increasing"
                    risk_score = min(1.0, risk_score + 0.2)
                elif recent_waste < older_waste * 0.8:
                    trend = "Decreasing"
                    risk_score = max(0, risk_score - 0.2)
                else:
                    trend = "Stable"
            else:
                trend = "Insufficient data"
            
            predictions[ingredient] = {
                'risk_level': risk_level,
                'risk_score': round(risk_score, 2),
                'average_waste_rate': round(avg_waste_rate, 2),
                'trend': trend,
                'historical_occurrences': len(waste_events),
                'recommendation': self._generate_waste_recommendation(risk_level, trend, avg_waste_rate)
            }
        
        # Sort by risk score
        sorted_predictions = dict(sorted(predictions.items(), key=lambda x: x[1]['risk_score'], reverse=True))
        
        return {
            'forecast_period': f"Next {days_ahead} days",
            'high_risk_ingredients': [k for k, v in sorted_predictions.items() if v['risk_level'] == 'High'],
            'predictions': sorted_predictions
        }
    
    def _generate_waste_recommendation(self, risk_level: str, trend: str, waste_rate: float) -> str:
        """Generate recommendation based on waste risk"""
        if risk_level == "High":
            if trend == "Increasing":
                return f"URGENT: Waste rate is {waste_rate:.1f}% and increasing. Review preparation quantities and storage immediately."
            return f"HIGH PRIORITY: Waste rate is {waste_rate:.1f}%. Consider reducing order quantities by 20-30%."
        elif risk_level == "Medium":
            if trend == "Increasing":
                return f"ATTENTION: Waste rate is {waste_rate:.1f}% and rising. Monitor closely and adjust orders."
            return f"Moderate waste rate of {waste_rate:.1f}%. Consider reducing orders by 10-15%."
        else:
            return f"Waste rate is acceptable at {waste_rate:.1f}%. Continue monitoring."


class InsightGenerator:
    """Generate insights from data"""
    
    def generate(self, data: List[NormalizedFoodDataDB]) -> List[PredictiveInsight]:
        """
        Generate insights from data
        """
        insights = []
        
        # Waste reduction insights
        waste_insights = self._generate_waste_insights(data)
        insights.extend(waste_insights)
        
        # Ordering optimization insights
        ordering_insights = self._generate_ordering_insights(data)
        insights.extend(ordering_insights)
        
        # Demand forecast insights
        demand_insights = self._generate_demand_insights(data)
        insights.extend(demand_insights)
        
        # Cost saving insights
        cost_insights = self._generate_cost_insights(data)
        insights.extend(cost_insights)
        
        return insights
    
    def _generate_waste_insights(self, data: List[NormalizedFoodDataDB]) -> List[PredictiveInsight]:
        """Generate waste-related insights"""
        insights = []
        
        # Find top wasted items
        waste_by_item = defaultdict(float)
        for record in data:
            total_waste = float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
            waste_by_item[record.food_item_name] += total_waste
        
        # Get top 5 wasted items
        top_wasted = sorted(waste_by_item.items(), key=lambda x: x[1], reverse=True)[:5]
        
        for item, waste_amount in top_wasted:
            if waste_amount > 10:  # Significant waste
                insights.append(PredictiveInsight(
                    insight_type="waste_reduction",
                    priority="high" if waste_amount > 50 else "medium",
                    title=f"High Waste Detected: {item}",
                    description=f"{item} has generated {waste_amount:.1f} lbs of waste in the analyzed period.",
                    recommendation=f"Review preparation procedures for {item}. Consider reducing batch sizes or adjusting recipes.",
                    expected_impact={
                        "waste_reduction_lb": round(waste_amount * 0.3, 2),
                        "cost_savings_estimate": round(waste_amount * 0.3 * 5, 2)  # $5/lb estimate
                    },
                    confidence_score=0.85,
                    based_on_data_points=len([d for d in data if d.food_item_name == item]),
                    relevant_ingredients=[item],
                    relevant_locations=list(set(d.location for d in data if d.food_item_name == item)),
                    relevant_meal_periods=list(set(d.meal_period for d in data if d.food_item_name == item))
                ))
        
        return insights
    
    def _generate_ordering_insights(self, data: List[NormalizedFoodDataDB]) -> List[PredictiveInsight]:
        """Generate ordering optimization insights"""
        insights = []
        
        # Find items with poor ordering accuracy
        ordering_accuracy = {}
        for item in set(d.food_item_name for d in data):
            item_data = [d for d in data if d.food_item_name == item and d.food_ordered and d.food_used]
            
            if len(item_data) < 3:
                continue
            
            accuracies = []
            for record in item_data:
                ordered = float(record.food_ordered)
                used = float(record.food_used)
                if ordered > 0:
                    accuracy = min(used, ordered) / ordered
                    accuracies.append(accuracy)
            
            if accuracies:
                ordering_accuracy[item] = np.mean(accuracies)
        
        # Find items with low accuracy
        for item, accuracy in ordering_accuracy.items():
            if accuracy < 0.7:  # Less than 70% accuracy
                avg_ordered = np.mean([float(d.food_ordered or 0) for d in data if d.food_item_name == item and d.food_ordered])
                avg_used = np.mean([float(d.food_used or 0) for d in data if d.food_item_name == item and d.food_used])
                
                difference = avg_ordered - avg_used
                
                if difference > 0:
                    insights.append(PredictiveInsight(
                        insight_type="ordering_optimization",
                        priority="medium",
                        title=f"Over-ordering Detected: {item}",
                        description=f"{item} is being consistently over-ordered. Average accuracy is {accuracy*100:.1f}%.",
                        recommendation=f"Reduce {item} orders by approximately {difference:.1f} units to match actual usage.",
                        expected_impact={
                            "waste_reduction_lb": round(difference, 2),
                            "accuracy_improvement": round((1 - accuracy) * 100, 2)
                        },
                        confidence_score=0.75,
                        based_on_data_points=len([d for d in data if d.food_item_name == item]),
                        relevant_ingredients=[item]
                    ))
        
        return insights
    
    def _generate_demand_insights(self, data: List[NormalizedFoodDataDB]) -> List[PredictiveInsight]:
        """Generate demand forecast insights"""
        insights = []
        
        # Analyze trends
        df_data = []
        for record in data:
            df_data.append({
                'date': record.date,
                'item': record.food_item_name,
                'used': float(record.food_used or 0)
            })
        
        df = pd.DataFrame(df_data)
        
        for item in df['item'].unique():
            item_df = df[df['item'] == item].sort_values('date')
            
            if len(item_df) < 14:
                continue
            
            # Compare recent to older usage
            recent_usage = item_df.tail(7)['used'].mean()
            older_usage = item_df.head(7)['used'].mean()
            
            if recent_usage > older_usage * 1.3:  # 30% increase
                insights.append(PredictiveInsight(
                    insight_type="demand_forecast",
                    priority="medium",
                    title=f"Increasing Demand: {item}",
                    description=f"Usage of {item} has increased by {((recent_usage/older_usage - 1) * 100):.1f}% recently.",
                    recommendation=f"Consider increasing {item} orders to meet growing demand. Forecast suggests {recent_usage:.1f} units/day.",
                    expected_impact={
                        "demand_increase_percent": round((recent_usage/older_usage - 1) * 100, 2),
                        "recommended_daily_order": round(recent_usage, 2)
                    },
                    confidence_score=0.7,
                    based_on_data_points=len(item_df),
                    relevant_ingredients=[item]
                ))
        
        return insights
    
    def _generate_cost_insights(self, data: List[NormalizedFoodDataDB]) -> List[PredictiveInsight]:
        """Generate cost-related insights"""
        insights = []
        
        # Calculate potential savings from waste reduction
        total_waste = sum(float((d.food_wasted_boh or 0) + (d.food_wasted_foh or 0)) for d in data)
        
        if total_waste > 100:  # Significant total waste
            estimated_savings = total_waste * 5  # $5/lb estimate
            
            insights.append(PredictiveInsight(
                insight_type="cost_savings",
                priority="high",
                title="Significant Cost Savings Opportunity",
                description=f"Total waste of {total_waste:.1f} lbs detected. This represents approximately ${estimated_savings:.2f} in lost value.",
                recommendation="Implement waste reduction strategies across all high-waste items. A 30% reduction would save approximately ${:.2f}".format(estimated_savings * 0.3),
                expected_impact={
                    "total_waste_lb": round(total_waste, 2),
                    "estimated_cost": round(estimated_savings, 2),
                    "potential_savings_30_percent": round(estimated_savings * 0.3, 2)
                },
                confidence_score=0.8,
                based_on_data_points=len(data),
                relevant_ingredients=[],
                relevant_locations=list(set(d.location for d in data))
            ))
        
        return insights
    
    def analyze_trends(self, data: List[NormalizedFoodDataDB]) -> Dict[str, Any]:
        """Analyze trends in the data"""
        trends = {
            'overall': {},
            'by_ingredient': {},
            'by_location': {}
        }
        
        if not data:
            return trends
        
        # Overall trends
        df_data = []
        for record in data:
            df_data.append({
                'date': record.date,
                'prepared': float(record.food_prepared or 0),
                'used': float(record.food_used or 0),
                'wasted': float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
            })
        
        df = pd.DataFrame(df_data)
        df = df.groupby('date').sum().reset_index()
        df = df.sort_values('date')
        
        if len(df) >= 7:
            recent = df.tail(7)
            older = df.head(7)
            
            trends['overall'] = {
                'prepared_trend': 'increasing' if recent['prepared'].mean() > older['prepared'].mean() else 'decreasing',
                'waste_trend': 'increasing' if recent['wasted'].mean() > older['wasted'].mean() else 'decreasing',
                'recent_waste_rate': round(recent['wasted'].sum() / recent['prepared'].sum() * 100, 2) if recent['prepared'].sum() > 0 else 0
            }
        
        return trends


class RecommendationEngine:
    """Generate actionable recommendations"""
    
    def generate_waste_recommendations(self, data: List[NormalizedFoodDataDB]) -> List[Dict[str, Any]]:
        """Generate waste reduction recommendations"""
        recommendations = []
        
        # Analyze waste by location
        waste_by_location = defaultdict(lambda: defaultdict(float))
        
        for record in data:
            total_waste = float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
            if total_waste > 0:
                waste_by_location[record.location][record.food_item_name] += total_waste
        
        for location, items in waste_by_location.items():
            top_wasted = sorted(items.items(), key=lambda x: x[1], reverse=True)[:3]
            
            for item, waste in top_wasted:
                recommendations.append({
                    'location': location,
                    'ingredient': item,
                    'waste_amount': round(waste, 2),
                    'recommendation': f"At {location}, reduce {item} preparation by 20-30%",
                    'priority': 'high' if waste > 20 else 'medium',
                    'estimated_savings': round(waste * 0.3 * 5, 2)
                })
        
        return recommendations
    
    def generate_ordering_recommendations(self, data: List[NormalizedFoodDataDB]) -> List[Dict[str, Any]]:
        """Generate ordering optimization recommendations"""
        recommendations = []
        
        # Analyze ordering patterns
        ingredient_stats = defaultdict(lambda: {'ordered': [], 'used': []})
        
        for record in data:
            if record.food_ordered and record.food_used:
                ingredient_stats[record.food_item_name]['ordered'].append(float(record.food_ordered))
                ingredient_stats[record.food_item_name]['used'].append(float(record.food_used))
        
        for ingredient, stats in ingredient_stats.items():
            if len(stats['ordered']) < 3:
                continue
            
            avg_ordered = np.mean(stats['ordered'])
            avg_used = np.mean(stats['used'])
            
            if abs(avg_ordered - avg_used) > avg_ordered * 0.15:  # 15% difference
                if avg_ordered > avg_used:
                    action = "reduce"
                    amount = avg_ordered - avg_used
                else:
                    action = "increase"
                    amount = avg_used - avg_ordered
                
                recommendations.append({
                    'ingredient': ingredient,
                    'current_avg_order': round(avg_ordered, 2),
                    'actual_avg_usage': round(avg_used, 2),
                    'recommendation': f"{action.capitalize()} {ingredient} orders by {amount:.1f} units",
                    'priority': 'medium',
                    'action': action
                })
        
        return recommendations
