import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.config import get_settings
from app.core.logging import logger

# Import all models to ensure tables are created
from app.models import *

# Import routers
from app.routers import auth, projects, logs, dashboard, ai, parsers, settings, alerts

app_settings = get_settings()

# Create tables (skipped during alembic autogeneration)
if not os.environ.get("SKIP_TABLE_CREATE"):
    Base.metadata.create_all(bind=engine)

# Swagger/ReDoc docs only enabled in non-production environments
docs_url = "/api/docs" if app_settings.is_docs_enabled else None
redoc_url = "/api/redoc" if app_settings.is_docs_enabled else None
openapi_url = "/api/openapi.json" if app_settings.is_docs_enabled else None

app = FastAPI(
    title=app_settings.APP_NAME,
    version=app_settings.VERSION,
    description="AI-powered log management and analysis platform",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

# CORS — origins from .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(parsers.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "version": app_settings.VERSION}

@app.get("/api/info")
def app_info():
    return {
        "name": app_settings.APP_NAME,
        "version": app_settings.VERSION,
        "features": [
            "multi-project support",
            "AI log analysis",
            "real-time monitoring",
            "advanced search",
            "alert rules",
            "custom parsers"
        ]
    }

# Seed default data on startup
@app.on_event("startup")
async def startup_event():
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models.user import User, UserRole
    from app.models.ai import AIProvider
    from app.core.security import get_password_hash

    db = SessionLocal()
    try:
        # Create default admin if no users exist
        user_count = db.query(User).count()
        if user_count == 0:
            admin = User(
                username="admin",
                email="admin@logmorph.ai",
                full_name="Administrator",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=True
            )
            db.add(admin)
            logger.info("Created default admin user: admin/admin123")

        # Create sample AI providers
        provider_count = db.query(AIProvider).count()
        if provider_count == 0:
            providers = [
                AIProvider(
                    name="Ollama (Local)",
                    provider_type="ollama",
                    base_url=app_settings.OLLAMA_HOST,
                    model="llama3",
                    is_enabled=True
                ),
                AIProvider(
                    name="OpenAI",
                    provider_type="openai",
                    model="gpt-4o",
                    is_enabled=False
                ),
                AIProvider(
                    name="Anthropic Claude",
                    provider_type="anthropic",
                    model="claude-3-sonnet-20240229",
                    is_enabled=False
                )
            ]
            for p in providers:
                db.add(p)
            logger.info("Created default AI providers")

        db.commit()
    except Exception as e:
        logger.error(f"Startup error: {e}")
        db.rollback()
    finally:
        db.close()

@app.on_event("shutdown")
async def shutdown_event():
    from app.services.watcher_service import file_watcher
    file_watcher.stop_all()
    logger.info("Application shutdown")
