"""Request/response models (the HTTP contract) and the stored domain model.

Pydantic gives validation for free: wrong types, missing fields and failed
constraints come back as 422 before your code runs.
"""
import string
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


class VehicleEntryRequest(BaseModel):
    vehicleNumber : str
    vehicleType : str

class VehicleExitRequest(BaseModel):
    ticketId:str
    minutesParked :Decimal


class TicketResponse(BaseModel):
    ticketId : str
    slot : str
    vehicleType: str
    status: str

class FeesResponse(BaseModel):
    ticketID: str
    minutes : Decimal

class Ticket:
    ticketId: str
    slot: str
    vehicleType: str
    status: str
    created_at: datetime= field(default_factory=datetime.now)
    def to_response(self) -> TicketResponse:
        return TicketResponse(
            ticketId=self.ticketId,
            slot=self.slot,
            vehicleType=self.vehicleType,
            status=self.status,
        )


