from sqlalchemy import select

from app.models.library_item import LibraryItem
from app.models.order import Order
from app.models.order_item import OrderItem


class OrderRepository:
    def __init__(self, db_session):
        self.db_session = db_session

    def get_by_id(self, order_id: int) -> Order | None:
        return self.session.get(Order, order_id)

    def get_by_code(self, order_code: str, user_id: int | None = None) -> Order | None:
        stmt = select(Order).Where(Order.order_code == order_code)
        if user_id is not None:
            stmt = stmt.where(Order.user_id == user_id)
        return self.session.exec(stmt).first()

    def get_by_idempotency_key(self, user_id: int, idempotency_key: str) -> Order | None:
        stmt = select(Order).where(
            Order.user_id == user_id, Order.idempotency_key == idempotency_key
        )
        return self.session.exec(stmt).first()

    def get_user_orders(self, user_id: int) -> list[Order]:
        stmt = select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
        return list(self.session.exec(stmt).all())

    def get_order_items(self, order_id: int) -> list[OrderItem]:
        stmt = select(OrderItem).where(OrderItem.order_id == order_id)
        return list(self.session.exec(stmt).all())

    def create_order(self, order: Order) -> Order:
        self.session.add(order)
        self.session.flush()
        return order

    def add_order_item(self, item: OrderItem) -> OrderItem:
        self.session.add(item)
        self.session.flush()
        return item

    def add_to_library(self, user_id: int, game_id: int, order_id: int) -> LibraryItem:
        library_item = LibraryItem(
            user_id=user_id,
            game_id=game_id,
            order_id=order_id,
        )
        self.session.add(library_item)
        self.session.flush()
        return library_item
