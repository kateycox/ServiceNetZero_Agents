"""
Carbon footprint calculators for Machine 5
"""
from typing import List, Dict, Any
from datetime import date
from decimal import Decimal
from collections import defaultdict
import sys
sys.path.append('/workspace')

from shared.models import (
    MenuItemCarbon, CarbonFootprintReport, WasteType
)
from shared.database import (
    WasteDataDB, UtilityDataDB, DeliveryDataDB, NormalizedFoodDataDB
)


class CarbonCalculator:
    """Main carbon footprint calculator"""
    
    # Carbon emission factors (kg CO2e per unit)
    ELECTRICITY_FACTOR = 0.92  # kg CO2e per kWh (US average)
    GAS_FACTOR = 5.3  # kg CO2e per therm
    WATER_FACTOR = 0.0003  # kg CO2e per gallon
    DELIVERY_FACTOR = 0.4  # kg CO2e per mile (average truck)
    
    def generate_report(
        self,
        waste_data: List[WasteDataDB],
        utility_data: List[UtilityDataDB],
        delivery_data: List[DeliveryDataDB],
        food_data: List[NormalizedFoodDataDB],
        start_date: date,
        end_date: date
    ) -> CarbonFootprintReport:
        """
        Generate comprehensive carbon footprint report
        """
        # Calculate carbon from waste
        waste_calculator = WasteCalculator()
        carbon_from_waste = waste_calculator.calculate_total_carbon(waste_data)
        
        # Calculate carbon from utilities
        carbon_from_utilities = self._calculate_utility_carbon(utility_data)
        
        # Calculate carbon from deliveries
        carbon_from_deliveries = self._calculate_delivery_carbon(delivery_data)
        
        # Calculate carbon from food
        menu_calculator = MenuItemCarbonCalculator()
        carbon_from_food = menu_calculator.calculate_total_food_carbon(food_data)
        
        # Breakdown by location
        breakdown_by_location = self._calculate_location_breakdown(
            waste_data, utility_data, delivery_data, food_data
        )
        
        # Breakdown by category
        breakdown_by_category = {
            "waste": float(carbon_from_waste),
            "utilities": float(carbon_from_utilities),
            "deliveries": float(carbon_from_deliveries),
            "food_production": float(carbon_from_food)
        }
        
        total_carbon = carbon_from_waste + carbon_from_utilities + carbon_from_deliveries + carbon_from_food
        
        # Generate recommendations
        recommendations = self._generate_carbon_recommendations(
            carbon_from_waste, carbon_from_utilities, carbon_from_deliveries, carbon_from_food, total_carbon
        )
        
        return CarbonFootprintReport(
            date_range_start=start_date,
            date_range_end=end_date,
            total_carbon_kg=Decimal(str(round(total_carbon, 2))),
            carbon_from_waste=Decimal(str(round(carbon_from_waste, 2))),
            carbon_from_utilities=Decimal(str(round(carbon_from_utilities, 2))),
            carbon_from_deliveries=Decimal(str(round(carbon_from_deliveries, 2))),
            carbon_from_food=Decimal(str(round(carbon_from_food, 2))),
            breakdown_by_location=breakdown_by_location,
            breakdown_by_category=breakdown_by_category,
            recommendations=recommendations
        )
    
    def _calculate_utility_carbon(self, utility_data: List[UtilityDataDB]) -> float:
        """Calculate carbon from utilities"""
        total = 0.0
        
        for record in utility_data:
            if record.electricity_kwh:
                total += float(record.electricity_kwh) * self.ELECTRICITY_FACTOR
            if record.gas_therms:
                total += float(record.gas_therms) * self.GAS_FACTOR
            if record.water_gallons:
                total += float(record.water_gallons) * self.WATER_FACTOR
        
        return total
    
    def _calculate_delivery_carbon(self, delivery_data: List[DeliveryDataDB]) -> float:
        """Calculate carbon from deliveries"""
        total = 0.0
        
        for record in delivery_data:
            if record.total_distance_miles:
                total += float(record.total_distance_miles) * self.DELIVERY_FACTOR
            else:
                # Estimate 20 miles per delivery if distance not provided
                total += record.number_of_deliveries * 20 * self.DELIVERY_FACTOR
        
        return total
    
    def _calculate_location_breakdown(
        self,
        waste_data: List[WasteDataDB],
        utility_data: List[UtilityDataDB],
        delivery_data: List[DeliveryDataDB],
        food_data: List[NormalizedFoodDataDB]
    ) -> Dict[str, Decimal]:
        """Calculate carbon breakdown by location"""
        location_totals = defaultdict(float)
        
        # Waste by location
        waste_calc = WasteCalculator()
        for record in waste_data:
            carbon = waste_calc.calculate_waste_carbon(
                float(record.weight),
                WasteType(record.waste_type)
            )
            location_totals[record.location] += carbon
        
        # Utilities by location
        for record in utility_data:
            carbon = 0
            if record.electricity_kwh:
                carbon += float(record.electricity_kwh) * self.ELECTRICITY_FACTOR
            if record.gas_therms:
                carbon += float(record.gas_therms) * self.GAS_FACTOR
            if record.water_gallons:
                carbon += float(record.water_gallons) * self.WATER_FACTOR
            location_totals[record.location] += carbon
        
        # Deliveries by location
        for record in delivery_data:
            distance = float(record.total_distance_miles) if record.total_distance_miles else record.number_of_deliveries * 20
            carbon = distance * self.DELIVERY_FACTOR
            location_totals[record.location] += carbon
        
        return {loc: Decimal(str(round(total, 2))) for loc, total in location_totals.items()}
    
    def _generate_carbon_recommendations(
        self,
        waste_carbon: float,
        utility_carbon: float,
        delivery_carbon: float,
        food_carbon: float,
        total_carbon: float
    ) -> List[str]:
        """Generate recommendations for carbon reduction"""
        recommendations = []
        
        # Check which category is highest
        categories = [
            ("waste", waste_carbon),
            ("utilities", utility_carbon),
            ("deliveries", delivery_carbon),
            ("food production", food_carbon)
        ]
        categories.sort(key=lambda x: x[1], reverse=True)
        
        # Recommend based on highest categories
        if categories[0][0] == "food production":
            recommendations.append(
                f"Food production is your largest carbon source ({categories[0][1]:.1f} kg). "
                "Consider shifting menu towards plant-based proteins to reduce by up to 40%."
            )
        
        if categories[1][0] == "waste":
            recommendations.append(
                f"Food waste accounts for {waste_carbon:.1f} kg CO2e. "
                "Reducing waste by 30% could save {:.1f} kg CO2e.".format(waste_carbon * 0.3)
            )
        
        if delivery_carbon > total_carbon * 0.2:
            recommendations.append(
                f"Deliveries account for {delivery_carbon/total_carbon*100:.1f}% of your carbon footprint. "
                "Consider consolidating deliveries or sourcing locally."
            )
        
        if utility_carbon > total_carbon * 0.3:
            recommendations.append(
                "Utilities are a significant portion of your footprint. "
                "Consider energy-efficient equipment and renewable energy sources."
            )
        
        return recommendations
    
    def generate_recommendations(self, food_data: List[NormalizedFoodDataDB]) -> List[Dict[str, Any]]:
        """Generate specific carbon reduction recommendations"""
        recommendations = []
        
        # Analyze protein usage
        protein_usage = defaultdict(float)
        high_carbon_proteins = ["beef", "lamb", "pork"]
        medium_carbon_proteins = ["chicken", "turkey", "fish", "salmon"]
        low_carbon_proteins = ["tofu", "beans", "lentils", "vegetables"]
        
        for record in food_data:
            item_lower = record.food_item_name.lower()
            usage = float(record.food_used or 0)
            
            for protein in high_carbon_proteins:
                if protein in item_lower:
                    protein_usage["high_carbon"] += usage
            
            for protein in medium_carbon_proteins:
                if protein in item_lower:
                    protein_usage["medium_carbon"] += usage
            
            for protein in low_carbon_proteins:
                if protein in item_lower:
                    protein_usage["low_carbon"] += usage
        
        total_protein = sum(protein_usage.values())
        
        if total_protein > 0:
            high_pct = protein_usage["high_carbon"] / total_protein * 100
            
            if high_pct > 40:
                recommendations.append({
                    "priority": "high",
                    "category": "menu_optimization",
                    "title": "High Carbon Protein Usage",
                    "description": f"High-carbon proteins (beef, lamb, pork) account for {high_pct:.1f}% of protein usage",
                    "recommendation": "Shift 25% of high-carbon proteins to chicken or plant-based alternatives",
                    "estimated_reduction_kg": round(protein_usage["high_carbon"] * 0.25 * 27, 2)  # 27 kg CO2e per kg beef
                })
        
        return recommendations


