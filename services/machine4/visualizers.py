"""
Chart and report generators for Machine 4
"""
import plotly.graph_objects as go
import plotly.express as px
from collections import defaultdict
from typing import List, Dict, Any
from datetime import date
import pandas as pd
import sys
sys.path.append('/workspace')

from shared.models import ChartData, DashboardFilter
from shared.database import NormalizedFoodDataDB


class ChartGenerator:
    """Generate chart data for visualization"""
    
    def generate_waste_overview(self, data: List[NormalizedFoodDataDB]) -> ChartData:
        """
        Generate waste overview pie chart
        """
        waste_by_item = defaultdict(float)
        
        for record in data:
            total_waste = float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
            if total_waste > 0:
                waste_by_item[record.food_item_name] += total_waste
        
        # Get top 10 and group rest as "Other"
        sorted_waste = sorted(waste_by_item.items(), key=lambda x: x[1], reverse=True)
        top_items = sorted_waste[:10]
        other_waste = sum(w for _, w in sorted_waste[10:])
        
        labels = [item for item, _ in top_items]
        values = [waste for _, waste in top_items]
        
        if other_waste > 0:
            labels.append("Other")
            values.append(other_waste)
        
        chart_data = {
            "labels": labels,
            "values": [round(v, 2) for v in values],
            "type": "pie"
        }
        
        return ChartData(
            chart_type="pie",
            title="Waste Distribution by Ingredient",
            data=chart_data,
            options={"unit": "lbs"}
        )
    
    def generate_ingredient_usage(self, data: List[NormalizedFoodDataDB]) -> ChartData:
        """
        Generate ingredient usage bar chart
        """
        usage_by_item = defaultdict(lambda: {"ordered": 0, "prepared": 0, "used": 0, "wasted": 0})
        
        for record in data:
            item = record.food_item_name
            usage_by_item[item]["ordered"] += float(record.food_ordered or 0)
            usage_by_item[item]["prepared"] += float(record.food_prepared or 0)
            usage_by_item[item]["used"] += float(record.food_used or 0)
            usage_by_item[item]["wasted"] += float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
        
        # Get top 15 ingredients by usage
        sorted_items = sorted(usage_by_item.items(), key=lambda x: x[1]["used"], reverse=True)[:15]
        
        ingredients = [item for item, _ in sorted_items]
        ordered = [round(stats["ordered"], 2) for _, stats in sorted_items]
        prepared = [round(stats["prepared"], 2) for _, stats in sorted_items]
        used = [round(stats["used"], 2) for _, stats in sorted_items]
        wasted = [round(stats["wasted"], 2) for _, stats in sorted_items]
        
        chart_data = {
            "ingredients": ingredients,
            "ordered": ordered,
            "prepared": prepared,
            "used": used,
            "wasted": wasted
        }
        
        return ChartData(
            chart_type="bar",
            title="Ingredient Usage Breakdown",
            data=chart_data,
            options={"orientation": "v", "barmode": "group"}
        )
    
    def generate_timeline(self, data: List[NormalizedFoodDataDB]) -> ChartData:
        """
        Generate timeline chart showing trends
        """
        daily_stats = defaultdict(lambda: {"prepared": 0, "used": 0, "wasted": 0})
        
        for record in data:
            date_str = record.date.isoformat()
            daily_stats[date_str]["prepared"] += float(record.food_prepared or 0)
            daily_stats[date_str]["used"] += float(record.food_used or 0)
            daily_stats[date_str]["wasted"] += float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
        
        # Sort by date
        sorted_dates = sorted(daily_stats.keys())
        
        dates = sorted_dates
        prepared = [round(daily_stats[d]["prepared"], 2) for d in sorted_dates]
        used = [round(daily_stats[d]["used"], 2) for d in sorted_dates]
        wasted = [round(daily_stats[d]["wasted"], 2) for d in sorted_dates]
        
        chart_data = {
            "dates": dates,
            "prepared": prepared,
            "used": used,
            "wasted": wasted
        }
        
        return ChartData(
            chart_type="line",
            title="Usage Timeline",
            data=chart_data,
            options={"xaxis_title": "Date", "yaxis_title": "Amount (lbs)"}
        )
    
    def generate_location_comparison(self, data: List[NormalizedFoodDataDB]) -> ChartData:
        """
        Compare metrics across locations
        """
        location_stats = defaultdict(lambda: {"prepared": 0, "used": 0, "wasted": 0, "waste_pct": 0})
        
        for record in data:
            loc = record.location
            location_stats[loc]["prepared"] += float(record.food_prepared or 0)
            location_stats[loc]["used"] += float(record.food_used or 0)
            location_stats[loc]["wasted"] += float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
        
        # Calculate waste percentages
        for loc, stats in location_stats.items():
            if stats["prepared"] > 0:
                stats["waste_pct"] = (stats["wasted"] / stats["prepared"]) * 100
        
        locations = list(location_stats.keys())
        prepared = [round(location_stats[loc]["prepared"], 2) for loc in locations]
        used = [round(location_stats[loc]["used"], 2) for loc in locations]
        wasted = [round(location_stats[loc]["wasted"], 2) for loc in locations]
        waste_pct = [round(location_stats[loc]["waste_pct"], 2) for loc in locations]
        
        chart_data = {
            "locations": locations,
            "prepared": prepared,
            "used": used,
            "wasted": wasted,
            "waste_percentage": waste_pct
        }
        
        return ChartData(
            chart_type="bar",
            title="Location Comparison",
            data=chart_data,
            options={"orientation": "v"}
        )
    
    def generate_meal_period_breakdown(self, data: List[NormalizedFoodDataDB]) -> ChartData:
        """
        Break down usage by meal period
        """
        meal_stats = defaultdict(lambda: {"prepared": 0, "used": 0, "wasted": 0})
        
        for record in data:
            meal = record.meal_period
            meal_stats[meal]["prepared"] += float(record.food_prepared or 0)
            meal_stats[meal]["used"] += float(record.food_used or 0)
            meal_stats[meal]["wasted"] += float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
        
        meals = list(meal_stats.keys())
        prepared = [round(meal_stats[m]["prepared"], 2) for m in meals]
        used = [round(meal_stats[m]["used"], 2) for m in meals]
        wasted = [round(meal_stats[m]["wasted"], 2) for m in meals]
        
        chart_data = {
            "meal_periods": meals,
            "prepared": prepared,
            "used": used,
            "wasted": wasted
        }
        
        return ChartData(
            chart_type="bar",
            title="Usage by Meal Period",
            data=chart_data,
            options={"orientation": "v", "barmode": "group"}
        )
    
    def generate_accuracy_chart(self, data: List[NormalizedFoodDataDB]) -> ChartData:
        """
        Show ordering accuracy over time
        """
        daily_accuracy = defaultdict(list)
        
        for record in data:
            if record.food_ordered and record.food_used:
                ordered = float(record.food_ordered)
                used = float(record.food_used)
                if ordered > 0:
                    accuracy = min(used, ordered) / ordered * 100
                    daily_accuracy[record.date.isoformat()].append(accuracy)
        
        # Calculate average accuracy per day
        dates = sorted(daily_accuracy.keys())
        accuracies = [round(sum(daily_accuracy[d]) / len(daily_accuracy[d]), 2) for d in dates]
        
        chart_data = {
            "dates": dates,
            "accuracy": accuracies
        }
        
        return ChartData(
            chart_type="line",
            title="Ordering Accuracy Over Time",
            data=chart_data,
            options={"xaxis_title": "Date", "yaxis_title": "Accuracy (%)"}
        )


