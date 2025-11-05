"""
Machine 1: Data Ingestion & Normalization Service

Reads scanned BEOs/Invoices/handwritten notes and organizes data.
Takes in data from online systems (inventory, vendor, accounting, catering, POS).
Normalizes and structures all data with standardized fields.
"""
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import sys
import os

sys.path.append('/workspace')

from shared.models import (
    RawDataInput, NormalizedFoodData, IngredientMapping, 
    DataSource, HealthCheck, APIResponse
)
from shared.database import get_db, init_db, NormalizedFoodDataDB, IngredientMappingDB, RawDataInputDB
from shared.utils import IngredientNormalizer, TextExtractor
from services.machine1.processors import (
    OCRProcessor, BEOProcessor, InvoiceProcessor, 
    IntegrationProcessor, HandwrittenNotesProcessor
)

app = FastAPI(title="Machine 1: Data Ingestion & Normalization", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
ingredient_normalizer = IngredientNormalizer()
text_extractor = TextExtractor()
ocr_processor = OCRProcessor()


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("Machine 1: Data Ingestion & Normalization Service started")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(service="Machine 1: Data Ingestion & Normalization", status="healthy")


@app.post("/upload/document", response_model=APIResponse)
async def upload_document(
    file: UploadFile = File(...),
    source: DataSource = DataSource.BEO,
    db: Session = Depends(get_db)
):
    """
    Upload a document (BEO, invoice, handwritten note, etc.) for processing
    """
    try:
        # Save the uploaded file
        upload_dir = "/workspace/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process with OCR
        raw_text = ocr_processor.process_document(file_path)
        
        # Save raw input
        raw_input = RawDataInputDB(
            source=source.value,
            file_path=file_path,
            raw_text=raw_text,
            metadata={"filename": file.filename}
        )
        db.add(raw_input)
        db.commit()
        db.refresh(raw_input)
        
        # Process based on document type
        normalized_data = []
        if source == DataSource.BEO:
            processor = BEOProcessor(ingredient_normalizer, text_extractor)
            normalized_data = processor.process(raw_text)
        elif source in [DataSource.INVOICE, DataSource.SYSCO, DataSource.VENDOR_INVOICE]:
            processor = InvoiceProcessor(ingredient_normalizer, text_extractor)
            normalized_data = processor.process(raw_text)
        elif source == DataSource.HANDWRITTEN_NOTE:
            processor = HandwrittenNotesProcessor(ingredient_normalizer, text_extractor)
            normalized_data = processor.process(raw_text)
        
        # Save normalized data
        saved_records = []
        for data in normalized_data:
            db_record = NormalizedFoodDataDB(**data.dict(exclude={'id'}))
            db_record.source_document_id = str(raw_input.id)
            db.add(db_record)
            saved_records.append(db_record)
        
        db.commit()
        
        # Mark raw input as processed
        raw_input.processed = True
        db.commit()
        
        return APIResponse(
            success=True,
            message=f"Document processed successfully. Extracted {len(saved_records)} records.",
            data={"raw_input_id": raw_input.id, "records_created": len(saved_records)}
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integrate/external-system", response_model=APIResponse)
async def integrate_external_system(
    source: DataSource,
    data: dict,
    db: Session = Depends(get_db)
):
    """
    Receive data from external systems (inventory, POS, accounting, etc.)
    """
    try:
        processor = IntegrationProcessor(ingredient_normalizer, text_extractor)
        normalized_data = processor.process(source, data)
        
        saved_records = []
        for item in normalized_data:
            db_record = NormalizedFoodDataDB(**item.dict(exclude={'id'}))
            db.add(db_record)
            saved_records.append(db_record)
        
        db.commit()
        
        return APIResponse(
            success=True,
            message=f"External system data integrated successfully. Created {len(saved_records)} records.",
            data={"records_created": len(saved_records)}
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/normalize/ingredient", response_model=IngredientMapping)
async def normalize_ingredient(
    raw_name: str,
    db: Session = Depends(get_db)
):
    """
    Normalize an ingredient name
    """
    normalized_name, confidence = ingredient_normalizer.normalize(raw_name)
    
    # Check if mapping exists
    existing = db.query(IngredientMappingDB).filter(
        IngredientMappingDB.raw_name == raw_name
    ).first()
    
    if not existing:
        mapping = IngredientMappingDB(
            raw_name=raw_name,
            normalized_name=normalized_name,
            confidence_score=confidence,
            aliases=[]
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
    else:
        mapping = existing
    
    return IngredientMapping(
        raw_name=mapping.raw_name,
        normalized_name=mapping.normalized_name,
        confidence_score=float(mapping.confidence_score),
        aliases=mapping.aliases or []
    )


@app.post("/normalize/ingredient/add-alias", response_model=APIResponse)
async def add_ingredient_alias(
    alias: str,
    normalized_name: str,
    db: Session = Depends(get_db)
):
    """
    Add a new ingredient alias mapping
    """
    ingredient_normalizer.add_mapping(alias, normalized_name)
    
    # Save to database
    mapping = IngredientMappingDB(
        raw_name=alias,
        normalized_name=normalized_name,
        confidence_score=1.0,
        aliases=[]
    )
    db.add(mapping)
    db.commit()
    
    return APIResponse(
        success=True,
        message=f"Added alias '{alias}' for '{normalized_name}'"
    )


@app.get("/data/normalized", response_model=List[NormalizedFoodData])
async def get_normalized_data(
    skip: int = 0,
    limit: int = 100,
    location: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get normalized food data with optional filters
    """
    query = db.query(NormalizedFoodDataDB)
    
    if location:
        query = query.filter(NormalizedFoodDataDB.location == location)
    if start_date:
        query = query.filter(NormalizedFoodDataDB.date >= start_date)
    if end_date:
        query = query.filter(NormalizedFoodDataDB.date <= end_date)
    
    records = query.offset(skip).limit(limit).all()
    
    return [NormalizedFoodData.from_orm(record) for record in records]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MACHINE1_PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
