from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

import aioboto3
from aiobotocore.config import AioConfig

from app.config import Settings


@asynccontextmanager
async def open_s3_client(settings: Settings) -> AsyncIterator[Any]:
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key.get_secret_value(),
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        region_name=settings.s3_region,
        config=AioConfig(s3={"addressing_style": "path"}),  # MinIO serves buckets by path
    ) as client:
        yield client


class S3ImageStorage:
    def __init__(self, client: Any, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        await self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