class WasteCalculator:
    """Calculate carbon impact of waste"""
    
    # Carbon factors for different waste types (kg CO2e per kg waste)
    WASTE_FACTORS = {
        WasteType.REGULAR_WASTE: 2.5,  # Landfill emissions
        WasteType.COMPOST: 0.5,  # Much lower for composting
        WasteType.RECYCLING: 0.3  # Lowest for recycling
    }
    
    def calculate_waste_carbon(self, weight_kg: float, waste_type: WasteType) -> float:
        """Calculate carbon for a specific waste entry"""
        factor = self.WASTE_FACTORS.get(waste_type, 2.5)
        return weight_kg * factor
    
    def calculate_total_carbon(self, waste_data: List[WasteDataDB]) -> float:
        """Calculate total carbon from all waste"""
        total = 0.0
        
        for record in waste_data:
            # Convert weight to kg if needed
            weight_kg = float(record.weight)
            if record.unit.lower() in ["lb", "lbs"]:
                weight_kg = weight_kg * 0.453592
            
            carbon = self.calculate_waste_carbon(weight_kg, WasteType(record.waste_type))
            total += carbon
        
        return total
    
    def calculate_waste_impact(self, waste_data: List[WasteDataDB]) -> Dict[str, Any]:
        """Calculate detailed waste impact"""
        impact_by_type = defaultdict(float)
        weight_by_type = defaultdict(float)
        
        for record in waste_data:
            weight_kg = float(record.weight)
            if record.unit.lower() in ["lb", "lbs"]:
                weight_kg = weight_kg * 0.453592
            
            waste_type = WasteType(record.waste_type)
            carbon = self.calculate_waste_carbon(weight_kg, waste_type)
            
            impact_by_type[waste_type.value] += carbon
            weight_by_type[waste_type.value] += weight_kg
        
        total_carbon = sum(impact_by_type.values())
        total_weight = sum(weight_by_type.values())
        
        # Calculate potential savings if all waste was composted
        if WasteType.REGULAR_WASTE.value in weight_by_type:
            regular_waste_kg = weight_by_type[WasteType.REGULAR_WASTE.value]
            current_emissions = regular_waste_kg * self.WASTE_FACTORS[WasteType.REGULAR_WASTE]
            compost_emissions = regular_waste_kg * self.WASTE_FACTORS[WasteType.COMPOST]
            potential_savings = current_emissions - compost_emissions
        else:
            potential_savings = 0
        
        return {
            "total_carbon_kg": round(total_carbon, 2),
            "total_weight_kg": round(total_weight, 2),
            "breakdown_by_type": {k: round(v, 2) for k, v in impact_by_type.items()},
            "weight_by_type_kg": {k: round(v, 2) for k, v in weight_by_type.items()},
            "potential_savings_kg": round(potential_savings, 2),
            "recommendation": "Divert regular waste to composting to save {:.1f} kg CO2e".format(potential_savings) if potential_savings > 10 else None
        }


