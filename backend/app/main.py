from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api import health, products
from app.config import get_settings
from app.domain import InvalidProduct, ProductNotFound
from app.infrastructure.db import create_engine, create_session_factory
from app.infrastructure.storage import S3ImageStorage, open_s3_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Only connections live in the process (the DB pool and the S3 client); all data is in PostgreSQL
    # and MinIO, so any replica can serve any request.
    settings = get_settings()
    engine = create_engine(settings.database_url)
    async with AsyncExitStack() as stack:
        stack.push_async_callback(engine.dispose)
        app.state.session_factory = create_session_factory(engine)
        s3_client = await stack.enter_async_context(open_s3_client(settings))
        app.state.image_storage = S3ImageStorage(s3_client, settings.s3_bucket)
        yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Catalog API",
        lifespan=lifespan,
        docs_url="/api/docs",  # under /api/, so nginx serves it too
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.include_router(products.router)
    app.include_router(health.router)

    @app.exception_handler(InvalidProduct)
    async def invalid_product(_: Request, exc: InvalidProduct) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": str(exc)})

    @app.exception_handler(ProductNotFound)
    async def product_not_found(_: Request, exc: ProductNotFound) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    return app


app = create_app()
