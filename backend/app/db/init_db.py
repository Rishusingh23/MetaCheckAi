import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import logger
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import async_engine, AsyncSessionLocal
from app.models.user import Role, User, RoleEnum
from app.models.product import Product
from app.services.rules.seed_rules import seed_statutory_baseline_rules


async def init_database():
    """
    Initializes database schema and seeds initial roles, administrative/officer users,
    and official statutory baseline rules.
    """
    logger.info("Initializing database schema...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # 1. Seed Standard Roles
        roles_data = [
            (RoleEnum.ADMIN.value, "Administrator with full system and rule management authority"),
            (RoleEnum.ENFORCEMENT_OFFICER.value, "Legal Metrology Enforcement Officer with inspection and review authority"),
            (RoleEnum.VIEWER.value, "Read-only auditor with dashboard and report access"),
        ]
        
        role_map = {}
        for role_name, description in roles_data:
            stmt = select(Role).where(Role.name == role_name)
            res = await db.execute(stmt)
            role_obj = res.scalar_one_or_none()
            if not role_obj:
                role_obj = Role(
                    id=str(uuid.uuid4()),
                    name=role_name,
                    description=description,
                )
                db.add(role_obj)
                await db.flush()
            role_map[role_name] = role_obj

        # 2. Seed Default Users for Local Testing & SIH Evaluation
        users_data = [
            ("admin@metacheck.gov.in", "Admin@123", "Shri R. K. Sharma", RoleEnum.ADMIN.value, "Department of Consumer Affairs"),
            ("officer@metacheck.gov.in", "Officer@123", "Inspector A. Verma", RoleEnum.ENFORCEMENT_OFFICER.value, "Legal Metrology Field Unit 1"),
            ("viewer@metacheck.gov.in", "Viewer@123", "Auditor S. Nair", RoleEnum.VIEWER.value, "Compliance Audit Wing"),
        ]

        for email, password, full_name, role_name, dept in users_data:
            stmt = select(User).where(User.email == email)
            res = await db.execute(stmt)
            user_obj = res.scalar_one_or_none()
            if not user_obj:
                user_obj = User(
                    id=str(uuid.uuid4()),
                    email=email,
                    name=full_name,
                    password_hash=hash_password(password),
                    role_id=role_map[role_name].id,
                    is_active=True,
                )
                db.add(user_obj)

        await db.commit()

        # 3. Seed Statutory Baseline Rules
        seeded_rules = await seed_statutory_baseline_rules(db)
        logger.info(f"Database initialized. Statutory baseline rules checked/seeded: {seeded_rules}")

        # 4. Seed sample products in development if product table empty
        prod_stmt = select(Product).limit(1)
        prod_res = await db.execute(prod_stmt)
        if prod_res.scalar_one_or_none() is None:
            sample_products = [
                Product(
                    id=str(uuid.uuid4()),
                    name="Classic Salted Potato Wafers (100g)",
                    brand="CrispBite",
                    manufacturer="CrispBite Foods Pvt Ltd, Plot 12, Industrial Area, Sector 58, Gurugram, Haryana 122001",
                    country_of_origin="India",
                    category="Food & Beverages",
                ),
                Product(
                    id=str(uuid.uuid4()),
                    name="Imported Swiss Dark Chocolate 85% (150g)",
                    brand="AlpenChoc",
                    manufacturer="Alpen Confectionery SA, Zurich, Switzerland",
                    importer="Global Foods Import Corp, Unit 4B, Maritime Gateway, Ballard Estate, Mumbai, Maharashtra 400001",
                    country_of_origin="Switzerland",
                    category="Food & Beverages",
                ),
                Product(
                    id=str(uuid.uuid4()),
                    name="Organic Whole Rolled Oats (1kg)",
                    brand="NutriGrain",
                    manufacturer="NutriGrain Agro Ltd, Village Kheri, NH-1, Sonipat, Haryana 131001",
                    country_of_origin="India",
                    category="Food & Beverages",
                ),
            ]
            for p in sample_products:
                db.add(p)
            await db.commit()
            logger.info("Sample product repository catalog seeded.")
