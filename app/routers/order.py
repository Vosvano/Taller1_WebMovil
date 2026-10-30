from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import CurrentUser
from app.schemas.order import OrderRead
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/checkout", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def checkout(
    current_user: CurrentUser,
    session: SessionDep,
    background_tasks: BackgroundTasks,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> OrderRead:

    service = OrderService(session)
    return service.checkout(
        user=current_user,
        idempotency_key=idempotency_key,
        background_tasks=background_tasks,
    )


@router.get("", response_model=list[OrderRead])
def get_orders(
    current_user: CurrentUser,
    session: SessionDep,
) -> list[OrderRead]:
    service = OrderService(session)
    return service.get_user_orders(current_user.id)


@router.get("/{order_code}", response_model=OrderRead)
def get_order_detail(
    order_code: str,
    current_user: CurrentUser,
    session: SessionDep,
) -> OrderRead:
    service = OrderService(session)
    return service.get_order_by_code(order_code=order_code, user_id=current_user.id)
