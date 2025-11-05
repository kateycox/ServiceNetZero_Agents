# System Architecture

## Overview

The Food Service Data Analysis System is a microservices-based application designed to provide comprehensive insights into food service operations. The system follows a modular architecture where each "machine" (service) has a specific responsibility.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway (8000)                       │
│                    Unified Entry Point & Routing                 │
└────────┬─────────┬─────────┬─────────┬─────────┬────────┬──────┘
         │         │         │         │         │        │
    ┌────▼────┐┌──▼──┐┌─────▼────┐┌──▼───┐┌───▼───┐┌───▼────┐
    │Machine 1││M2   ││Machine 3 ││M4    ││M5     ││Machine6│
    │Data     ││Anal.││Insights  ││Dash. ││Carbon ││Chatbot │
    │Ingestion││     ││& Predict.││      ││Track  ││        │
    │(8001)   ││(8002)││(8003)    ││(8004)││(8005) ││(8006)  │
    └────┬────┘└──┬──┘└─────┬────┘└──┬───┘└───┬───┘└───┬────┘
         │        │         │         │        │        │
         └────────┴─────────┴─────────┴────────┴────────┘
                            │
                     ┌──────▼───────┐
                     │  PostgreSQL  │
                     │   Database   │
                     └──────────────┘
```

## Service Details

### Machine 1: Data Ingestion & Normalization (Port 8001)

**Responsibilities:**
- OCR processing of documents (BEOs, invoices, notes)
- Integration with external systems (POS, inventory, accounting)
- Data normalization and standardization
- Field extraction and structuring

**Key Components:**
- `OCRProcessor`: Handles image/PDF text extraction
- `BEOProcessor`: Parses Banquet Event Orders
- `InvoiceProcessor`: Extracts data from vendor invoices
- `IntegrationProcessor`: Handles external system data
- `IngredientNormalizer`: Standardizes ingredient names

**Data Flow:**
1. Receive raw input (document/API data)
2. Extract text/data
3. Parse and structure
4. Normalize ingredient names
5. Save to database

### Machine 2: Statistical Analysis & Pattern Detection (Port 8002)

**Responsibilities:**
- Event statistics calculation
- Waste pattern detection
- Ordering accuracy analysis
- Seasonal trend identification
- BEO comparison

**Key Components:**
- `EventAnalyzer`: Aggregates event-level statistics
- `IngredientAnalyzer`: Analyzes ingredient usage patterns
- `BEOComparator`: Compares before/after BEOs
- `PatternDetector`: Identifies recurring patterns

**Analysis Types:**
1. **Descriptive**: What happened? (counts, totals, averages)
2. **Diagnostic**: Why did it happen? (correlations, comparisons)
3. **Pattern-based**: What patterns exist? (trends, seasonality)

### Machine 3: Predictive Insights & Recommendations (Port 8003)

**Responsibilities:**
- Demand forecasting
- Waste risk prediction
- Cost savings identification
- Recommendation generation
- Trend analysis

**Key Components:**
- `DemandPredictor`: Time-series forecasting using Random Forest
- `WastePredictor`: Risk assessment for future waste
- `InsightGenerator`: Creates actionable insights
- `RecommendationEngine`: Generates specific recommendations

**ML Approach:**
- Historical data analysis (90-day window)
- Feature engineering (day of week, month, trends)
- Confidence interval calculation
- Multi-factor recommendation scoring

### Machine 4: Visualization Dashboard (Port 8004)

**Responsibilities:**
- Interactive data visualization
- Filterable dashboards
- Report generation
- Chart creation

**Key Components:**
- `ChartGenerator`: Creates Plotly charts
- `ReportGenerator`: Generates comprehensive reports
- HTML/JavaScript dashboard with real-time filtering

**Visualization Types:**
1. Pie charts (waste distribution)
2. Line charts (timeline trends)
3. Bar charts (comparisons)
4. Heatmaps (patterns)

### Machine 5: Carbon Footprint Tracking (Port 8005)

**Responsibilities:**
- Carbon emission calculation
- Waste impact measurement
- Utility carbon tracking
- Menu item carbon footprint
- Reduction recommendations

**Key Components:**
- `CarbonCalculator`: Main carbon calculation engine
- `WasteCalculator`: Waste-specific carbon impact
- `MenuItemCarbonCalculator`: Food production emissions

**Carbon Factors:**
- Electricity: 0.92 kg CO2e/kWh
- Natural Gas: 5.3 kg CO2e/therm
- Landfill Waste: 2.5 kg CO2e/kg
- Beef: 27 kg CO2e/kg
- Chicken: 6.9 kg CO2e/kg
- Vegetables: 2.0 kg CO2e/kg

### Machine 6: Orchestration Chatbot (Port 8006)

**Responsibilities:**
- Natural language interface
- Cross-service orchestration
- Context management
- User alert handling
- Intent classification

**Key Components:**
- `IntentClassifier`: Classifies user intent
- `ContextManager`: Maintains conversation context
- `FoodServiceBot`: Main chatbot logic

**Intent Types:**
- waste_query
- ordering_query
- insight_query
- carbon_query
- forecast_query
- status_query
- alert_create

## Data Models

### Core Entities

1. **NormalizedFoodData**: Central data model
   - Captures all food-related transactions
   - Links events, locations, ingredients
   - Tracks quantities (ordered, prepared, used, wasted)

2. **PredictiveInsight**: AI-generated insights
   - Categorized by type and priority
   - Includes recommendations and impact estimates
   - Confidence-scored

3. **Carbon Data**: Environmental tracking
   - Waste, utilities, deliveries
   - Menu item carbon intensity
   - Location-based breakdown

## Communication Patterns

### Synchronous (HTTP/REST)
- API Gateway → Services
- Service → Service (when needed)
- Client → API Gateway

### Asynchronous (Future Enhancement)
- Redis pub/sub for real-time updates
- Celery for background tasks
- WebSocket for live dashboard updates

## Data Storage

### PostgreSQL Database

**Tables:**
- `normalized_food_data`: Main fact table
- `ingredient_mappings`: Normalization rules
- `predictive_insights`: AI insights
- `waste_data`: Waste tracking
- `utility_data`: Utility usage
- `delivery_data`: Delivery logs
- `user_alerts`: User notifications
- `chat_history`: Conversation logs
- `raw_data_inputs`: Original uploads

### Data Partitioning Strategy
- Partition by date for large tables
- Index on frequently queried fields (date, location, ingredient)

## Scalability Considerations

### Horizontal Scaling
- Each service can be scaled independently
- Stateless design (except chatbot context)
- Load balancing via Docker Swarm/Kubernetes

### Vertical Scaling
- Database connection pooling
- Caching layer (Redis)
- Async processing for heavy operations

### Performance Optimization
- Database query optimization
- Batch processing for large datasets
- CDN for static dashboard assets

## Security

### API Security
- JWT authentication (future)
- Rate limiting per endpoint
- Input validation on all endpoints

### Data Security
- Encrypted database connections
- Parameterized queries (SQL injection prevention)
- Sensitive data encryption at rest

## Monitoring & Observability

### Health Checks
- `/health` endpoint on each service
- API Gateway aggregates health status

### Logging
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Centralized log aggregation (future: ELK stack)

### Metrics (Future)
- Request latency
- Error rates
- Resource utilization
- Prediction accuracy

## Deployment

### Development
```bash
docker-compose up -d
```

### Production (Future)
- Kubernetes deployment
- Helm charts
- CI/CD pipeline (GitHub Actions)
- Blue-green deployments

## Error Handling

### Strategy
1. Validate input at API boundary
2. Try-catch blocks around external calls
3. Meaningful error messages
4. HTTP status codes follow REST conventions
5. Database rollback on errors

### Circuit Breaker Pattern
- Prevents cascade failures
- Fallback responses when service unavailable
- Automatic retry with exponential backoff

## Testing Strategy

### Unit Tests
- Test individual functions
- Mock external dependencies
- Coverage target: 80%+

### Integration Tests
- Test service interactions
- Database integration
- API endpoint testing

### E2E Tests
- Full workflow testing
- Dashboard functionality
- Chatbot conversations

## Future Enhancements

1. **Real-time Processing**: Stream processing with Kafka
2. **Advanced ML**: Deep learning for better predictions
3. **Mobile App**: React Native companion app
4. **Multi-tenancy**: Support for multiple organizations
5. **Advanced Analytics**: Real-time anomaly detection
6. **Integration Hub**: Pre-built connectors for major POS/ERP systems
