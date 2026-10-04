from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import register_exception_handlers
from app.api.v1.router import api_router
from app.api.v1.endpoints.health import get_health_status
from app.schemas.health import HealthResponse


from app.db.init_db import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle manager."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    logger.info(f"Configured CORS origins: {settings.BACKEND_CORS_ORIGINS}")
    try:
        await init_database()
    except Exception as e:
        logger.warning(f"Database auto-initialization skipped or encountered: {e}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


def create_application() -> FastAPI:
    """Factory function to build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        description=(
            "MetaCheck AI — AI-Assisted Legal Metrology Compliance Inspection Platform.\n"
            "Provides automated screening of packaged commodity declarations against "
            "Legal Metrology (Packaged Commodities) Rules."
        ),
        lifespan=lifespan,
    )

    # Configure CORS middleware
    origins = (
        settings.BACKEND_CORS_ORIGINS
        if isinstance(settings.BACKEND_CORS_ORIGINS, list)
        else [settings.BACKEND_CORS_ORIGINS]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Exception Handlers
    register_exception_handlers(app)

    # Direct health check endpoints (/api/health and /health)
    app.add_api_route(
        "/api/health",
        get_health_status,
        methods=["GET"],
        response_model=HealthResponse,
        tags=["Health"],
        summary="Root API Health Check",
    )
    app.add_api_route(
        "/health",
        get_health_status,
        methods=["GET"],
        response_model=HealthResponse,
        tags=["Health"],
        summary="Service Health Check",
        include_in_schema=False,
    )

    # Mount API v1 router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_application()
