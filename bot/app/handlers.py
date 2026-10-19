"""The bot's logic. It keeps no state between messages: a product comes in one message (photo + caption),
so any replica can handle any update, and the API makes a repeated update harmless (idempotency key)."""

import io
import logging

from aiogram import Bot, F, Router
from aiogram.filters import BaseFilter, Command, CommandStart
from aiogram.types import Message

from app.catalog_api import CatalogApiError, CatalogClient
from app.keyboards import CREATE_PRODUCT_BUTTON, admin_keyboard, catalog_keyboard

log = logging.getLogger(__name__)

GREETING = "У меня есть товар"
HOW_TO_CREATE = "Отправьте одним сообщением фото товара и его название в подписи к фото."
NO_TITLE = "Добавьте название товара в подпись к фото и отправьте ещё раз."


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, admin_ids: frozenset[int]) -> bool:
        return message.from_user is not None and message.from_user.id in admin_ids


is_image = F.photo | F.document.mime_type.startswith("image/")


async def start(message: Message, webapp_url: str, admin_ids: frozenset[int]) -> None:
    await message.answer(GREETING, reply_markup=catalog_keyboard(webapp_url))
    if message.from_user is not None and message.from_user.id in admin_ids:
        await message.answer(
            f"Чтобы разместить товар, нажмите «{CREATE_PRODUCT_BUTTON}».", reply_markup=admin_keyboard()
        )


async def explain_create(message: Message) -> None:
    await message.answer(HOW_TO_CREATE)


async def create_product(message: Message, bot: Bot, catalog: CatalogClient, webapp_url: str) -> None:
    title = (message.caption or "").strip()
    if not title:
        await message.answer(NO_TITLE)
        return

    if message.photo:
        file_id, content_type = message.photo[-1].file_id, "image/jpeg"  # the largest size
    else:
        file_id, content_type = message.document.file_id, message.document.mime_type
    image = io.BytesIO()  # in memory: nothing is written to the replica's disk
    await bot.download(file_id, destination=image)

    try:
        product = await catalog.create_product(
            title=title,
            image=image.getvalue(),
            content_type=content_type,
            idempotency_key=f"tg:{message.chat.id}:{message.message_id}",
        )
    except CatalogApiError as exc:
        if not exc.is_client_error:
            raise  # the webhook answers 500, Telegram delivers the update again
        log.info("The API refused the product: %s", exc)
        await message.answer(f"Не удалось добавить товар: {exc.detail}")
        return

    await message.answer(f"Товар «{product['title']}» добавлен в каталог.", reply_markup=catalog_keyboard(webapp_url))


async def anything_else(message: Message, webapp_url: str) -> None:
    await message.answer(GREETING, reply_markup=catalog_keyboard(webapp_url))


def create_router() -> Router:
    """A new router per dispatcher (an aiogram router can be attached to only one). Order matters:
    the first matching handler takes the message."""
    router = Router(name="catalog")
    router.message.register(start, CommandStart())
    router.message.register(explain_create, IsAdmin(), F.text == CREATE_PRODUCT_BUTTON)
    router.message.register(explain_create, IsAdmin(), Command("create"))
    router.message.register(create_product, IsAdmin(), is_image)
    router.message.register(anything_else)
    return router
