# app/schemas/order.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    game_id: int | None
    title_snapshot: str
    slug_snapshot: str
    unit_price: Decimal
    discount_percent: int
    final_price: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_code: str
    user_id: int
    status: str
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal
    created_at: datetime
    paid_at: datetime
    items: list[OrderItemRead] = []
