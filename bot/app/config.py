from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: SecretStr
    # Telegram user ids allowed to create products, comma-separated: "123,456".
    admin_ids_raw: str = Field(default="", alias="ADMIN_IDS")
    # Public HTTPS address of the whole system (nginx): the Mini App and the webhook live under it.
    public_url: str
    webhook_path: str = "/bot/webhook"
    webhook_secret: SecretStr

    api_url: str = "http://api:8000"
    service_token: SecretStr

    host: str = "0.0.0.0"
    port: int = 8080

    @property
    def admin_ids(self) -> frozenset[int]:
        return frozenset(int(part) for part in self.admin_ids_raw.replace(" ", "").split(",") if part)

    @property
    def webapp_url(self) -> str:
        return self.public_url.rstrip("/") + "/"

    @property
    def webhook_url(self) -> str:
        return self.public_url.rstrip("/") + self.webhook_path
