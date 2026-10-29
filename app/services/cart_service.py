# app/services/cart_service.py
from __future__ import annotations

from decimal import Decimal

from sqlmodel import Session, select

from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import utcnow
from app.models.game_image import GameImage
from app.models.library_item import LibraryItem
from app.models.user import User
from app.repositories.cart_repository import CartRepository
from app.repositories.game_repository import GameRepository
from app.repositories.offer_repository import (
    compute_effective_price,
    get_active_offer_for_game,
)
from app.schemas.cart import CartItemRead, CartRead


class CartService:
    def __init__(self, session: Session):
        self.session = session
        self.cart_repo = CartRepository(session)
        self.game_repo = GameRepository(session)

    def _resolve_cart(self, *, user: User | None, session_token: str | None):
        if user:
            cart = self.cart_repo.get_or_create_user_cart(user.id)
            if session_token:
                self.cart_repo.merge_guest_into_user_cart(
                    user_cart_id=cart.id, guest_session_token=session_token
                )
            return cart
        return self.cart_repo.get_or_create_guest_cart(session_token)

    def _build_cart_response(self, cart) -> CartRead:
        cart_items = self.cart_repo.get_cart_items(cart.id)

        read_items: list[CartItemRead] = []
        subtotal = Decimal("0.00")
        total = Decimal("0.00")
        now = utcnow()

        for item in cart_items:
            game = self.game_repo.get(item.game_id)
            if not game or game.deleted_at is not None or not game.is_active:
                continue

            active_offer = get_active_offer_for_game(self.session, game.id, now)
            final_price, discount_percent = compute_effective_price(game.base_price, active_offer)
            has_offer = active_offer is not None

            cover_url = self.session.exec(
                select(GameImage.url)
                .where(GameImage.game_id == game.id)
                .order_by(GameImage.is_cover.desc(), GameImage.sort_order.asc())
            ).first()

            read_items.append(
                CartItemRead(
                    game_id=game.id,
                    title=game.title,
                    slug=game.slug,
                    platform=game.platform,
                    cover_image_url=cover_url,
                    base_price=game.base_price,
                    discount_percent=discount_percent,
                    final_price=final_price,
                    has_active_offer=has_offer,
                )
            )
            subtotal += game.base_price
            total += final_price

        return CartRead(
            items=read_items,
            subtotal=subtotal,
            discount_total=subtotal - total,
            total=total,
            session_token=cart.session_token,
        )

    def get_cart(self, *, user: User | None, session_token: str | None) -> CartRead:
        cart = self._resolve_cart(user=user, session_token=session_token)
        return self._build_cart_response(cart)

    def add_to_cart(
        self, *, user: User | None, session_token: str | None, game_id: int
    ) -> CartRead:
        game = self.game_repo.get(game_id)
        if not game or game.deleted_at is not None or not game.is_active:
            raise NotFoundError("El juego no está disponible en el catálogo.")

        if user:
            owned = self.session.exec(
                select(LibraryItem).where(
                    LibraryItem.user_id == user.id, LibraryItem.game_id == game_id
                )
            ).first()
            if owned:
                raise ConflictError("Ya posees este juego en tu biblioteca.")

        cart = self._resolve_cart(user=user, session_token=session_token)
        self.cart_repo.add_item(cart.id, game_id)
        return self._build_cart_response(cart)

    def remove_from_cart(
        self, *, user: User | None, session_token: str | None, game_id: int
    ) -> CartRead:
        cart = self._resolve_cart(user=user, session_token=session_token)
        self.cart_repo.remove_item(cart.id, game_id)
        return self._build_cart_response(cart)

    def clear_cart(self, *, user: User | None, session_token: str | None) -> CartRead:
        cart = self._resolve_cart(user=user, session_token=session_token)
        self.cart_repo.clear_cart(cart.id)
        return self._build_cart_response(cart)
