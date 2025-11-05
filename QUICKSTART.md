# Quick Start Guide

Get your Food Service Data Analysis System up and running in 5 minutes!

## Step 1: Initial Setup (1 minute)

```bash
# Navigate to workspace
cd /workspace

# Copy environment file
cp .env.example .env

# (Optional) Edit .env file if you want custom configuration
# Default settings work fine for local development
```

## Step 2: Start Services (2 minutes)

```bash
# Start all services with Docker Compose
docker-compose up -d

# Wait about 30 seconds for all services to initialize
# Check if services are running
docker-compose ps
```

You should see all services in "Up" state:
- postgres
- redis
- machine1, machine2, machine3, machine4, machine5, machine6
- api_gateway

## Step 3: Verify Installation (1 minute)

```bash
# Check system health
curl http://localhost:8000/health

# You should see all services reporting "healthy"
```

Or visit in your browser: http://localhost:8000/health

## Step 4: Access the Dashboard (1 minute)

Open your browser and visit:

**http://localhost:8004**

You'll see the interactive Food Service Dashboard!

## Step 5: Load Sample Data (Optional)

```bash
# Create a sample data file
cat > sample_data.json << 'EOF'
{
  "items": [
    {
      "date": "2024-01-15",
      "location": "Main Kitchen",
      "meal_period": "lunch",
      "food_item_name": "chicken",
      "food_ordered": 50.0,
      "food_prepared": 48.0,
      "food_used": 42.0,
      "food_wasted_boh": 3.0,
      "food_wasted_foh": 3.0,
      "unit_of_measure": "lb"
    }
  ]
}
EOF

# Upload the data
curl -X POST "http://localhost:8001/integrate/external-system?source=inventory_system" \
  -H "Content-Type: application/json" \
  -d @sample_data.json
```

## Try These Commands

### 1. Ask the Chatbot a Question

```bash
# Create a chat session
SESSION_ID=$(curl -X POST "http://localhost:8006/chat/session" | jq -r '.data.session_id')

# Ask about waste
curl -X POST "http://localhost:8006/chat/message" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What are my waste patterns?\", \"session_id\": \"$SESSION_ID\"}"
```

### 2. Get Event Statistics

```bash
curl "http://localhost:8002/analyze/events?start_date=2024-01-01&end_date=2024-01-31"
```

### 3. Generate Insights

```bash
curl -X POST "http://localhost:8003/insights/generate?days_to_analyze=30"
```

### 4. Get Carbon Report

```bash
curl "http://localhost:8005/carbon/report?start_date=2024-01-01&end_date=2024-01-31"
```

## API Documentation

Each service has interactive API documentation:

- **API Gateway**: http://localhost:8000/docs
- **Machine 1**: http://localhost:8001/docs
- **Machine 2**: http://localhost:8002/docs
- **Machine 3**: http://localhost:8003/docs
- **Machine 4**: http://localhost:8004/docs
- **Machine 5**: http://localhost:8005/docs
- **Machine 6**: http://localhost:8006/docs

## Common Issues

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Restart services
docker-compose restart
```

### Port Already in Use

Edit `.env` file and change the ports:
```bash
MACHINE1_PORT=9001
MACHINE2_PORT=9002
# etc...
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

### Database Connection Error

```bash
# Recreate database
docker-compose down -v
docker-compose up -d postgres
sleep 10
docker-compose up -d
```

## Next Steps

1. **Upload Real Data**: Use Machine 1 to upload your BEOs, invoices, or integrate with your systems

2. **Explore Dashboard**: Visit http://localhost:8004 and try different filters

3. **Chat with Bot**: Create insights by chatting at http://localhost:8006

4. **Generate Reports**: Use Machine 4 to create comprehensive reports

5. **Track Carbon**: Log waste and utility data to track environmental impact

## Getting Help

- **Documentation**: See README.md
- **Architecture**: See ARCHITECTURE.md
- **API Reference**: http://localhost:8000/docs

## Stop Services

When you're done:

```bash
docker-compose down

# To remove all data (start fresh):
docker-compose down -v
```

---

**That's it!** You now have a fully functional food service analysis system. Happy analyzing! 🎉
