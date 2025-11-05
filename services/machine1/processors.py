"""
Document processors for Machine 1
"""
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
from typing import List, Dict, Any
from datetime import date, datetime
import re
import sys
sys.path.append('/workspace')

from shared.models import NormalizedFoodData, DataSource, MealPeriod, UnitOfMeasure
from shared.utils import IngredientNormalizer, TextExtractor


class OCRProcessor:
    """Handles OCR processing of documents"""
    
    def process_document(self, file_path: str) -> str:
        """
        Process a document with OCR
        """
        try:
            # Handle PDF
            if file_path.lower().endswith('.pdf'):
                images = convert_from_path(file_path)
                text = ""
                for image in images:
                    text += pytesseract.image_to_string(image)
                return text
            
            # Handle images
            else:
                image = cv2.imread(file_path)
                # Preprocess image for better OCR
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                # Denoise
                denoised = cv2.fastNlMeansDenoising(gray)
                # Threshold
                _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Run OCR
                text = pytesseract.image_to_string(thresh)
                return text
                
        except Exception as e:
            print(f"OCR processing error: {e}")
            return ""


class BEOProcessor:
    """Process Banquet Event Orders (BEOs)"""
    
    def __init__(self, normalizer: IngredientNormalizer, extractor: TextExtractor):
        self.normalizer = normalizer
        self.extractor = extractor
    
    def process(self, text: str) -> List[NormalizedFoodData]:
        """
        Extract structured data from BEO text
        """
        records = []
        lines = text.split('\n')
        
        # Extract metadata
        event_date = self.extractor.extract_date(text)
        event_name = self._extract_event_name(lines)
        location = self._extract_location(lines)
        meal_period = self._extract_meal_period(text)
        guest_count = self._extract_guest_count(lines)
        
        # Extract food items
        food_items = self._extract_food_items(lines)
        
        for item in food_items:
            normalized_name, confidence = self.normalizer.normalize(item['name'])
            
            record = NormalizedFoodData(
                date=event_date or date.today(),
                event_name=event_name,
                location=location or "Unknown",
                meal_period=meal_period,
                original_guest_count=guest_count,
                final_guest_count=guest_count,
                food_item_name=normalized_name,
                food_ordered=item.get('quantity'),
                unit_of_measure=item.get('unit', UnitOfMeasure.SERVING),
                source=DataSource.BEO
            )
            records.append(record)
        
        return records
    
    def _extract_event_name(self, lines: List[str]) -> str:
        """Extract event name from BEO"""
        for line in lines[:10]:  # Check first 10 lines
            if any(keyword in line.lower() for keyword in ['event', 'function', 'party', 'meeting']):
                # Extract the part after the keyword
                for keyword in ['event:', 'function:', 'party:', 'meeting:']:
                    if keyword in line.lower():
                        return line.split(keyword, 1)[1].strip()
        return "Unknown Event"
    
    def _extract_location(self, lines: List[str]) -> str:
        """Extract location from BEO"""
        for line in lines[:15]:
            if any(keyword in line.lower() for keyword in ['location', 'venue', 'room', 'ballroom']):
                # Extract the part after the keyword
                for keyword in ['location:', 'venue:', 'room:', 'ballroom:']:
                    if keyword in line.lower():
                        return line.split(keyword, 1)[1].strip()
        return "Unknown Location"
    
    def _extract_meal_period(self, text: str) -> MealPeriod:
        """Extract meal period from text"""
        text_lower = text.lower()
        if 'breakfast' in text_lower:
            return MealPeriod.BREAKFAST
        elif 'lunch' in text_lower:
            return MealPeriod.LUNCH
        elif 'dinner' in text_lower:
            return MealPeriod.DINNER
        elif 'brunch' in text_lower:
            return MealPeriod.BRUNCH
        elif 'reception' in text_lower:
            return MealPeriod.RECEPTION
        else:
            return MealPeriod.LUNCH
    
    def _extract_guest_count(self, lines: List[str]) -> int:
        """Extract guest count from BEO"""
        for line in lines[:20]:
            if any(keyword in line.lower() for keyword in ['guest', 'attendance', 'count', 'pax']):
                numbers = self.extractor.extract_numbers(line)
                if numbers:
                    return int(numbers[0])
        return 0
    
    def _extract_food_items(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract food items with quantities"""
        items = []
        in_menu_section = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect menu section
            if any(keyword in line_lower for keyword in ['menu', 'food', 'items', 'courses']):
                in_menu_section = True
                continue
            
            if in_menu_section and line.strip():
                # Extract quantity and item name
                quantities = self.extractor.extract_quantities(line)
                
                # Remove quantity from line to get item name
                item_name = re.sub(r'[-+]?\d*\.?\d+\s*(lb|lbs|oz|kg|g|piece|pieces|serving|servings|cup|cups|gallon|gallons|liter|liters)?', '', line, flags=re.IGNORECASE).strip()
                
                if item_name and len(item_name) > 2:
                    item = {
                        'name': item_name,
                        'quantity': quantities[0]['quantity'] if quantities else None,
                        'unit': quantities[0]['unit'] if quantities else UnitOfMeasure.SERVING
                    }
                    items.append(item)
        
        return items


class InvoiceProcessor:
    """Process vendor invoices"""
    
    def __init__(self, normalizer: IngredientNormalizer, extractor: TextExtractor):
        self.normalizer = normalizer
        self.extractor = extractor
    
    def process(self, text: str) -> List[NormalizedFoodData]:
        """
        Extract structured data from invoice text
        """
        records = []
        lines = text.split('\n')
        
        invoice_date = self.extractor.extract_date(text)
        location = self._extract_location(lines)
        
        # Extract line items
        items = self._extract_line_items(lines)
        
        for item in items:
            normalized_name, confidence = self.normalizer.normalize(item['name'])
            
            record = NormalizedFoodData(
                date=invoice_date or date.today(),
                location=location or "Unknown",
                meal_period=MealPeriod.LUNCH,  # Default, could be refined
                food_item_name=normalized_name,
                food_ordered=item.get('quantity'),
                unit_of_measure=item.get('unit', UnitOfMeasure.LB),
                transaction_volume=item.get('price'),
                source=DataSource.VENDOR_INVOICE
            )
            records.append(record)
        
        return records
    
    def _extract_location(self, lines: List[str]) -> str:
        """Extract delivery location from invoice"""
        for line in lines[:10]:
            if any(keyword in line.lower() for keyword in ['deliver to', 'ship to', 'location']):
                return line.split(':', 1)[1].strip() if ':' in line else "Unknown"
        return "Unknown"
    
    def _extract_line_items(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract line items from invoice"""
        items = []
        in_items_section = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect items section
            if any(keyword in line_lower for keyword in ['item', 'description', 'product']):
                in_items_section = True
                continue
            
            if in_items_section and line.strip():
                # Pattern: Item Name, Quantity, Unit, Price
                quantities = TextExtractor.extract_quantities(line)
                prices = TextExtractor.extract_numbers(line)
                
                # Extract item name (usually at the beginning)
                item_name = line.split()[0:3]  # First few words
                item_name = ' '.join(item_name)
                
                if item_name and len(item_name) > 2:
                    item = {
                        'name': item_name,
                        'quantity': quantities[0]['quantity'] if quantities else None,
                        'unit': quantities[0]['unit'] if quantities else UnitOfMeasure.LB,
                        'price': prices[-1] if prices else None  # Last number is usually price
                    }
                    items.append(item)
        
        return items


class HandwrittenNotesProcessor:
    """Process handwritten notes"""
    
    def __init__(self, normalizer: IngredientNormalizer, extractor: TextExtractor):
        self.normalizer = normalizer
        self.extractor = extractor
    
    def process(self, text: str) -> List[NormalizedFoodData]:
        """
        Extract structured data from handwritten notes
        """
        records = []
        lines = text.split('\n')
        
        note_date = self.extractor.extract_date(text) or date.today()
        
        # Process each line as a potential food item note
        for line in lines:
            if not line.strip():
                continue
            
            # Look for waste indicators
            is_waste = any(keyword in line.lower() for keyword in ['waste', 'thrown', 'leftover', 'excess'])
            
            # Extract food item and quantity
            quantities = self.extractor.extract_quantities(line)
            
            # Get item name
            item_name = re.sub(r'[-+]?\d*\.?\d+\s*(lb|lbs|oz|kg|g|piece|pieces)?', '', line, flags=re.IGNORECASE).strip()
            item_name = re.sub(r'\b(waste|thrown|leftover|excess)\b', '', item_name, flags=re.IGNORECASE).strip()
            
            if item_name and len(item_name) > 2:
                normalized_name, confidence = self.normalizer.normalize(item_name)
                
                record = NormalizedFoodData(
                    date=note_date,
                    location="Kitchen",  # Default
                    meal_period=MealPeriod.LUNCH,  # Default
                    food_item_name=normalized_name,
                    food_wasted_boh=quantities[0]['quantity'] if is_waste and quantities else None,
                    unit_of_measure=quantities[0]['unit'] if quantities else UnitOfMeasure.LB,
                    source=DataSource.HANDWRITTEN_NOTE
                )
                records.append(record)
        
        return records


class IntegrationProcessor:
    """Process data from external integrations"""
    
    def __init__(self, normalizer: IngredientNormalizer, extractor: TextExtractor):
        self.normalizer = normalizer
        self.extractor = extractor
    
    def process(self, source: DataSource, data: dict) -> List[NormalizedFoodData]:
        """
        Process data from external systems
        """
        if source == DataSource.INVENTORY_SYSTEM:
            return self._process_inventory(data)
        elif source == DataSource.POS_SYSTEM:
            return self._process_pos(data)
        elif source == DataSource.CATERING_SYSTEM:
            return self._process_catering(data)
        else:
            return self._process_generic(data, source)
    
    def _process_inventory(self, data: dict) -> List[NormalizedFoodData]:
        """Process inventory system data"""
        records = []
        items = data.get('items', [])
        
        for item in items:
            normalized_name, _ = self.normalizer.normalize(item.get('name', ''))
            
            record = NormalizedFoodData(
                date=date.today(),
                location=data.get('location', 'Unknown'),
                meal_period=MealPeriod.LUNCH,
                food_item_name=normalized_name,
                food_ordered=item.get('quantity_on_hand'),
                unit_of_measure=UnitOfMeasure(item.get('unit', 'lb')),
                source=DataSource.INVENTORY_SYSTEM
            )
            records.append(record)
        
        return records
    
    def _process_pos(self, data: dict) -> List[NormalizedFoodData]:
        """Process POS system data"""
        records = []
        transactions = data.get('transactions', [])
        
        for transaction in transactions:
            for item in transaction.get('items', []):
                normalized_name, _ = self.normalizer.normalize(item.get('name', ''))
                
                record = NormalizedFoodData(
                    date=datetime.fromisoformat(transaction.get('date')).date(),
                    location=data.get('location', 'Unknown'),
                    meal_period=MealPeriod(transaction.get('meal_period', 'lunch')),
                    food_item_name=normalized_name,
                    food_used=item.get('quantity'),
                    unit_of_measure=UnitOfMeasure.SERVING,
                    transaction_volume=item.get('price'),
                    source=DataSource.POS_SYSTEM
                )
                records.append(record)
        
        return records
    
    def _process_catering(self, data: dict) -> List[NormalizedFoodData]:
        """Process catering system data"""
        records = []
        events = data.get('events', [])
        
        for event in events:
            for item in event.get('menu_items', []):
                normalized_name, _ = self.normalizer.normalize(item.get('name', ''))
                
                record = NormalizedFoodData(
                    date=datetime.fromisoformat(event.get('date')).date(),
                    event_name=event.get('name'),
                    location=event.get('location', 'Unknown'),
                    meal_period=MealPeriod(event.get('meal_period', 'lunch')),
                    original_guest_count=event.get('guest_count'),
                    final_guest_count=event.get('final_guest_count', event.get('guest_count')),
                    food_item_name=normalized_name,
                    food_ordered=item.get('quantity_ordered'),
                    food_prepared=item.get('quantity_prepared'),
                    unit_of_measure=UnitOfMeasure(item.get('unit', 'serving')),
                    source=DataSource.CATERING_SYSTEM
                )
                records.append(record)
        
        return records
    
    def _process_generic(self, data: dict, source: DataSource) -> List[NormalizedFoodData]:
        """Process generic data format"""
        records = []
        items = data.get('items', [])
        
        for item in items:
            normalized_name, _ = self.normalizer.normalize(item.get('food_item_name', ''))
            
            record = NormalizedFoodData(
                date=datetime.fromisoformat(item.get('date')).date() if item.get('date') else date.today(),
                event_name=item.get('event_name'),
                location=item.get('location', 'Unknown'),
                meal_period=MealPeriod(item.get('meal_period', 'lunch')),
                original_guest_count=item.get('original_guest_count'),
                final_guest_count=item.get('final_guest_count'),
                food_item_name=normalized_name,
                food_ordered=item.get('food_ordered'),
                food_prepared=item.get('food_prepared'),
                food_used=item.get('food_used'),
                unit_of_measure=UnitOfMeasure(item.get('unit_of_measure', 'lb')),
                source=source
            )
            records.append(record)
        
        return records
