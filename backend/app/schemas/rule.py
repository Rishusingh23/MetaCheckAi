from datetime import datetime
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from app.models.rule import (
    ApplicableContextEnum,
    RuleVerificationStatusEnum,
    SeverityEnum,
    ValidationTypeEnum,
)


class RuleVersionBase(BaseModel):
    version: str = Field(min_length=1, max_length=50, description="Version tag, e.g. 1.0.0 or 2022_AMENDMENT")
    requirement_text: str = Field(min_length=1, description="Official statutory requirement statement")
    conditions: Optional[dict] = Field(default=None, description="Logical conditions / parameters")
    applicable_product_categories: Optional[Union[dict, list]] = Field(default=None, description="Categories where rule applies")
    applicable_contexts: Optional[Union[dict, list]] = Field(
        default=None,
        description="Applicability contexts, e.g. PHYSICAL_PACKAGE, E_COMMERCE_LISTING, IMPORTED_PRODUCT, DOMESTIC_PRODUCT",
    )
    validation_type: ValidationTypeEnum = Field(default=ValidationTypeEnum.PRESENCE_CHECK)
    severity: SeverityEnum = Field(default=SeverityEnum.MAJOR)
    verification_status: RuleVerificationStatusEnum = Field(
        default=RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
        description="Statutory authenticity state: VERIFIED_OFFICIAL, NEEDS_LEGAL_REVIEW, DEPRECATED",
    )
    evidence_required: bool = Field(default=True)
    source_document: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Official Department of Consumer Affairs statutory source publication",
    )
    source_gazette_reference: Optional[str] = Field(default=None, max_length=500)
    active_from: Optional[datetime] = None
    active_to: Optional[datetime] = None


class RuleVersionCreate(RuleVersionBase):
    rule_id: str


class RuleVersionRead(RuleVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_id: str
    created_at: datetime


class RuleBase(BaseModel):
    rule_code: str = Field(min_length=1, max_length=100, description="Unique statutory identifier, e.g. PCR_2011_RULE_6_1_A")
    name: str = Field(min_length=1, max_length=255, description="Rule display name")
    description: Optional[str] = Field(default=None)
    legal_reference: str = Field(min_length=1, max_length=500, description="Authoritative statutory source reference")
    is_active: bool = Field(default=True)


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    legal_reference: Optional[str] = Field(default=None, min_length=1, max_length=500)
    is_active: Optional[bool] = None


class RuleRead(RuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class RuleDetailRead(RuleRead):
    versions: List[RuleVersionRead] = []
