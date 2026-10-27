from datetime import datetime

from sqlmodel import Session, func, select

from app.models.enums import OrderStatus
from app.models.game import Game
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.wishlist_item import WishlistItem


class StatsRepository:
    def __initit__(self, session: Session):
        self.session = session

    def get_most_wished_games(
        self, *, since: datetime | None = None, limit: int = 10
    ) -> list[tuple[Game, int]]:
        query = (
            select(Game, func.count(WishlistItem.id).label("wishlist_count"))
            .join(WishlistItem, WishlistItem.game_id == Game.id)
            .group_by(Game.id)
            .order_by(func.count(WishlistItem.id).desc())
            .limit(limit)
        )
        if since is not None:
            query = query.where(WishlistItem.created_at >= since)

        return list(self.session.exec(query).all())

    def get_most_purchased_games(
        self, *, since: datetime | None = None, limit: int = 10
    ) -> list[tuple[int, str, str, int]]:
        query = (
            select(
                OrderItem.game_id,
                OrderItem.title_snapshot.label("title"),
                OrderItem.slug_snapshot.label("slug"),
                func.count(OrderItem.id).label("sales_count"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.status == OrderStatus.PAID)
            .where(OrderItem.game_id.is_not(None))
            .group_by(OrderItem.game_id, OrderItem.title_snapshot, OrderItem.slug_snapshot)
            .order_by(func.count(OrderItem.id).desc())
            .limit(limit)
        )
        if since is not None:
            query = query.where(Order.created_at >= since)
        return list(self.session.exec(query).all())
