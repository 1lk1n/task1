import pytest

from app.domain import InvalidProduct, ProductNotFound
from app.services import CatalogService


async def test_create_product_stores_the_image_and_the_product(service: CatalogService, storage) -> None:
    product = await service.create_product("  Кружка  ", b"jpeg-bytes", "image/jpeg", "tg:1:10")

    assert product.title == "Кружка"
    assert product.image_key.endswith(".jpg")
    assert storage.saved[product.image_key] == (b"jpeg-bytes", "image/jpeg")


async def test_a_repeated_request_returns_the_same_product(service: CatalogService, storage, repository) -> None:
    first = await service.create_product("Кружка", b"jpeg-bytes", "image/jpeg", "tg:1:10")
    again = await service.create_product("Кружка", b"jpeg-bytes", "image/jpeg", "tg:1:10")

    assert again == first
    assert len(repository.products) == 1
    assert storage.uploads == 1


async def test_the_image_key_comes_from_the_idempotency_key(service: CatalogService) -> None:
    first = await service.create_product("Кружка", b"a", "image/png", "tg:1:10")
    other = await service.create_product("Кружка", b"a", "image/png", "tg:1:11")

    assert first.image_key != other.image_key
    assert first.image_key.endswith(".png")


@pytest.mark.parametrize(
    ("title", "image", "content_type"),
    [
        ("   ", b"a", "image/jpeg"),
        ("x" * 256, b"a", "image/jpeg"),
        ("Кружка", b"a", "image/gif"),
        ("Кружка", b"", "image/jpeg"),
    ],
)
async def test_invalid_products_are_rejected(service: CatalogService, storage, title, image, content_type) -> None:
    with pytest.raises(InvalidProduct):
        await service.create_product(title, image, content_type, "tg:1:10")
    assert storage.uploads == 0


async def test_products_are_listed_newest_first(service: CatalogService) -> None:
    await service.create_product("Первый", b"a", "image/jpeg", "tg:1:1")
    await service.create_product("Второй", b"a", "image/jpeg", "tg:1:2")

    assert [product.title for product in await service.list_products()] == ["Второй", "Первый"]


async def test_a_missing_product_raises(service: CatalogService) -> None:
    with pytest.raises(ProductNotFound):
        await service.get_product(42)
