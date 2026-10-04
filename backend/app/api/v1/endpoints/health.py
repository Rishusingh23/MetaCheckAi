import os
import tempfile
from fastapi import APIRouter
from app.core.config import settings
from app.db.session import check_db_health
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Health Check",
    description="Returns detailed operational status including database connectivity, storage availability, and version info.",
)
async def get_health_status() -> HealthResponse:
    """
    Check application status, database connectivity, and local storage read/write availability.
    """
    db_ok = await check_db_health()

    # Check storage availability
    storage_ok = True
    try:
        test_dir = tempfile.gettempdir()
        test_file = os.path.join(test_dir, ".health_check_probe")
        with open(test_file, "w") as f:
            f.write("probe")
        os.remove(test_file)
    except Exception:
        storage_ok = False

    overall_status = "healthy" if (db_ok and storage_ok) else "degraded"

    return HealthResponse(
        status=overall_status,
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database_connected=db_ok,
        services={
            "api": "healthy",
            "database": "connected" if db_ok else "disconnected",
            "storage": "writable" if storage_ok else "error",
            "ocr_engine": settings.OCR_ENGINE,
        },
    )
