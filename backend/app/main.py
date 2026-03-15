"""InfraGen — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas.common import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    print(f"🚀 {settings.app_name} starting up (env={settings.app_env})")
    yield
    # Shutdown
    print(f"👋 {settings.app_name} shutting down")


app = FastAPI(
    title=settings.app_name,
    description="AI-powered infrastructure-as-code generation platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — permissive in development, restricted in production
cors_origins = (
    ["*"] if settings.app_env == "development"
    else settings.backend_cors_origins
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


# Mount API routers
from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as projects_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
