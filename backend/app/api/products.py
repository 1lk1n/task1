from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, status

from app.api.deps import CatalogServiceDep, SettingsDep, read_limited_body, require_service_token
from app.api.schemas import ProductOut

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
async def list_products(service: CatalogServiceDep, settings: SettingsDep) -> list[ProductOut]:
    products = await service.list_products()
    return [ProductOut.from_domain(product, settings.media_base_url) for product in products]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, service: CatalogServiceDep, settings: SettingsDep) -> ProductOut:
    product = await service.get_product(product_id)
    return ProductOut.from_domain(product, settings.media_base_url)


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_service_token)],
)
async def create_product(
    request: Request,
    service: CatalogServiceDep,
    settings: SettingsDep,
    title: Annotated[str, Query(min_length=1, max_length=255)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    content_type: Annotated[str, Header(alias="Content-Type")],
) -> ProductOut:
    """The body is the image itself (Content-Type image/jpeg, image/png or image/webp)."""
    image = await read_limited_body(request, settings.max_image_bytes)
    product = await service.create_product(
        title=title,
        image=image,
        content_type=content_type.split(";")[0].strip().lower(),
        idempotency_key=idempotency_key,
    )
    return ProductOut.from_domain(product, settings.media_base_url)
