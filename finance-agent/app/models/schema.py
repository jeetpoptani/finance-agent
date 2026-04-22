from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MismatchType(str, Enum):
    price_variance = "price_variance"
    quantity_variance = "quantity_variance"
    duplicate = "duplicate"
    tax_variance = "tax_variance"
    unknown = "unknown"


class InvoiceEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    invoice_id: str = Field(..., min_length=2, max_length=64)
    vendor_id: str = Field(..., min_length=2, max_length=64)
    po_id: str = Field(..., min_length=2, max_length=64)
    grn_id: str = Field(..., min_length=2, max_length=64)
    mismatch_type: MismatchType
    variance_amount: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    detected_at: datetime

    invoice_total: float | None = Field(default=None, ge=0)
    expected_total: float | None = Field(default=None, ge=0)
    quantity_variance_pct: float | None = Field(default=None, ge=0, le=100)
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)

    is_duplicate_suspected: bool = False
    duplicate_invoice_id: str | None = None
    vendor_risk_score: float | None = Field(default=None, ge=0, le=1)
    prior_dispute_count_90d: int = Field(default=0, ge=0)
    invoice_count_90d: int = Field(default=0, ge=0)

    source_system: str | None = None
    region: str | None = None
    business_unit: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchInvoiceRequest(BaseModel):
    invoices: list[InvoiceEvent] = Field(..., min_length=1, max_length=500)


class ProcessResult(BaseModel):
    analysis: dict[str, Any]
    risk_score: float
    decision: str
    result: dict[str, Any]
    meta: dict[str, Any]
