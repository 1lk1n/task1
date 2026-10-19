from collections.abc import AsyncIterator

import httpx
import pytest

from app.api.deps import get_catalog_service
from app.main import create_app
from app.services import CatalogService

AUTH = {"Authorization": "Bearer test-token"}


@pytest.fixture
async def client(service: CatalogService) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_catalog_service] = lambda: service
    # ASGITransport doesn't run the lifespan, so no database or S3 connection is opened.
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def create(client: httpx.AsyncClient, title: str = "Кружка", key: str = "tg:1:10", **headers) -> httpx.Response:
    return await client.post(
        "/api/products",
        params={"title": title},
        content=b"jpeg-bytes",
        headers={**AUTH, "Idempotency-Key": key, "Content-Type": "image/jpeg", **headers},
    )


async def test_the_catalog_lists_products_with_image_urls(client: httpx.AsyncClient) -> None:
    created = (await create(client)).json()

    response = await client.get("/api/products")

    assert response.status_code == 200
    [product] = response.json()
    assert product["title"] == "Кружка"
    assert product["image_url"] == f"/media/{created['image_url'].rsplit('/', 1)[1]}"


async def test_a_product_page(client: httpx.AsyncClient) -> None:
    created = (await create(client)).json()

    assert (await client.get(f"/api/products/{created['id']}")).json()["title"] == "Кружка"
    assert (await client.get("/api/products/999")).status_code == 404


async def test_creating_needs_the_service_token(client: httpx.AsyncClient) -> None:
    response = await create(client, Authorization="Bearer wrong")

    assert response.status_code == 401
    assert (await client.get("/api/products")).json() == []


async def test_creating_twice_with_one_key_gives_one_product(client: httpx.AsyncClient) -> None:
    first = await create(client)
    again = await create(client)

    assert first.status_code == again.status_code == 201
    assert again.json()["id"] == first.json()["id"]
    assert len((await client.get("/api/products")).json()) == 1


async def test_too_large_and_wrong_images_are_refused(client: httpx.AsyncClient) -> None:
    too_large = await client.post(
        "/api/products",
        params={"title": "Кружка"},
        content=b"x" * 2048,  # MAX_IMAGE_BYTES is 1024 in the tests
        headers={**AUTH, "Idempotency-Key": "tg:1:11", "Content-Type": "image/jpeg"},
    )
    wrong_type = await create(client, key="tg:1:12", **{"Content-Type": "image/gif"})

    assert too_large.status_code == 413
    assert wrong_type.status_code == 422
