import aiohttp


class CatalogApiError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"Catalog API answered {status}: {detail}")
        self.status = status
        self.detail = detail

    @property
    def is_client_error(self) -> bool:
        """The request itself is wrong (bad title, unsupported image): retrying won't help."""
        return 400 <= self.status < 500


class CatalogClient:
    """The bot doesn't touch the database or the storage itself: products are created through the API."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, service_token: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token

    async def close(self) -> None:
        await self._session.close()

    async def create_product(self, title: str, image: bytes, content_type: str, idempotency_key: str) -> dict:
        async with self._session.post(
            f"{self._base_url}/api/products",
            params={"title": title},
            data=image,
            headers={
                "Authorization": f"Bearer {self._service_token}",
                "Idempotency-Key": idempotency_key,
                "Content-Type": content_type,
            },
        ) as response:
            if response.status >= 400:
                raise CatalogApiError(response.status, await response.text())
            return await response.json()
