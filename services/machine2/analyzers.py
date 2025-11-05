"""
Statistical analyzers for Machine 2
"""
import numpy as np
import pandas as pd
from scipy import stats
from collections import defaultdict
from typing import List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
import sys
sys.path.append('/workspace')

from shared.models import (
    EventStatistics, IngredientUsagePattern, BEOComparisonAnalysis,
    MealPeriod, WastePattern
)
from shared.database import NormalizedFoodDataDB


class EventAnalyzer:
    """Analyze events and generate statistics"""
    
    def analyze(self, data: List[NormalizedFoodDataDB], start_date: date, end_date: date) -> EventStatistics:
        """
        Analyze events within a date range
        """
        # Count unique events
        events = set()
        for record in data:
            if record.event_name:
                events.add(f"{record.date}_{record.event_name}")
        
        total_events = len(events)
        total_orders = len(data)
        
        # Guest statistics
        total_guests = sum(record.final_guest_count or 0 for record in data)
        avg_guests = total_guests / total_events if total_events > 0 else 0
        
        # Food statistics by ingredient
        food_prepared = defaultdict(Decimal)
        food_used = defaultdict(Decimal)
        food_wasted = defaultdict(Decimal)
        
        for record in data:
            item = record.food_item_name
            food_prepared[item] += Decimal(str(record.food_prepared or 0))
            food_used[item] += Decimal(str(record.food_used or 0))
            food_wasted[item] += Decimal(str((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0)))
        
        # Calculate percentages
        total_prepared_sum = sum(food_prepared.values())
        total_wasted_sum = sum(food_wasted.values())
        
        waste_percentage = float(total_wasted_sum / total_prepared_sum * 100) if total_prepared_sum > 0 else 0
        
        # Calculate accuracy (ordered vs used)
        accuracy_rate = 0
        count = 0
        for record in data:
            if record.food_ordered and record.food_used:
                ordered = float(record.food_ordered)
                used = float(record.food_used)
                if ordered > 0:
                    accuracy = min(used, ordered) / ordered
                    accuracy_rate += accuracy
                    count += 1
        
        accuracy_rate = (accuracy_rate / count * 100) if count > 0 else 0
        
        return EventStatistics(
            date_range_start=start_date,
            date_range_end=end_date,
            total_events=total_events,
            total_orders=total_orders,
            total_guests=total_guests,
            average_guests_per_event=round(avg_guests, 1),
            total_food_prepared={k: v for k, v in food_prepared.items()},
            total_food_used={k: v for k, v in food_used.items()},
            total_food_wasted={k: v for k, v in food_wasted.items()},
            waste_percentage=round(waste_percentage, 2),
            accuracy_rate=round(accuracy_rate, 2)
        )


class IngredientAnalyzer:
    """Analyze ingredient usage patterns"""
    
    def analyze(self, ingredient_name: str, data: List[NormalizedFoodDataDB], 
                start_date: date, end_date: date) -> IngredientUsagePattern:
        """
        Analyze usage patterns for a specific ingredient
        """
        # Aggregate totals
        total_ordered = sum(Decimal(str(record.food_ordered or 0)) for record in data)
        total_prepared = sum(Decimal(str(record.food_prepared or 0)) for record in data)
        total_used = sum(Decimal(str(record.food_used or 0)) for record in data)
        total_wasted = sum(Decimal(str((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))) for record in data)
        
        waste_percentage = float(total_wasted / total_prepared * 100) if total_prepared > 0 else 0
        
        # Usage by meal period
        usage_by_meal = defaultdict(Decimal)
        for record in data:
            usage_by_meal[MealPeriod(record.meal_period)] += Decimal(str(record.food_used or 0))
        
        # Usage by location
        usage_by_location = defaultdict(Decimal)
        for record in data:
            usage_by_location[record.location] += Decimal(str(record.food_used or 0))
        
        # Peak usage days
        usage_by_day = defaultdict(Decimal)
        for record in data:
            usage_by_day[record.date.isoformat()] += Decimal(str(record.food_used or 0))
        
        # Get top 5 days
        peak_days = sorted(usage_by_day.items(), key=lambda x: x[1], reverse=True)[:5]
        peak_usage_days = [day for day, _ in peak_days]
        
        time_period = f"{start_date} to {end_date}"
        
        return IngredientUsagePattern(
            ingredient_name=ingredient_name,
            time_period=time_period,
            total_ordered=total_ordered,
            total_prepared=total_prepared,
            total_used=total_used,
            total_wasted=total_wasted,
            waste_percentage=round(waste_percentage, 2),
            usage_by_meal_period=dict(usage_by_meal),
            usage_by_location=dict(usage_by_location),
            peak_usage_days=peak_usage_days
        )


