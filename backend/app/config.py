from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration comes only from the environment, so every replica is configured the same way."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    service_token: SecretStr

    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: SecretStr
    s3_secret_key: SecretStr
    s3_bucket: str = "products"
    s3_region: str = "us-east-1"

    # Public prefix the images are served under (nginx proxies it to the bucket).
    media_base_url: str = "/media"
    max_image_bytes: int = 10 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
