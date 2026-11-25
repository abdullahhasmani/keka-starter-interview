"""Request/response models (the HTTP contract) and the stored domain model.

Pydantic gives validation for free: wrong types, missing fields and failed
constraints come back as 422 before your code runs.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


# ---------- HTTP layer: what clients send / receive ----------
class CreateAccountRequest(BaseModel):
    owner_name: str = Field(min_length=1, max_length=100)
    initial_balance: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)

    @field_validator("owner_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("owner_name must not be blank")
        return v


class DepositRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)


class AccountResponse(BaseModel):
    id: str
    owner_name: str
    balance: Decimal
    created_at: datetime


# ---------- Domain model: what we store ----------
@dataclass
class Account:
    id: str
    owner_name: str
    balance: Decimal
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_response(self) -> AccountResponse:
        return AccountResponse(
            id=self.id,
            owner_name=self.owner_name,
            balance=self.balance,
            created_at=self.created_at,
        )
