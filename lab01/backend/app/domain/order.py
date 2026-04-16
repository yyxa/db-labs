"""Доменные сущности заказа."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List
from dataclasses import dataclass, field

from .exceptions import (
    OrderAlreadyPaidError,
    OrderCancelledError,
    InvalidQuantityError,
    InvalidPriceError,
    InvalidAmountError,
)


class OrderStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    CANCELLED = "cancelled"
    SHIPPED = "shipped"
    COMPLETED = "completed"


@dataclass
class OrderItem:
    product_name: str
    price: Decimal
    quantity: int
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    order_id: uuid.UUID = field(default=None)

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise InvalidQuantityError("Quantity must be > 0")
        if self.price < 0:
            raise InvalidPriceError("Price must be >= 0")

    @property
    def subtotal(self) -> Decimal:
        return self.price * self.quantity


@dataclass
class OrderStatusChange:
    order_id: uuid.UUID
    status: OrderStatus
    changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class Order:
    user_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: OrderStatus = OrderStatus.CREATED
    total_amount: Decimal = Decimal("0.00")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    items: List[OrderItem] = field(default_factory=list)
    status_history: List[OrderStatusChange] = field(default_factory=list)

    def add_item(self, product_name: str, price: Decimal, quantity: int) -> OrderItem:
        if self.status != OrderStatus.CREATED:
            if self.status == OrderStatus.CANCELLED:
                raise OrderCancelledError(self.id)
            else:
                raise ValueError(f"Cannot add items to {self.status.value} order")

        item = OrderItem(
            product_name=product_name,
            price=price,
            quantity=quantity,
            order_id=self.id
        )
        self.items.append(item)
        self._recalculate_total()
        return item

    def _recalculate_total(self) -> None:
        self.total_amount = sum(item.subtotal for item in self.items)

    def pay(self) -> None:
        if self.status == OrderStatus.PAID:
            raise OrderAlreadyPaidError(self.id)
        
        if self.status == OrderStatus.CANCELLED:
            raise OrderCancelledError(self.id)
        
        if self.total_amount < 0:
            raise InvalidAmountError(self.total_amount)
        
        self.status = OrderStatus.PAID
        self.status_history.append(
            OrderStatusChange(order_id=self.id, status=OrderStatus.PAID)
        )

    def cancel(self) -> None:
        if self.status == OrderStatus.PAID:
            raise OrderAlreadyPaidError(self.id)
        
        if self.status in (OrderStatus.SHIPPED, OrderStatus.COMPLETED):
            raise OrderCancelledError(self.id)
        
        self.status = OrderStatus.CANCELLED
        self.status_history.append(
            OrderStatusChange(order_id=self.id, status=OrderStatus.CANCELLED)
        )

    def ship(self) -> None:
        if self.status != OrderStatus.PAID:
            raise ValueError("Only paid order can be shipped")
        self.status = OrderStatus.SHIPPED
        self.status_history.append(
            OrderStatusChange(order_id=self.id, status=OrderStatus.SHIPPED)
        )

    def complete(self) -> None:
        if self.status != OrderStatus.SHIPPED:
            raise ValueError("Only shipped order can be completed")
        self.status = OrderStatus.COMPLETED
        self.status_history.append(
            OrderStatusChange(order_id=self.id, status=OrderStatus.COMPLETED)
        )
