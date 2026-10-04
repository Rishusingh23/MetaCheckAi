from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.products import router as products_router
from app.api.v1.endpoints.inspections import router as inspections_router
from app.api.v1.endpoints.scans import router as scans_router
from app.api.v1.endpoints.images import router as images_router
from app.api.v1.endpoints.rules import router as rules_router
from app.api.v1.endpoints.violations import router as violations_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.roles import router as roles_router
from app.api.v1.endpoints.declarations import router as declarations_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.demo import router as demo_router

api_router = APIRouter()

# Include version 1 endpoint routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard & Analytics"])
api_router.include_router(demo_router, prefix="/demo", tags=["SIH Demonstration"])
api_router.include_router(products_router, prefix="/products", tags=["Products"])
api_router.include_router(inspections_router, prefix="/inspections", tags=["Inspections"])
api_router.include_router(scans_router, prefix="/scans", tags=["Scans & OCR Pipeline"])
api_router.include_router(images_router, prefix="/images", tags=["Images & Quality Analytics"])
api_router.include_router(declarations_router, tags=["Declarations & Normalization"])
api_router.include_router(rules_router, prefix="/rules", tags=["Rules"])
api_router.include_router(violations_router, prefix="/violations", tags=["Violations"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(roles_router, prefix="/roles", tags=["Roles"])

