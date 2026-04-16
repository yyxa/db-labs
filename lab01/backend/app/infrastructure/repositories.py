"""Реализация репозиториев с использованием SQLAlchemy."""

import uuid
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import text, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.domain.user import User
from app.domain.order import Order, OrderItem, OrderStatus, OrderStatusChange


class UserRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, user: User) -> None:
        stmt = pg_insert(User.__table__).values(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
        ).on_conflict_do_update(
            index_elements=['email'],
            set_={
                'name': user.name,
                'created_at': user.created_at,
            }
        )
        await self.session.execute(stmt)

    async def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def find_all(self) -> List[User]:
        result = await self.session.execute(select(User))
        return result.scalars().all()


class OrderRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, order: Order) -> None:
        await self.session.execute(
            update(Order.__table__).where(Order.id == order.id).values(
                status=order.status.value,
                total_amount=order.total_amount,
            )
        ) if order.id else await self.session.execute(
            insert(Order.__table__).values(
                id=order.id,
                user_id=order.user_id,
                status=order.status.value,
                total_amount=order.total_amount,
                created_at=order.created_at,
            )
        )

        for item in order.items:
            await self.session.execute(
                pg_insert(OrderItem.__table__)
                .values(
                    id=item.id,
                    order_id=order.id,
                    product_name=item.product_name,
                    price=item.price,
                    quantity=item.quantity,
                )
                .on_conflict_do_update(
                    index_elements=['id'],
                    set_={
                        'product_name': item.product_name,
                        'price': item.price,
                        'quantity': item.quantity,
                    }
                )
            )

        for change in order.status_history:
            await self.session.execute(
                insert(OrderStatusChange.__table__).values(
                    id=change.id,
                    order_id=change.order_id,
                    status=change.status.value,
                    changed_at=change.changed_at,
                ).on_conflict_do_nothing()
            )

    async def find_by_id(self, order_id: uuid.UUID) -> Optional[Order]:
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        db_order = result.scalar_one_or_none()
        if not db_order:
            return None

        items = await self.session.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        history = await self.session.execute(
            select(OrderStatusChange)
            .where(OrderStatusChange.order_id == order_id)
            .order_by(OrderStatusChange.changed_at)
        )

        order = object.__new__(Order)
        order.__dict__.update({
            'id': db_order.id,
            'user_id': db_order.user_id,
            'status': OrderStatus(db_order.status),
            'total_amount': db_order.total_amount,
            'created_at': db_order.created_at,
            'items': items.scalars().all(),
            'status_history': history.scalars().all(),
        })
        return order

    async def find_by_user(self, user_id: uuid.UUID) -> List[Order]:
        result = await self.session.execute(
            select(Order).where(Order.user_id == user_id)
        )
        return result.scalars().all()

    async def find_all(self) -> List[Order]:
        result = await self.session.execute(select(Order))
        return result.scalars().all()
