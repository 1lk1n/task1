"""Use cases of the catalog. They know nothing about HTTP, SQL or S3, only about the ports."""

import hashlib

from app.domain import InvalidProduct, Product, ProductNotFound
from app.ports import ImageStorage, ProductRepository

MAX_TITLE_LENGTH = 255
IMAGE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class CatalogService:
    def __init__(self, products: ProductRepository, images: ImageStorage) -> None:
        self._products = products
        self._images = images

    async def list_products(self) -> list[Product]:
        return await self._products.list_newest_first()

    async def get_product(self, product_id: int) -> Product:
        product = await self._products.get(product_id)
        if product is None:
            raise ProductNotFound(f"Product {product_id} not found")
        return product

    async def create_product(self, title: str, image: bytes, content_type: str, idempotency_key: str) -> Product:
        """Store the image and the product.

        The same request can arrive more than once (Telegram redelivers a webhook it didn't get an answer to),
        and possibly at two replicas at the same time. The idempotency key makes that safe: the image key is
        derived from it, so a repeated upload overwrites the same object, and the database keeps one row per key.
        """
        title = title.strip()
        if not title:
            raise InvalidProduct("The product title is empty")
        if len(title) > MAX_TITLE_LENGTH:
            raise InvalidProduct(f"The product title is longer than {MAX_TITLE_LENGTH} characters")
        extension = IMAGE_EXTENSIONS.get(content_type)
        if extension is None:
            raise InvalidProduct("The image must be JPEG, PNG or WebP")
        if not image:
            raise InvalidProduct("The image is empty")

        existing = await self._products.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing

        image_key = f"{hashlib.sha256(idempotency_key.encode()).hexdigest()[:32]}.{extension}"
        await self._images.save(image_key, image, content_type)
        return await self._products.add(title=title, image_key=image_key, idempotency_key=idempotency_key)
