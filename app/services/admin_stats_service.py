from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session

from app.core.time import utcnow
from app.repositories.stats_repository import StatsRepository
from app.schemas.stats import MostPurchasedGame, MostWishedGame


def get_most_wished(
    session: Session, *, days: int | None = 30, limit: int = 10
) -> list[MostWishedGame]:
    stats_repo = StatsRepository(session)
    since = utcnow() - timedelta(days=days) if days and days > 0 else None

    results = stats_repo.get_most_wished_games(since=since, limit=limit)

    return [
        MostWishedGame(
            id=game.id,
            title=game.title,
            slug=game.slug,
            wishlist_count=count,
        )
        for game, count in results
    ]


def get_most_purchased(
    session: Session, *, days: int | None = 30, limit: int = 10
) -> list[MostPurchasedGame]:
    stats_repo = StatsRepository(session)
    since = utcnow() - timedelta(days=days) if days and days > 0 else None

    results = stats_repo.get_most_purchased_games(since=since, limit=limit)

    return [
        MostPurchasedGame(
            id=game_id,
            title=title,
            slug=slug,
            sales_count=count,
        )
        for game_id, title, slug, count in results
    ]
