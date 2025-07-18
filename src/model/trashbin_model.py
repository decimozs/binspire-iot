from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime


class Trashbin(BaseModel):
    id: str
    org_id: str = Field(..., alias="orgId")
    name: str
    location: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    is_operational: bool = Field(default=False, alias="isOperational")
    is_archive: bool = Field(default=False, alias="isArchive")
    is_collected: bool = Field(default=False, alias="isCollected")
    is_scheduled: bool = Field(default=False, alias="isScheduled")
    scheduled_at: Optional[datetime] = Field(default=None, alias="scheduledAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class TrashbinStatus(BaseModel):
    wasteLevel: int
    weightLevel: float
    batteryLevel: int


class TrashbinMessage(BaseModel):
    trashbin: Trashbin
    status: TrashbinStatus