class ReportGenerator:
    """Generate comprehensive reports"""
    
    def generate_report(self, data: List[NormalizedFoodDataDB], report_type: str, 
                       filters: DashboardFilter) -> Dict[str, Any]:
        """
        Generate a comprehensive report
        """
        if report_type == "comprehensive":
            return self._generate_comprehensive_report(data, filters)
        elif report_type == "waste":
            return self._generate_waste_report(data, filters)
        elif report_type == "ordering":
            return self._generate_ordering_report(data, filters)
        else:
            return self._generate_comprehensive_report(data, filters)
    
    def _generate_comprehensive_report(self, data: List[NormalizedFoodDataDB], 
                                      filters: DashboardFilter) -> Dict[str, Any]:
        """Generate comprehensive report"""
        report = {
            "report_type": "Comprehensive Food Service Report",
            "filters": {
                "date_range": f"{filters.start_date} to {filters.end_date}" if filters.start_date and filters.end_date else "All dates",
                "location": filters.location or "All locations",
                "ingredient": filters.ingredient or "All ingredients"
            },
            "summary": {},
            "waste_analysis": {},
            "ordering_analysis": {},
            "top_items": {},
            "recommendations": []
        }
        
        # Summary statistics
        total_prepared = sum(float(d.food_prepared or 0) for d in data)
        total_used = sum(float(d.food_used or 0) for d in data)
        total_wasted = sum(float((d.food_wasted_boh or 0) + (d.food_wasted_foh or 0)) for d in data)
        
        report["summary"] = {
            "total_events": len(set(f"{d.date}_{d.event_name}" for d in data if d.event_name)),
            "total_records": len(data),
            "total_prepared_lb": round(total_prepared, 2),
            "total_used_lb": round(total_used, 2),
            "total_wasted_lb": round(total_wasted, 2),
            "waste_percentage": round((total_wasted / total_prepared * 100) if total_prepared > 0 else 0, 2)
        }
        
        # Waste analysis
        waste_by_item = defaultdict(float)
        for record in data:
            total_waste = float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
            if total_waste > 0:
                waste_by_item[record.food_item_name] += total_waste
        
        top_wasted = sorted(waste_by_item.items(), key=lambda x: x[1], reverse=True)[:10]
        
        report["waste_analysis"] = {
            "top_wasted_items": [
                {"item": item, "waste_lb": round(waste, 2)} for item, waste in top_wasted
            ]
        }
        
        # Ordering analysis
        ordering_accuracy = {}
        for item in set(d.food_item_name for d in data):
            item_data = [d for d in data if d.food_item_name == item and d.food_ordered and d.food_used]
            
            if len(item_data) >= 3:
                accuracies = []
                for record in item_data:
                    ordered = float(record.food_ordered)
                    used = float(record.food_used)
                    if ordered > 0:
                        accuracy = min(used, ordered) / ordered * 100
                        accuracies.append(accuracy)
                
                if accuracies:
                    ordering_accuracy[item] = sum(accuracies) / len(accuracies)
        
        low_accuracy_items = [(item, acc) for item, acc in ordering_accuracy.items() if acc < 70]
        low_accuracy_items.sort(key=lambda x: x[1])
        
        report["ordering_analysis"] = {
            "average_accuracy": round(sum(ordering_accuracy.values()) / len(ordering_accuracy) if ordering_accuracy else 0, 2),
            "low_accuracy_items": [
                {"item": item, "accuracy": round(acc, 2)} for item, acc in low_accuracy_items[:10]
            ]
        }
        
        # Generate recommendations
        if report["summary"]["waste_percentage"] > 15:
            report["recommendations"].append("HIGH PRIORITY: Waste percentage exceeds 15%. Implement waste reduction strategies immediately.")
        
        for item, waste in top_wasted[:3]:
            report["recommendations"].append(f"Reduce preparation of {item} - currently wasting {waste:.1f} lbs")
        
        return report
    
    def _generate_waste_report(self, data: List[NormalizedFoodDataDB], 
                               filters: DashboardFilter) -> Dict[str, Any]:
        """Generate waste-focused report"""
        waste_by_item = defaultdict(lambda: {"boh": 0, "foh": 0, "total": 0})
        
        for record in data:
            item = record.food_item_name
            waste_by_item[item]["boh"] += float(record.food_wasted_boh or 0)
            waste_by_item[item]["foh"] += float(record.food_wasted_foh or 0)
            waste_by_item[item]["total"] += float((record.food_wasted_boh or 0) + (record.food_wasted_foh or 0))
        
        sorted_waste = sorted(waste_by_item.items(), key=lambda x: x[1]["total"], reverse=True)
        
        return {
            "report_type": "Waste Analysis Report",
            "total_waste_lb": round(sum(w["total"] for _, w in waste_by_item.items()), 2),
            "items": [
                {
                    "ingredient": item,
                    "boh_waste_lb": round(waste["boh"], 2),
                    "foh_waste_lb": round(waste["foh"], 2),
                    "total_waste_lb": round(waste["total"], 2)
                } for item, waste in sorted_waste
            ]
        }
    
    def _generate_ordering_report(self, data: List[NormalizedFoodDataDB], 
                                  filters: DashboardFilter) -> Dict[str, Any]:
        """Generate ordering-focused report"""
        ordering_stats = defaultdict(lambda: {"ordered": [], "used": []})
        
        for record in data:
            if record.food_ordered and record.food_used:
                ordering_stats[record.food_item_name]["ordered"].append(float(record.food_ordered))
                ordering_stats[record.food_item_name]["used"].append(float(record.food_used))
        
        report_items = []
        for item, stats in ordering_stats.items():
            if len(stats["ordered"]) < 2:
                continue
            
            avg_ordered = sum(stats["ordered"]) / len(stats["ordered"])
            avg_used = sum(stats["used"]) / len(stats["used"])
            
            accuracies = [min(u, o) / o * 100 if o > 0 else 0 for o, u in zip(stats["ordered"], stats["used"])]
            avg_accuracy = sum(accuracies) / len(accuracies)
            
            report_items.append({
                "ingredient": item,
                "avg_ordered": round(avg_ordered, 2),
                "avg_used": round(avg_used, 2),
                "difference": round(avg_ordered - avg_used, 2),
                "accuracy": round(avg_accuracy, 2)
            })
        
        report_items.sort(key=lambda x: abs(x["difference"]), reverse=True)
        
        return {
            "report_type": "Ordering Analysis Report",
            "items": report_items
        }
