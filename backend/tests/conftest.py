import os
from datetime import UTC, datetime

import pytest

# Settings are read from the environment; the tests never connect to PostgreSQL or MinIO.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("SERVICE_TOKEN", "test-token")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")
os.environ.setdefault("MAX_IMAGE_BYTES", "1024")

from app.domain import Product  # noqa: E402
from app.services import CatalogService  # noqa: E402


class FakeProductRepository:
    def __init__(self) -> None:
        self.products: dict[str, Product] = {}

    async def list_newest_first(self) -> list[Product]:
        return sorted(self.products.values(), key=lambda product: product.id, reverse=True)

    async def get(self, product_id: int) -> Product | None:
        return next((p for p in self.products.values() if p.id == product_id), None)

    async def get_by_idempotency_key(self, idempotency_key: str) -> Product | None:
        return self.products.get(idempotency_key)

    async def add(self, title: str, image_key: str, idempotency_key: str) -> Product:
        if idempotency_key not in self.products:
            self.products[idempotency_key] = Product(
                id=len(self.products) + 1, title=title, image_key=image_key, created_at=datetime.now(UTC)
            )
        return self.products[idempotency_key]


class FakeImageStorage:
    def __init__(self) -> None:
        self.saved: dict[str, tuple[bytes, str]] = {}
        self.uploads = 0

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        self.uploads += 1
        self.saved[key] = (data, content_type)


@pytest.fixture
def repository() -> FakeProductRepository:
    return FakeProductRepository()


@pytest.fixture
def storage() -> FakeImageStorage:
    return FakeImageStorage()


@pytest.fixture
def service(repository: FakeProductRepository, storage: FakeImageStorage) -> CatalogService:
    return CatalogService(repository, storage)
