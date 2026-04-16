"""Доменная сущность пользователя."""

import uuid
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field

from .exceptions import InvalidEmailError


@dataclass
class User:
    email: str
    name: str = ""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.email or not re.match(
            r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            self.email
        ):
            raise InvalidEmailError(f"Invalid email: {self.email}")
