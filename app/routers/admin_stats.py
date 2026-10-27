from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import AdminUser
from app.schemas.stats import MostPurchasedGame, MostWishedGame
from app.services import admin_stats_service

router = APIRouter(prefix="/admin/stats", tags=["admin-stats"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/most-wished", response_model=list[MostWishedGame])
def get_most_wished_games(
    session: SessionDep,
    admin: AdminUser,
    days: Annotated[int | None, Query(ge=1, description="Período en días")] = 30,
    limit: Annotated[int, Query(ge=1, le=50, description="Cantidad máxima de títulos")] = 10,
) -> list[MostWishedGame]:
    return admin_stats_service.get_most_wished(session, days=days, limit=limit)


@router.get("/most-purchased", response_model=list[MostPurchasedGame])
def get_most_purchased_games(
    session: SessionDep,
    admin: AdminUser,
    days: Annotated[int | None, Query(ge=1, description="Período en días")] = 30,
    limit: Annotated[int, Query(ge=1, le=50, description="Cantidad máxima de títulos")] = 10,
) -> list[MostPurchasedGame]:
    return admin_stats_service.get_most_purchased(session, days=days, limit=limit)