class BEOComparator:
    """Compare BEOs to detect changes"""
    
    def compare(self, beo_data: List[NormalizedFoodDataDB]) -> List[BEOComparisonAnalysis]:
        """
        Compare multiple BEOs for the same event to detect changes
        """
        # Group by event
        events = defaultdict(list)
        for record in beo_data:
            if record.event_name:
                events[record.event_name].append(record)
        
        comparisons = []
        
        for event_name, records in events.items():
            if len(records) < 2:
                continue
            
            # Sort by created_at to get original and revised
            records.sort(key=lambda x: x.created_at)
            original = records[0]
            revised = records[-1]
            
            # Calculate variances
            guest_variance = (revised.final_guest_count or 0) - (original.original_guest_count or 0)
            
            # Food item changes
            food_changes = {}
            original_items = {r.food_item_name: r for r in records if r.created_at == original.created_at}
            revised_items = {r.food_item_name: r for r in records if r.created_at == revised.created_at}
            
            all_items = set(original_items.keys()) | set(revised_items.keys())
            
            for item in all_items:
                orig = original_items.get(item)
                rev = revised_items.get(item)
                
                if orig and rev:
                    orig_qty = float(orig.food_ordered or 0)
                    rev_qty = float(rev.food_ordered or 0)
                    change = rev_qty - orig_qty
                    
                    if abs(change) > 0.01:
                        food_changes[item] = {
                            "original_quantity": orig_qty,
                            "revised_quantity": rev_qty,
                            "change": change,
                            "percent_change": (change / orig_qty * 100) if orig_qty > 0 else 0
                        }
                elif orig and not rev:
                    food_changes[item] = {
                        "original_quantity": float(orig.food_ordered or 0),
                        "revised_quantity": 0,
                        "change": -float(orig.food_ordered or 0),
                        "status": "removed"
                    }
                elif rev and not orig:
                    food_changes[item] = {
                        "original_quantity": 0,
                        "revised_quantity": float(rev.food_ordered or 0),
                        "change": float(rev.food_ordered or 0),
                        "status": "added"
                    }
            
            # Estimate waste impact (if available)
            impact_on_waste = None
            if revised.food_wasted_boh or revised.food_wasted_foh:
                impact_on_waste = Decimal(str((revised.food_wasted_boh or 0) + (revised.food_wasted_foh or 0)))
            
            comparison = BEOComparisonAnalysis(
                event_id=event_name,
                original_beo_date=original.created_at,
                revised_beo_date=revised.created_at,
                guest_count_variance=guest_variance,
                food_item_changes=food_changes,
                impact_on_waste=impact_on_waste,
                cost_impact=None  # Could be calculated if price data available
            )
            
            comparisons.append(comparison)
        
        return comparisons


