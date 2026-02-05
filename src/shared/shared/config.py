from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    NOTE:
    - Do NOT instantiate Settings() at import time.
    - Use get_settings() so the app can boot even when optional settings are missing.
    - Keep strict validation for core platform settings (DB/Storage/ServiceBus).
    - AML settings are optional until you actually wire AML calls.
    """

    model_config = SettingsConfigDict(env_file=None)

    ENV_NAME: str = "dev"

    # Postgres (required)
    DATABASE_URL: str

    # Azure Storage (required)
    STORAGE_ACCOUNT_NAME: str
    STORAGE_RAW_CONTAINER: str = "raw"
    STORAGE_OUTPUTS_CONTAINER: str = "outputs"
    STORAGE_EXPORTS_CONTAINER: str = "exports"

    # Service Bus (required)
    SERVICEBUS_NAMESPACE: str
    SERVICEBUS_JOBS_QUEUE: str = "jobs"
    SERVICEBUS_EXPORTS_QUEUE: str = "exports"

    # Azure ML endpoint (optional for now; required when you start calling AML)
    AML_ENDPOINT_URL: str | None = None
    AML_ENDPOINT_KEY: str | None = None

    # App behavior
    LOG_LEVEL: str = "INFO"

    # Mollie (billing-service only; optional for now)
    MOLLIE_API_KEY: str | None = None
    MOLLIE_WEBHOOK_SECRET: str | None = None

    def aml_configured(self) -> bool:
        return bool(self.AML_ENDPOINT_URL and self.AML_ENDPOINT_KEY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached settings loader.
    If required settings are missing, this will still raise a ValidationError
    BUT only at the moment the app first asks for settings.
    """
    return Settings()
