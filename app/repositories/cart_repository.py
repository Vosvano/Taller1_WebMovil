# app/repositories/cart_repository.py
from __future__ import annotations

import secrets

from sqlmodel import Session, select

from app.models.cart import Cart
from app.models.cart_item import CartItem


class CartRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create_user_cart(self, user_id: int) -> Cart:
        statement = select(Cart).where(Cart.user_id == user_id)
        cart = self.session.exec(statement).first()
        if cart is None:
            cart = Cart(user_id=user_id)
            self.session.add(cart)
            self.session.commit()
            self.session.refresh(cart)
        return cart

    def get_or_create_guest_cart(self, session_token: str | None = None) -> Cart:
        if session_token:
            statement = select(Cart).where(Cart.session_token == session_token)
            cart = self.session.exec(statement).first()
            if cart:
                return cart

        new_token = secrets.token_hex(32)
        cart = Cart(session_token=new_token)
        self.session.add(cart)
        self.session.commit()
        self.session.refresh(cart)
        return cart

    def get_cart_items(self, cart_id: int) -> list[CartItem]:
        statement = select(CartItem).where(CartItem.cart_id == cart_id)
        return list(self.session.exec(statement).all())

    def add_item(self, cart_id: int, game_id: int) -> CartItem:
        statement = select(CartItem).where(CartItem.cart_id == cart_id, CartItem.game_id == game_id)
        existing = self.session.exec(statement).first()
        if existing:
            return existing

        item = CartItem(cart_id=cart_id, game_id=game_id)
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def remove_item(self, cart_id: int, game_id: int) -> bool:
        statement = select(CartItem).where(CartItem.cart_id == cart_id, CartItem.game_id == game_id)
        item = self.session.exec(statement).first()
        if not item:
            return False
        self.session.delete(item)
        self.session.commit()
        return True

    def clear_cart(self, cart_id: int) -> None:
        statement = select(CartItem).where(CartItem.cart_id == cart_id)
        for item in self.session.exec(statement).all():
            self.session.delete(item)
        self.session.commit()

    def merge_guest_into_user_cart(self, *, user_cart_id: int, guest_session_token: str) -> None:
        statement = select(Cart).where(Cart.session_token == guest_session_token)
        guest_cart = self.session.exec(statement).first()
        if not guest_cart:
            return

        guest_items = self.get_cart_items(guest_cart.id)
        for item in guest_items:
            self.add_item(user_cart_id, item.game_id)

        self.session.delete(guest_cart)
        self.session.commit()
