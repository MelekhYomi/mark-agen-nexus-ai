from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db, close_db
from app.routers import dashboard, content, campaigns, billing, admin
from app.auth import router as auth
from app.integrations import oauth

# Parse allowed origins
allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and seed admin
    init_db()
    yield
    # Shutdown: Close database connections
    close_db()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - Secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Only allowed origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    expose_headers=["X-Total-Count", "X-Page", "X-Page-Size"],
    max_age=600,  # Cache preflight for 10 minutes
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(oauth.router, prefix="/api/v1/auth", tags=["OAuth"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(content.router, prefix="/api/v1", tags=["Content"])
app.include_router(campaigns.router, prefix="/api/v1", tags=["Campaigns"])
app.include_router(billing.router, prefix="/api/v1", tags=["Billing"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )