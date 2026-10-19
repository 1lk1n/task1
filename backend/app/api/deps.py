import secrets
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.infrastructure.repositories import SqlAlchemyProductRepository
from app.services import CatalogService

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request. The context manager closes it (and returns the connection to the pool)
    whatever happens; a failed request is rolled back."""
    async with request.app.state.session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_catalog_service(request: Request, session: SessionDep) -> CatalogService:
    return CatalogService(SqlAlchemyProductRepository(session), request.app.state.image_storage)


CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]


def require_service_token(settings: SettingsDep, authorization: Annotated[str | None, Header()] = None) -> None:
    """Only the bot may create products: it sends the shared service token."""
    expected = f"Bearer {settings.service_token.get_secret_value()}"
    if authorization is None or not secrets.compare_digest(authorization.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid service token")


async def read_limited_body(request: Request, limit: int) -> bytes:
    """The request body in memory, at most `limit` bytes. Unlike a multipart form, it never spills
    into a temporary file on disk."""
    declared = request.headers.get("content-length")
    if declared is not None:
        if not declared.isdigit():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid Content-Length")
        if int(declared) > limit:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"The image is larger than {limit} bytes")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"The image is larger than {limit} bytes")
        chunks.append(chunk)
    return b"".join(chunks)
