"""The bot as a webhook server: Telegram pushes each update to one of the replicas behind the load balancer.
Long polling can't run in several replicas (Telegram allows one getUpdates consumer per bot)."""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import MenuButtonWebApp, WebAppInfo
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.catalog_api import CatalogClient
from app.config import Settings
from app.handlers import create_router

log = logging.getLogger(__name__)
T = TypeVar("T")


async def with_flood_retry(call: Callable[[], Awaitable[T]], attempts: int = 6) -> T:
    """Telegram rate-limits these calls per bot, not per replica: replicas that start together get
    "retry after N seconds". Wait as told (plus a random bit, so they don't collide again) and repeat."""
    for attempt in range(1, attempts + 1):
        try:
            return await call()
        except TelegramRetryAfter as exc:
            if attempt == attempts:
                raise
            log.info("Telegram asks to wait %s s before repeating the call", exc.retry_after)
            await asyncio.sleep(exc.retry_after + random.uniform(0, 2))
    raise AssertionError("unreachable")


async def on_startup(bot: Bot, dispatcher: Dispatcher, settings: Settings) -> None:
    # Every replica sets the same webhook and menu button at start: repeating them changes nothing, and
    # setting them every time keeps the secret and the address in step with this replica's configuration.
    await with_flood_retry(lambda: bot.set_webhook(
        settings.webhook_url,
        secret_token=settings.webhook_secret.get_secret_value(),
        allowed_updates=dispatcher.resolve_used_update_types(),
    ))
    await with_flood_retry(lambda: bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="Каталог", web_app=WebAppInfo(url=settings.webapp_url))
    ))
    dispatcher["catalog"] = CatalogClient(
        aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)),
        settings.api_url,
        settings.service_token.get_secret_value(),
    )


async def on_shutdown(dispatcher: Dispatcher) -> None:
    catalog = dispatcher.workflow_data.get("catalog")
    if catalog is not None:
        await catalog.close()


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def create_dispatcher(settings: Settings) -> Dispatcher:
    # Workflow data reaches the handlers by parameter name (webapp_url, admin_ids, and catalog from startup).
    dispatcher = Dispatcher(settings=settings, webapp_url=settings.webapp_url, admin_ids=settings.admin_ids)
    dispatcher.include_router(create_router())
    return dispatcher


def create_app(settings: Settings) -> web.Application:
    bot = Bot(token=settings.bot_token.get_secret_value())
    dispatcher = create_dispatcher(settings)
    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)

    app = web.Application()
    app.router.add_get("/health", health)
    # handle_in_background=False: Telegram gets 200 only after the update is handled; if a replica fails
    # midway, Telegram delivers the update again (the API's idempotency key prevents duplicates).
    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        handle_in_background=False,
        secret_token=settings.webhook_secret.get_secret_value(),
    ).register(app, path=settings.webhook_path)
    setup_application(app, dispatcher, bot=bot)
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings()
    web.run_app(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
