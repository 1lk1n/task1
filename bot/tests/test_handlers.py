from types import SimpleNamespace

import pytest

from app import handlers
from app.catalog_api import CatalogApiError
from app.config import Settings

WEBAPP = "https://catalog.example.com/"


class FakeMessage:
    def __init__(self, caption: str | None = "Кружка", user_id: int = 1, photo: bool = True) -> None:
        self.caption = caption
        self.from_user = SimpleNamespace(id=user_id)
        self.chat = SimpleNamespace(id=500)
        self.message_id = 77
        self.photo = [SimpleNamespace(file_id="small"), SimpleNamespace(file_id="large")] if photo else None
        self.document = None if photo else SimpleNamespace(file_id="doc", mime_type="image/png")
        self.answers: list[str] = []

    async def answer(self, text: str, **_: object) -> None:
        self.answers.append(text)


class FakeBot:
    def __init__(self) -> None:
        self.downloaded: list[str] = []

    async def download(self, file_id: str, destination) -> None:
        self.downloaded.append(file_id)
        destination.write(b"image-bytes")


class FakeCatalog:
    def __init__(self, error: CatalogApiError | None = None) -> None:
        self.calls: list[dict] = []
        self.error = error

    async def create_product(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return {"id": 1, "title": kwargs["title"]}


async def test_a_photo_with_a_caption_becomes_a_product() -> None:
    message, bot, catalog = FakeMessage(caption="  Кружка  "), FakeBot(), FakeCatalog()

    await handlers.create_product(message, bot, catalog, WEBAPP)

    assert bot.downloaded == ["large"]  # the largest size of the photo
    assert catalog.calls == [{
        "title": "Кружка",
        "image": b"image-bytes",
        "content_type": "image/jpeg",
        "idempotency_key": "tg:500:77",  # the same Telegram message always gives the same key
    }]
    assert message.answers == ["Товар «Кружка» добавлен в каталог."]


async def test_an_image_sent_as_a_file_keeps_its_type() -> None:
    message, catalog = FakeMessage(photo=False), FakeCatalog()

    await handlers.create_product(message, FakeBot(), catalog, WEBAPP)

    assert catalog.calls[0]["content_type"] == "image/png"


async def test_a_photo_without_a_caption_asks_for_the_title() -> None:
    message, catalog = FakeMessage(caption=None), FakeCatalog()

    await handlers.create_product(message, FakeBot(), catalog, WEBAPP)

    assert catalog.calls == []
    assert message.answers == [handlers.NO_TITLE]


async def test_a_refused_product_is_explained_and_a_failing_api_is_retried() -> None:
    message = FakeMessage()
    await handlers.create_product(message, FakeBot(), FakeCatalog(CatalogApiError(422, "wrong image")), WEBAPP)
    assert message.answers == ["Не удалось добавить товар: wrong image"]

    with pytest.raises(CatalogApiError):  # the webhook answers 500 and Telegram delivers the update again
        await handlers.create_product(FakeMessage(), FakeBot(), FakeCatalog(CatalogApiError(503, "down")), WEBAPP)


async def test_only_admins_create_products() -> None:
    is_admin = handlers.IsAdmin()

    assert await is_admin(FakeMessage(user_id=1), admin_ids=frozenset({1}))
    assert not await is_admin(FakeMessage(user_id=2), admin_ids=frozenset({1}))


async def test_everyone_is_told_about_the_product() -> None:
    message = FakeMessage()

    await handlers.anything_else(message, WEBAPP)

    assert message.answers == ["У меня есть товар"]


def test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in {
        "BOT_TOKEN": "1:abc", "ADMIN_IDS": "1, 2", "PUBLIC_URL": "https://catalog.example.com/",
        "WEBHOOK_SECRET": "secret", "SERVICE_TOKEN": "token",
    }.items():
        monkeypatch.setenv(name, value)

    settings = Settings(_env_file=None)

    assert settings.admin_ids == frozenset({1, 2})
    assert settings.webapp_url == "https://catalog.example.com/"
    assert settings.webhook_url == "https://catalog.example.com/bot/webhook"
