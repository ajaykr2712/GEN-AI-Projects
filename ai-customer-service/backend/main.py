from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
import asyncio

from app.core.config import settings
from app.core.database import engine, Base
from app.core.container import configure_container
from app.api.routes import auth, chat, logs

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AI Customer Service Assistant")
    
    # Initialize database
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Configure dependency injection
    configure_container()
    logger.info("Dependency injection container configured")
    
    # Startup background tasks
    asyncio.create_task(periodic_health_check())
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Customer Service Assistant")


async def periodic_health_check():
    """Periodic health check task."""
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes
            logger.debug("Health check - System running normally")
        except Exception as e:
            logger.error(f"Health check error: {e}")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered customer service assistant with advanced architecture",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.vercel.app"]
)

# Add request timing and logging middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Calculate and add process time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log response
    logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
    
    return response


# Enhanced global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Enhanced global exception handler with detailed logging."""
    logger.error(
        f"Global exception on {request.method} {request.url}: {exc}",
        exc_info=True,
        extra={
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "unknown"
        }
    )
    
    # Return appropriate error response based on exception type
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", "unknown")
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    from app.core.monitoring import health_checker
    
    health_results = await health_checker.run_checks()
    
    return {
        "status": health_results["status"],
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": time.time(),
        "checks": health_results["checks"]
    }


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Get system metrics."""
    from app.core.monitoring import metrics_collector, performance_monitor
    
    metrics = metrics_collector.get_metrics_summary()
    alerts = performance_monitor.get_alerts()
    
    return {
        "metrics": metrics,
        "alerts": alerts,
        "timestamp": time.time()
    }


# Performance monitoring endpoint
@app.get("/metrics/{metric_name}")
async def get_metric_timeseries(metric_name: str, hours: int = 1):
    """Get time series data for a specific metric."""
    from app.core.monitoring import metrics_collector
    from datetime import datetime, timedelta
    
    since = datetime.utcnow() - timedelta(hours=hours)
    data = metrics_collector.get_time_series(metric_name, since)
    
    return {
        "metric_name": metric_name,
        "data": data,
        "count": len(data)
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Customer Service Assistant API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }

# Include routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"]
)

app.include_router(
    chat.router,
    prefix=f"{settings.API_V1_STR}/chat",
    tags=["Chat & AI"]
)

app.include_router(
    logs.router,
    prefix=f"{settings.API_V1_STR}/logs",
    tags=["Customer Logs"]
)

# Analytics endpoint
@app.get(f"{settings.API_V1_STR}/analytics")
async def get_analytics():
    """Get system analytics (placeholder for future implementation)."""
    return {
        "total_conversations": 0,
        "total_messages": 0,
        "active_users": 0,
        "avg_response_time": 0.0,
        "popular_categories": []
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
