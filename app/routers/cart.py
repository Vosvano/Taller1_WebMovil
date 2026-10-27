# app/routers/cart.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import _bearer_scheme, decode_access_token
from app.models.user import User
from app.repositories.token_blacklist_repository import TokenBlacklistRepository
from app.repositories.user_repository import UserRepository
from app.schemas.cart import AddToCartRequest, CartRead
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["cart"])

SessionDep = Annotated[Session, Depends(get_session)]


def get_optional_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        if TokenBlacklistRepository(session).is_revoked(payload["jti"]):
            return None
        return UserRepository(session).get(int(payload["sub"]))
    except Exception:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
SessionTokenHeader = Annotated[str | None, Header(alias="X-Session-Token")]


def _attach_session_header(response: Response, cart: CartRead) -> CartRead:
    if cart.session_token:
        response.headers["X-Session-Token"] = cart.session_token
    return cart


@router.get("", response_model=CartRead)
def get_cart(
    response: Response,
    session: SessionDep,
    user: OptionalUser,
    session_token: SessionTokenHeader = None,
) -> CartRead:
    cart = CartService(session).get_cart(user=user, session_token=session_token)
    return _attach_session_header(response, cart)


@router.post("/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    payload: AddToCartRequest,
    response: Response,
    session: SessionDep,
    user: OptionalUser,
    session_token: SessionTokenHeader = None,
) -> CartRead:
    cart = CartService(session).add_to_cart(
        user=user, session_token=session_token, game_id=payload.game_id
    )
    return _attach_session_header(response, cart)


@router.delete("/items/{game_id}", response_model=CartRead)
def remove_from_cart(
    game_id: int,
    response: Response,
    session: SessionDep,
    user: OptionalUser,
    session_token: SessionTokenHeader = None,
) -> CartRead:
    cart = CartService(session).remove_from_cart(
        user=user, session_token=session_token, game_id=game_id
    )
    return _attach_session_header(response, cart)


@router.delete("", response_model=CartRead)
def clear_cart(
    response: Response,
    session: SessionDep,
    user: OptionalUser,
    session_token: SessionTokenHeader = None,
) -> CartRead:
    cart = CartService(session).clear_cart(user=user, session_token=session_token)
    return _attach_session_header(response, cart)
