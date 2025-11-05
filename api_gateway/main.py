"""
API Gateway

Central entry point for all services.
Routes requests to appropriate machines and provides unified API.
"""
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import os
from typing import Optional

app = FastAPI(
    title="Food Service Data Analysis API Gateway",
    version="1.0.0",
    description="Unified API for all food service analysis machines"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
SERVICES = {
    "machine1": f"http://machine1:{os.getenv('MACHINE1_PORT', 8001)}",
    "machine2": f"http://machine2:{os.getenv('MACHINE2_PORT', 8002)}",
    "machine3": f"http://machine3:{os.getenv('MACHINE3_PORT', 8003)}",
    "machine4": f"http://machine4:{os.getenv('MACHINE4_PORT', 8004)}",
    "machine5": f"http://machine5:{os.getenv('MACHINE5_PORT', 8005)}",
    "machine6": f"http://machine6:{os.getenv('MACHINE6_PORT', 8006)}"
}


@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "Food Service Data Analysis System",
        "version": "1.0.0",
        "services": {
            "machine1": "Data Ingestion & Normalization",
            "machine2": "Statistical Analysis & Pattern Detection",
            "machine3": "Predictive Insights & Recommendations",
            "machine4": "Visualization Dashboard",
            "machine5": "Carbon Footprint Tracking",
            "machine6": "Orchestration Chatbot"
        },
        "endpoints": {
            "/health": "Check health of all services",
            "/api/v1/data": "Data ingestion endpoints (Machine 1)",
            "/api/v1/analytics": "Analytics endpoints (Machine 2)",
            "/api/v1/insights": "Insights endpoints (Machine 3)",
            "/api/v1/dashboard": "Dashboard endpoints (Machine 4)",
            "/api/v1/carbon": "Carbon tracking endpoints (Machine 5)",
            "/api/v1/chat": "Chatbot endpoints (Machine 6)"
        }
    }


@app.get("/health")
async def health_check():
    """
    Check health of all services
    """
    health_status = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health")
                if response.status_code == 200:
                    health_status[service_name] = "healthy"
                else:
                    health_status[service_name] = "unhealthy"
            except Exception as e:
                health_status[service_name] = f"error: {str(e)}"
    
    all_healthy = all(status == "healthy" for status in health_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": health_status
    }


# Machine 1 Routes - Data Ingestion
@app.api_route("/api/v1/data/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_machine1(path: str, request: Request):
    """Proxy requests to Machine 1"""
    return await proxy_request("machine1", path, request)


# Machine 2 Routes - Analytics
@app.api_route("/api/v1/analytics/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_machine2(path: str, request: Request):
    """Proxy requests to Machine 2"""
    return await proxy_request("machine2", path, request)


# Machine 3 Routes - Insights
@app.api_route("/api/v1/insights/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_machine3(path: str, request: Request):
    """Proxy requests to Machine 3"""
    return await proxy_request("machine3", path, request)


# Machine 4 Routes - Dashboard
@app.api_route("/api/v1/dashboard/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_machine4(path: str, request: Request):
    """Proxy requests to Machine 4"""
    return await proxy_request("machine4", path, request)


# Machine 5 Routes - Carbon
@app.api_route("/api/v1/carbon/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_machine5(path: str, request: Request):
    """Proxy requests to Machine 5"""
    return await proxy_request("machine5", path, request)


# Machine 6 Routes - Chat
@app.api_route("/api/v1/chat/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_machine6(path: str, request: Request):
    """Proxy requests to Machine 6"""
    return await proxy_request("machine6", path, request)


async def proxy_request(service_name: str, path: str, request: Request):
    """
    Generic proxy function to forward requests to services
    """
    service_url = SERVICES.get(service_name)
    
    if not service_url:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    # Build target URL
    target_url = f"{service_url}/{path}"
    
    # Get query parameters
    query_params = dict(request.query_params)
    
    # Get request body if present
    try:
        body = await request.body()
    except:
        body = None
    
    # Forward request
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if request.method == "GET":
                response = await client.get(target_url, params=query_params)
            elif request.method == "POST":
                response = await client.post(target_url, params=query_params, content=body)
            elif request.method == "PUT":
                response = await client.put(target_url, params=query_params, content=body)
            elif request.method == "DELETE":
                response = await client.delete(target_url, params=query_params)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            # Return response
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
            
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Service timeout")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_GATEWAY_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
