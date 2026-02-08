from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Azure AI Vision
    AZURE_VISION_ENDPOINT: str = Field(default='', env='AZURE_VISION_ENDPOINT')
    AZURE_VISION_KEY: str = Field(default='', env='AZURE_VISION_KEY')
    
    # Container Apps: everything comes from env vars, not a .env file
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

    # Azure ML endpoint (OPTIONAL for now)
    AML_ENDPOINT_URL: str | None = None
    AML_ENDPOINT_KEY: str | None = None

    # App behavior
    LOG_LEVEL: str = "INFO"


settings = Settings()


