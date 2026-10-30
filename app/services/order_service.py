# app/services/order_service.py
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from fastapi import BackgroundTasks
from sqlmodel import Session, func, select

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.time import utcnow
from app.integrations.resend_client import _send
from app.models.enums import OrderStatus
from app.models.game import Game
from app.models.library_item import LibraryItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.repositories.cart_repository import CartRepository
from app.repositories.game_repository import GameRepository
from app.repositories.offer_repository import (
    compute_effective_price,
    get_active_offer_for_game,
)
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderItemRead, OrderRead

logger = logging.getLogger(__name__)


def _generate_order_code(session: Session) -> str:
    year = utcnow().year
    count = session.exec(select(func.count()).select_from(Order)).one()
    return f"GV-{year}-{count + 1:06d}"


class OrderService:
    def __init__(self, session: Session):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.cart_repo = CartRepository(session)
        self.game_repo = GameRepository(session)

    def _build_order_read(self, order: Order) -> OrderRead:
        items = self.order_repo.get_order_items(order.id)
        items_read = [OrderItemRead.model_validate(it) for it in items]

        order_dict = order.model_dump()
        order_dict["status"] = (
            order.status.value if hasattr(order.status, "value") else str(order.status)
        )
        order_dict["items"] = items_read
        return OrderRead.model_validate(order_dict)

    def get_user_orders(self, user_id: int) -> list[OrderRead]:
        orders = self.order_repo.get_user_orders(user_id)
        return [self._build_order_read(o) for o in orders]

    def get_order_by_code(self, order_code: str, user_id: int) -> OrderRead:
        order = self.order_repo.get_by_code(order_code=order_code, user_id=user_id)
        if not order:
            raise NotFoundError("La orden solicitada no existe o no te pertenece.")
        return self._build_order_read(order)

    def checkout(
        self,
        *,
        user: User,
        idempotency_key: str | None = None,
        background_tasks: BackgroundTasks | None = None,
    ) -> OrderRead:
        key = idempotency_key or str(uuid.uuid4())
        existing_order = self.order_repo.get_by_idempotency_key(user.id, key)
        if existing_order:
            logger.info(
                "Checkout idempotente: devolviendo orden previa %s", existing_order.order_code
            )
            return self._build_order_read(existing_order)

        cart = self.cart_repo.get_or_create_user_cart(user.id)
        cart_items = self.cart_repo.get_cart_items(cart.id)
        if not cart_items:
            raise ValidationError("El carrito está vacío. Agrega juegos antes de comprar.")

        now = utcnow()
        games_to_buy: list[tuple[Game, Decimal, int, Decimal]] = []
        subtotal = Decimal("0.00")
        total = Decimal("0.00")

        for ci in cart_items:
            game = self.game_repo.get(ci.game_id)
            if not game or game.deleted_at is not None or not game.is_active:
                raise ValidationError(f"El juego con ID {ci.game_id} ya no está disponible.")

            already_owned = self.session.exec(
                select(LibraryItem).where(
                    LibraryItem.user_id == user.id,
                    LibraryItem.game_id == game.id,
                )
            ).first()
            if already_owned:
                raise ConflictError(f"Ya posees el juego '{game.title}' en tu biblioteca.")

            active_offer = get_active_offer_for_game(self.session, game.id, now)
            final_price, discount_pct = compute_effective_price(game.base_price, active_offer)

            games_to_buy.append((game, game.base_price, discount_pct, final_price))
            subtotal += game.base_price
            total += final_price

        discount_total = subtotal - total

        order_code = _generate_order_code(self.session)
        order = Order(
            order_code=order_code,
            user_id=user.id,
            status=OrderStatus.PAID,
            subtotal=subtotal,
            discount_total=discount_total,
            total=total,
            idempotency_key=key,
            created_at=now,
            paid_at=now,
        )
        self.order_repo.create_order(order)

        for game, unit_price, discount_pct, final_price in games_to_buy:
            order_item = OrderItem(
                order_id=order.id,
                game_id=game.id,
                title_snapshot=game.title,
                slug_snapshot=game.slug,
                unit_price=unit_price,
                discount_percent=discount_pct,
                final_price=final_price,
            )
            self.order_repo.add_order_item(order_item)
            self.order_repo.add_to_library(user_id=user.id, game_id=game.id, order_id=order.id)

        self.cart_repo.clear_cart(cart.id)

        self.session.commit()
        self.session.refresh(order)

        if background_tasks:
            background_tasks.add_task(
                self._send_purchase_confirmation,
                to_email=user.email,
                order_code=order.order_code,
                total=str(order.total),
            )

        return self._build_order_read(order)

    @staticmethod
    def _send_purchase_confirmation(*, to_email: str, order_code: str, total: str) -> None:
        subject = f"Confirmación de compra - {order_code}"
        html = (
            f"<h2>¡Gracias por tu compra en GameVault UCN!</h2>"
            f"<p>Tu orden <strong>{order_code}</strong> ha sido procesada con éxito.</p>"
            f"<p>Total pagado: <strong>${total}</strong></p>"
            f"<p>Los juegos adquiridos ya están disponibles en tu biblioteca personal.</p>"
        )
        try:
            _send(to_email=to_email, subject=subject, html=html)
        except Exception as e:
            logger.error("Error al enviar correo de confirmación de orden %s: %s", order_code, e)
