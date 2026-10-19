"""Updates go through the real dispatcher (filters, routing, injected data); Telegram is replaced by a session
that records the calls instead of sending them."""

from datetime import datetime
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import GetFile, SendMessage
from aiogram.types import Chat, File, Message, PhotoSize, Update, User

from app.config import Settings
from app.main import create_app, create_dispatcher

ADMIN, CUSTOMER = 1, 2


class RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.sent: list[SendMessage] = []

    async def make_request(self, bot: Bot, method: Any, timeout: int | None = None) -> Any:
        if isinstance(method, GetFile):
            return File(file_id=method.file_id, file_unique_id="u", file_path="photos/file.jpg")
        if isinstance(method, SendMessage):
            self.sent.append(method)
            return Message(message_id=len(self.sent), date=datetime.now(), chat=Chat(id=method.chat_id, type="private"))
        raise AssertionError(f"Unexpected Telegram call: {type(method).__name__}")

    async def stream_content(self, url: str, *args: Any, **kwargs: Any):
        yield b"image-bytes"

    async def close(self) -> None:
        pass


class FakeCatalog:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create_product(self, **kwargs: Any) -> dict:
        self.calls.append(kwargs)
        return {"id": 1, "title": kwargs["title"]}


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    for name, value in {
        "BOT_TOKEN": "42:test", "ADMIN_IDS": str(ADMIN), "PUBLIC_URL": "https://catalog.example.com",
        "WEBHOOK_SECRET": "secret", "SERVICE_TOKEN": "token",
    }.items():
        monkeypatch.setenv(name, value)
    return Settings(_env_file=None)


def update(user_id: int, text: str | None = None, caption: str | None = None, photo: bool = False) -> Update:
    message = Message(
        message_id=10,
        date=datetime.now(),
        chat=Chat(id=user_id, type="private"),
        from_user=User(id=user_id, is_bot=False, first_name="Test"),
        text=text,
        caption=caption,
        photo=[
            PhotoSize(file_id="small", file_unique_id="s", width=90, height=90),
            PhotoSize(file_id="large", file_unique_id="l", width=800, height=800),
        ] if photo else None,
    )
    return Update(update_id=1, message=message)


@pytest.fixture
def run(settings: Settings):
    session, catalog = RecordingSession(), FakeCatalog()
    bot = Bot(token=settings.bot_token.get_secret_value(), session=session)
    dispatcher = create_dispatcher(settings)
    dispatcher["catalog"] = catalog

    async def feed(event: Update) -> tuple[list[SendMessage], FakeCatalog]:
        await dispatcher.feed_update(bot, event)
        return session.sent, catalog

    return feed


async def test_start_offers_the_mini_app(run) -> None:
    sent, _ = await run(update(CUSTOMER, text="/start"))

    [greeting] = sent
    assert greeting.text == "У меня есть товар"
    button = greeting.reply_markup.inline_keyboard[0][0]
    assert button.web_app.url == "https://catalog.example.com/"


async def test_any_message_gets_the_same_answer(run) -> None:
    sent, _ = await run(update(CUSTOMER, text="привет"))

    assert [m.text for m in sent] == ["У меня есть товар"]


async def test_the_admin_sees_the_create_button(run) -> None:
    sent, _ = await run(update(ADMIN, text="/start"))

    assert sent[1].reply_markup.keyboard[0][0].text == "Создать товар"
    sent, _ = await run(update(ADMIN, text="Создать товар"))
    assert "фото товара и его название в подписи" in sent[-1].text


async def test_the_admin_creates_a_product_with_one_message(run) -> None:
    sent, catalog = await run(update(ADMIN, caption="Кружка", photo=True))

    assert catalog.calls == [{
        "title": "Кружка", "image": b"image-bytes", "content_type": "image/jpeg", "idempotency_key": f"tg:{ADMIN}:10",
    }]
    assert sent[-1].text == "Товар «Кружка» добавлен в каталог."


async def test_a_customers_photo_creates_nothing(run) -> None:
    sent, catalog = await run(update(CUSTOMER, caption="Кружка", photo=True))

    assert catalog.calls == []
    assert [m.text for m in sent] == ["У меня есть товар"]


def test_the_server_takes_webhooks_and_health_checks(settings: Settings) -> None:
    app = create_app(settings)  # nothing is sent to Telegram until the server starts

    paths = {route.resource.canonical for route in app.router.routes()}
    assert {"/bot/webhook", "/health"} <= paths


async def test_replicas_starting_together_wait_out_telegrams_flood_control(monkeypatch: pytest.MonkeyPatch) -> None:
    from aiogram.exceptions import TelegramRetryAfter
    from aiogram.methods import SetWebhook

    from app import main

    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)
    answers = iter([TelegramRetryAfter(SetWebhook(url="https://x"), "Flood control exceeded", 1)] * 2 + [True])

    async def set_webhook() -> bool:
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    assert await main.with_flood_retry(set_webhook) is True
    assert len(slept) == 2 and all(1 <= s <= 3 for s in slept)
