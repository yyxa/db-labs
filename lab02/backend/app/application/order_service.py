"""Сервис для работы с заказами."""

import uuid
from decimal import Decimal
from typing import List, Optional

from app.domain.order import Order, OrderItem, OrderStatus
from app.domain.exceptions import (
    OrderNotFoundError,
    UserNotFoundError,
    OrderAlreadyPaidError,
    OrderCancelledError,
    InvalidAmountError,
)


class OrderService:
    def __init__(self, order_repo, user_repo):
        self.order_repo = order_repo
        self.user_repo = user_repo

    async def create_order(self, user_id: uuid.UUID) -> Order:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User with id {user_id} not found")

        order = Order(user_id=user_id)

        await self.order_repo.save(order)

        return order

    async def get_order(self, order_id: uuid.UUID) -> Order:
        order = await self.order_repo.find_by_id(order_id)
        if not order:
            raise OrderNotFoundError(f"Order with id {order_id} not found")
        return order

    async def add_item(
        self,
        order_id: uuid.UUID,
        product_name: str,
        price: Decimal,
        quantity: int,
    ) -> OrderItem:
        order = await self.get_order(order_id)

        item = order.add_item(product_name, price, quantity)

        await self.order_repo.save(order)

        return item

    async def pay_order(self, order_id: uuid.UUID) -> Order:
        order = await self.get_order(order_id)

        try:
            order.pay()
        except (OrderAlreadyPaidError, OrderCancelledError, InvalidAmountError) as e:
            raise

        await self.order_repo.save(order)

        return order

    async def cancel_order(self, order_id: uuid.UUID) -> Order:
        order = await self.get_order(order_id)
        order.cancel()
        await self.order_repo.save(order)
        return order

    async def ship_order(self, order_id: uuid.UUID) -> Order:
        order = await self.get_order(order_id)
        order.ship()
        await self.order_repo.save(order)
        return order

    async def complete_order(self, order_id: uuid.UUID) -> Order:
        order = await self.get_order(order_id)
        order.complete()
        await self.order_repo.save(order)
        return order

    async def list_orders(self, user_id: Optional[uuid.UUID] = None) -> List[Order]:
        if user_id:
            return await self.order_repo.find_by_user(user_id)
        return await self.order_repo.find_all()

    async def get_order_history(self, order_id: uuid.UUID) -> List:
        order = await self.get_order(order_id)
        return list(order.status_history)
