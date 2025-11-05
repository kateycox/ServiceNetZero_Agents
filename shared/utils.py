"""
Shared utility functions
"""
from typing import Dict, List, Optional
from fuzzywuzzy import fuzz, process
from datetime import datetime, date
import re


class IngredientNormalizer:
    """Normalizes ingredient names using fuzzy matching"""
    
    def __init__(self):
        self.known_ingredients = {
            "chicken": ["chx", "chkn", "chiken", "chik", "chcken"],
            "beef": ["bef", "beaf"],
            "pork": ["prk"],
            "salmon": ["slmon", "salm"],
            "rice": ["rce"],
            "potato": ["potatoes", "pot", "tater", "taters"],
            "carrot": ["carrots", "crrt"],
            "onion": ["onions", "onin"],
            "tomato": ["tomatoes", "tomat", "tmto"],
            "lettuce": ["letuce", "ltce"],
            "cheese": ["chz", "chse"],
            "milk": "mlk",
            "butter": ["butr", "buttr"],
            "cream": ["crm"],
            "flour": ["flr"],
            "sugar": ["sgr"],
            "salt": ["slt"],
            "pepper": ["pepr", "ppr"],
            "oil": ["olive oil", "vegetable oil", "canola oil"],
        }
        
        # Build reverse mapping
        self.alias_to_normalized = {}
        for normalized, aliases in self.known_ingredients.items():
            if isinstance(aliases, str):
                aliases = [aliases]
            for alias in aliases:
                self.alias_to_normalized[alias.lower()] = normalized
            self.alias_to_normalized[normalized.lower()] = normalized
    
    def normalize(self, ingredient_name: str, threshold: int = 80) -> tuple[str, float]:
        """
        Normalize an ingredient name
        
        Returns:
            tuple: (normalized_name, confidence_score)
        """
        cleaned = ingredient_name.lower().strip()
        
        # Direct match
        if cleaned in self.alias_to_normalized:
            return self.alias_to_normalized[cleaned], 1.0
        
        # Fuzzy match
        matches = process.extractOne(
            cleaned,
            self.alias_to_normalized.keys(),
            scorer=fuzz.ratio
        )
        
        if matches and matches[1] >= threshold:
            matched_alias = matches[0]
            normalized = self.alias_to_normalized[matched_alias]
            confidence = matches[1] / 100.0
            return normalized, confidence
        
        # No good match found, return original with low confidence
        return ingredient_name, 0.5
    
    def add_mapping(self, alias: str, normalized_name: str):
        """Add a new ingredient mapping"""
        self.alias_to_normalized[alias.lower()] = normalized_name.lower()
        
        if normalized_name.lower() not in self.known_ingredients:
            self.known_ingredients[normalized_name.lower()] = []
        
        if isinstance(self.known_ingredients[normalized_name.lower()], str):
            self.known_ingredients[normalized_name.lower()] = [
                self.known_ingredients[normalized_name.lower()]
            ]
        
        if alias.lower() not in self.known_ingredients[normalized_name.lower()]:
            self.known_ingredients[normalized_name.lower()].append(alias.lower())


class TextExtractor:
    """Extract structured data from text"""
    
    @staticmethod
    def extract_date(text: str) -> Optional[date]:
        """Extract date from text"""
        # Common date patterns
        patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups[0]) == 4:  # YYYY first
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    else:
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    return date(year, month, day)
                except ValueError:
                    continue
        
        return None
    
    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """Extract all numbers from text"""
        pattern = r'[-+]?\d*\.?\d+'
        matches = re.findall(pattern, text)
        return [float(m) for m in matches]
    
    @staticmethod
    def extract_quantities(text: str) -> List[Dict[str, any]]:
        """Extract quantity-unit pairs from text"""
        # Pattern: number followed by unit
        pattern = r'([-+]?\d*\.?\d+)\s*(lb|lbs|oz|kg|g|piece|pieces|serving|servings|cup|cups|gallon|gallons|liter|liters)?'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        results = []
        for match in matches:
            quantity = float(match[0])
            unit = match[1].lower() if match[1] else "piece"
            
            # Normalize units
            unit_map = {
                "lbs": "lb",
                "pieces": "piece",
                "servings": "serving",
                "cups": "cup",
                "gallons": "gallon",
                "liters": "liter"
            }
            unit = unit_map.get(unit, unit)
            
            results.append({"quantity": quantity, "unit": unit})
        
        return results


class UnitConverter:
    """Convert between different units of measure"""
    
    # Conversion factors to grams
    TO_GRAMS = {
        "g": 1.0,
        "kg": 1000.0,
        "oz": 28.3495,
        "lb": 453.592,
    }
    
    # Conversion factors to liters
    TO_LITERS = {
        "liter": 1.0,
        "gallon": 3.78541,
        "cup": 0.236588,
    }
    
    @classmethod
    def convert(cls, value: float, from_unit: str, to_unit: str) -> Optional[float]:
        """Convert value from one unit to another"""
        from_unit = from_unit.lower()
        to_unit = to_unit.lower()
        
        # Weight conversions
        if from_unit in cls.TO_GRAMS and to_unit in cls.TO_GRAMS:
            grams = value * cls.TO_GRAMS[from_unit]
            return grams / cls.TO_GRAMS[to_unit]
        
        # Volume conversions
        if from_unit in cls.TO_LITERS and to_unit in cls.TO_LITERS:
            liters = value * cls.TO_LITERS[from_unit]
            return liters / cls.TO_LITERS[to_unit]
        
        return None
    
    @classmethod
    def normalize_to_standard(cls, value: float, unit: str) -> tuple[float, str]:
        """Normalize to standard unit (kg for weight, liter for volume)"""
        unit = unit.lower()
        
        if unit in cls.TO_GRAMS:
            kg = (value * cls.TO_GRAMS[unit]) / 1000.0
            return kg, "kg"
        
        if unit in cls.TO_LITERS:
            liters = value * cls.TO_LITERS[unit]
            return liters, "liter"
        
        return value, unit


def calculate_waste_percentage(prepared: float, used: float, wasted: float) -> float:
    """Calculate waste percentage"""
    if prepared == 0:
        return 0.0
    total_waste = wasted if wasted else (prepared - used)
    return (total_waste / prepared) * 100.0


def calculate_accuracy_rate(ordered: float, used: float) -> float:
    """Calculate how accurately ordering matched actual usage"""
    if ordered == 0:
        return 0.0
    accuracy = (min(used, ordered) / ordered) * 100.0
    return min(accuracy, 100.0)  # Cap at 100%
