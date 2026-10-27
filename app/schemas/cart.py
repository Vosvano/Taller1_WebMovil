# app/schemas/cart.py
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game_id: int
    title: str
    slug: str
    platform: str
    cover_image_url: str | None = None
    base_price: Decimal
    discount_percent: int = 0
    final_price: Decimal
    has_active_offer: bool = False


class CartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[CartItemRead] = []
    subtotal: Decimal = Decimal("0.00")
    discount_total: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
    session_token: str | None = None


class AddToCartRequest(BaseModel):
    game_id: int = Field(gt=0, description="ID del juego a agregar")
