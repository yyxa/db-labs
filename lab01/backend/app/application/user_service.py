"""Сервис для работы с пользователями."""

import uuid
from typing import Optional, List

from app.domain.user import User
from app.domain.exceptions import EmailAlreadyExistsError, UserNotFoundError


class UserService:
    def __init__(self, repo):
        self.repo = repo

    async def register(self, email: str, name: str = "") -> User:
        if await self.repo.find_by_email(email):
            raise EmailAlreadyExistsError(f"User with email {email} already exists")

        user = User(email=email, name=name)
        await self.repo.save(user)
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        user = await self.repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.repo.find_by_email(email)

    async def list_users(self) -> List[User]:
        return await self.repo.find_all()