class PatternDetector:
    """Detect various patterns in the data"""
    
    def detect_waste_patterns(self, data: List[NormalizedFoodDataDB]) -> List[Dict[str, Any]]:
        """
        Detect waste patterns
        """
        # Group waste by ingredient
        waste_by_ingredient = defaultdict(list)
        
        for record in data:
            total_waste = float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
            if total_waste > 0:
                waste_by_ingredient[record.food_item_name].append({
                    'date': record.date,
                    'amount': total_waste,
                    'location': record.location,
                    'meal_period': record.meal_period
                })
        
        patterns = []
        
        for ingredient, waste_events in waste_by_ingredient.items():
            if len(waste_events) < 3:
                continue
            
            amounts = [w['amount'] for w in waste_events]
            avg_waste = np.mean(amounts)
            std_waste = np.std(amounts)
            
            # Determine frequency
            days_span = (max(w['date'] for w in waste_events) - min(w['date'] for w in waste_events)).days
            frequency = len(waste_events) / max(days_span, 1) * 7  # per week
            
            # Determine if this is a recurring pattern
            if frequency > 0.5:  # More than twice per week
                frequency_desc = "High frequency"
            elif frequency > 0.2:
                frequency_desc = "Regular occurrence"
            else:
                frequency_desc = "Occasional"
            
            # Identify common factors
            locations = [w['location'] for w in waste_events]
            most_common_location = max(set(locations), key=locations.count)
            
            meal_periods = [w['meal_period'] for w in waste_events]
            most_common_meal = max(set(meal_periods), key=meal_periods.count)
            
            patterns.append({
                'ingredient': ingredient,
                'average_waste_amount': round(avg_waste, 2),
                'std_deviation': round(std_waste, 2),
                'frequency': frequency_desc,
                'occurrences': len(waste_events),
                'most_common_location': most_common_location,
                'most_common_meal_period': most_common_meal,
                'total_waste': round(sum(amounts), 2),
                'hypothesis': self._generate_waste_hypothesis(avg_waste, frequency_desc, most_common_location)
            })
        
        # Sort by total waste
        patterns.sort(key=lambda x: x['total_waste'], reverse=True)
        
        return patterns
    
    def _generate_waste_hypothesis(self, avg_waste: float, frequency: str, location: str) -> str:
        """Generate a hypothesis about waste cause"""
        if avg_waste > 10:
            return f"Large quantities being wasted - possible over-ordering or portion size issues at {location}"
        elif frequency == "High frequency":
            return f"Consistent waste pattern - may indicate preparation issues or unpopular menu item at {location}"
        else:
            return f"Occasional waste - could be related to specific events or fluctuating demand at {location}"
    
    def detect_ordering_patterns(self, data: List[NormalizedFoodDataDB]) -> List[Dict[str, Any]]:
        """
        Detect ordering accuracy patterns
        """
        # Group by ingredient
        ingredient_data = defaultdict(list)
        
        for record in data:
            if record.food_ordered and record.food_used:
                ingredient_data[record.food_item_name].append({
                    'ordered': float(record.food_ordered),
                    'used': float(record.food_used),
                    'date': record.date
                })
        
        patterns = []
        
        for ingredient, records in ingredient_data.items():
            if len(records) < 3:
                continue
            
            ordered_amounts = [r['ordered'] for r in records]
            used_amounts = [r['used'] for r in records]
            
            # Calculate accuracy
            accuracies = [min(u, o) / o * 100 if o > 0 else 0 for o, u in zip(ordered_amounts, used_amounts)]
            avg_accuracy = np.mean(accuracies)
            
            # Calculate over/under ordering tendency
            differences = [u - o for o, u in zip(ordered_amounts, used_amounts)]
            avg_difference = np.mean(differences)
            
            if avg_difference > 0:
                tendency = "Under-ordering"
                recommendation = f"Consider increasing orders by approximately {abs(avg_difference):.1f} units"
            elif avg_difference < -1:
                tendency = "Over-ordering"
                recommendation = f"Consider reducing orders by approximately {abs(avg_difference):.1f} units"
            else:
                tendency = "Well-calibrated"
                recommendation = "Current ordering levels are appropriate"
            
            patterns.append({
                'ingredient': ingredient,
                'average_accuracy': round(avg_accuracy, 2),
                'tendency': tendency,
                'average_difference': round(avg_difference, 2),
                'recommendation': recommendation,
                'sample_size': len(records)
            })
        
        return patterns
    
    def detect_seasonal_patterns(self, data: List[NormalizedFoodDataDB]) -> Dict[str, Any]:
        """
        Detect seasonal usage patterns
        """
        if not data:
            return {"message": "Insufficient data for seasonal analysis"}
        
        # Convert to DataFrame for easier time series analysis
        df_data = []
        for record in data:
            df_data.append({
                'date': record.date,
                'ingredient': record.food_item_name,
                'used': float(record.food_used or 0),
                'month': record.date.month,
                'day_of_week': record.date.weekday()
            })
        
        df = pd.DataFrame(df_data)
        
        # Monthly patterns
        monthly_usage = df.groupby(['ingredient', 'month'])['used'].sum().reset_index()
        
        # Day of week patterns
        dow_usage = df.groupby(['ingredient', 'day_of_week'])['used'].mean().reset_index()
        
        patterns = {
            'monthly_patterns': {},
            'day_of_week_patterns': {},
            'insights': []
        }
        
        # Analyze monthly patterns
        for ingredient in df['ingredient'].unique():
            ingredient_monthly = monthly_usage[monthly_usage['ingredient'] == ingredient]
            
            if len(ingredient_monthly) >= 3:
                months = ingredient_monthly['month'].values
                usage = ingredient_monthly['used'].values
                
                # Find peak month
                peak_month = months[np.argmax(usage)]
                peak_usage = np.max(usage)
                
                patterns['monthly_patterns'][ingredient] = {
                    'peak_month': int(peak_month),
                    'peak_usage': float(peak_usage),
                    'monthly_data': dict(zip(map(int, months), map(float, usage)))
                }
        
        # Analyze day of week patterns
        for ingredient in df['ingredient'].unique():
            ingredient_dow = dow_usage[dow_usage['ingredient'] == ingredient]
            
            if len(ingredient_dow) >= 3:
                days = ingredient_dow['day_of_week'].values
                usage = ingredient_dow['used'].values
                
                # Find peak day
                peak_day = days[np.argmax(usage)]
                peak_usage = np.max(usage)
                
                day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                patterns['day_of_week_patterns'][ingredient] = {
                    'peak_day': day_names[peak_day],
                    'peak_usage': float(peak_usage),
                    'daily_data': dict(zip([day_names[d] for d in days], map(float, usage)))
                }
        
        return patterns
