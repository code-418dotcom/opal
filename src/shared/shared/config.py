from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None)

    ENV_NAME: str = "dev"

    # Postgres
    DATABASE_URL: str

    # Azure Storage
    STORAGE_ACCOUNT_NAME: str
    STORAGE_RAW_CONTAINER: str = "raw"
    STORAGE_OUTPUTS_CONTAINER: str = "outputs"
    STORAGE_EXPORTS_CONTAINER: str = "exports"

    # Service Bus
    SERVICEBUS_NAMESPACE: str
    SERVICEBUS_JOBS_QUEUE: str = "jobs"
    SERVICEBUS_EXPORTS_QUEUE: str = "exports"

    # Azure ML endpoint
    AML_ENDPOINT_URL: str
    AML_ENDPOINT_KEY: str

    # App behavior
    LOG_LEVEL: str = "INFO"

    # Mollie (billing-service only; optional for now)
    MOLLIE_API_KEY: str | None = None
    MOLLIE_WEBHOOK_SECRET: str | None = None


settings = Settings()