class MenuItemCarbonCalculator:
    """Calculate carbon footprint of menu items"""
    
    # Carbon intensity factors (kg CO2e per kg of food)
    CARBON_FACTORS = {
        "beef": 27.0,
        "lamb": 39.0,
        "pork": 12.1,
        "chicken": 6.9,
        "turkey": 10.9,
        "fish": 6.1,
        "salmon": 11.9,
        "shrimp": 26.9,
        "cheese": 13.5,
        "milk": 1.9,
        "eggs": 4.8,
        "rice": 4.0,
        "wheat": 1.4,
        "potato": 0.5,
        "vegetables": 2.0,
        "beans": 2.0,
        "lentils": 0.9,
        "tofu": 2.0,
        "nuts": 2.3,
        "bread": 1.6
    }
    
    def calculate_menu_item_carbon(
        self,
        item_name: str,
        ingredient_data: List[NormalizedFoodDataDB]
    ) -> MenuItemCarbon:
        """Calculate carbon footprint for a menu item"""
        ingredient_breakdown = {}
        total_carbon = 0.0
        carbon_by_category = defaultdict(float)
        
        # Aggregate ingredients
        for record in ingredient_data:
            ingredient = record.food_item_name.lower()
            weight_kg = float(record.food_used or 0) * 0.453592  # Convert lb to kg
            
            # Find matching carbon factor
            carbon_factor = self._get_carbon_factor(ingredient)
            carbon = weight_kg * carbon_factor
            
            ingredient_breakdown[record.food_item_name] = Decimal(str(round(carbon, 2)))
            total_carbon += carbon
            
            # Categorize
            category = self._categorize_ingredient(ingredient)
            carbon_by_category[category] += carbon
        
        return MenuItemCarbon(
            menu_item=item_name,
            ingredient_breakdown=ingredient_breakdown,
            total_carbon_kg=Decimal(str(round(total_carbon, 2))),
            carbon_by_category={k: Decimal(str(round(v, 2))) for k, v in carbon_by_category.items()}
        )
    
    def _get_carbon_factor(self, ingredient: str) -> float:
        """Get carbon factor for an ingredient"""
        ingredient_lower = ingredient.lower()
        
        # Check for exact or partial matches
        for key, factor in self.CARBON_FACTORS.items():
            if key in ingredient_lower:
                return factor
        
        # Default to vegetable factor
        return 2.0
    
    def _categorize_ingredient(self, ingredient: str) -> str:
        """Categorize ingredient for carbon breakdown"""
        ingredient_lower = ingredient.lower()
        
        if any(p in ingredient_lower for p in ["beef", "pork", "lamb", "chicken", "turkey", "fish", "salmon", "shrimp"]):
            return "protein"
        elif any(d in ingredient_lower for d in ["cheese", "milk", "butter", "cream", "yogurt"]):
            return "dairy"
        elif any(g in ingredient_lower for g in ["rice", "wheat", "bread", "pasta", "flour"]):
            return "grains"
        elif any(v in ingredient_lower for v in ["potato", "carrot", "onion", "tomato", "lettuce"]):
            return "vegetables"
        else:
            return "other"
    
    def calculate_total_food_carbon(self, food_data: List[NormalizedFoodDataDB]) -> float:
        """Calculate total carbon from food production"""
        total = 0.0
        
        for record in food_data:
            ingredient = record.food_item_name.lower()
            weight_kg = float(record.food_used or 0) * 0.453592  # Convert lb to kg
            
            carbon_factor = self._get_carbon_factor(ingredient)
            total += weight_kg * carbon_factor
        
        return total
