"""Interfaces the use cases depend on. Implementations live in app.infrastructure."""

from typing import Protocol

from app.domain import Product


class ProductRepository(Protocol):
    async def list_newest_first(self) -> list[Product]: ...

    async def get(self, product_id: int) -> Product | None: ...

    async def get_by_idempotency_key(self, idempotency_key: str) -> Product | None: ...

    async def add(self, title: str, image_key: str, idempotency_key: str) -> Product:
        """Insert the product; if one with the same idempotency key already exists, return that one."""
        ...


class ImageStorage(Protocol):
    async def save(self, key: str, data: bytes, content_type: str) -> None: ...
