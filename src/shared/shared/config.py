from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    @model_validator(mode="after")
    def strip_string_values(self):
        """Strip leading/trailing whitespace from all string settings."""
        for name, field_info in self.model_fields.items():
            val = getattr(self, name)
            if isinstance(val, str) and val != val.strip():
                object.__setattr__(self, name, val.strip())
        return self
    # Azure AI Vision
    AZURE_VISION_ENDPOINT: str = Field(default='', env='AZURE_VISION_ENDPOINT')
    AZURE_VISION_KEY: str = Field(default='', env='AZURE_VISION_KEY')
    
    # Background Removal Provider
    BACKGROUND_REMOVAL_PROVIDER: str = Field(default='birefnet', env='BACKGROUND_REMOVAL_PROVIDER')
    REMOVEBG_API_KEY: str = Field(default='', env='REMOVEBG_API_KEY')
    
    # Image Generation
    IMAGE_GEN_PROVIDER: str = Field(default='fal-flux2', env='IMAGE_GEN_PROVIDER')
    FAL_API_KEY: str = Field(default='', env='FAL_API_KEY')
    REPLICATE_API_KEY: str = Field(default='', env='REPLICATE_API_KEY')
    HUGGINGFACE_API_KEY: str = Field(default='', env='HUGGINGFACE_API_KEY')
    
    # Image Upscaling
    UPSCALE_PROVIDER: str = Field(default='realesrgan', env='UPSCALE_PROVIDER')
    UPSCALE_ENABLED: bool = Field(default=False, env='UPSCALE_ENABLED')
    
    # Load from .env file in development, env vars in production
    # Look for .env in current directory or project root
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )

    ENV_NAME: str = "dev"

    # Database
    DATABASE_URL: str = Field(default='', env='DATABASE_URL')

    # Azure Storage
    STORAGE_ACCOUNT_NAME: str = Field(default='', env='STORAGE_ACCOUNT_NAME')
    STORAGE_RAW_CONTAINER: str = "raw"
    STORAGE_OUTPUTS_CONTAINER: str = "outputs"
    STORAGE_EXPORTS_CONTAINER: str = "exports"

    # Queue Backend Selection
    QUEUE_BACKEND: str = Field(default='database', env='QUEUE_BACKEND')  # 'database' or 'azure'

    # Azure Service Bus
    SERVICEBUS_NAMESPACE: str = Field(default='', env='SERVICEBUS_NAMESPACE')
    SERVICEBUS_JOBS_QUEUE: str = "jobs"
    SERVICEBUS_EXPORTS_QUEUE: str = "exports"
    SERVICEBUS_BG_REMOVAL_QUEUE: str = "bg-removal"
    SERVICEBUS_SCENE_GEN_QUEUE: str = "scene-gen"
    SERVICEBUS_UPSCALE_QUEUE: str = "upscale"

    # Azure ML endpoint (OPTIONAL for now)
    AML_ENDPOINT_URL: str | None = None
    AML_ENDPOINT_KEY: str | None = None

    # CORS
    CORS_ALLOWED_ORIGINS: str = Field(
        default="https://dev.opaloptics.com,https://ambitious-smoke-04d5b1703.1.azurestaticapps.net,http://localhost:5173",
        env="CORS_ALLOWED_ORIGINS",
    )

    # App behavior
    LOG_LEVEL: str = "INFO"

    # API Security
    API_KEYS: str = Field(default='', env='API_KEYS')

    # Entra External ID (Auth)
    ENTRA_TENANT_ID: str = Field(default='', env='ENTRA_TENANT_ID')
    ENTRA_CLIENT_ID: str = Field(default='', env='ENTRA_CLIENT_ID')
    ENTRA_ISSUER: str = Field(default='', env='ENTRA_ISSUER')

    # Mollie (Billing)
    MOLLIE_API_KEY: str = Field(default='', env='MOLLIE_API_KEY')
    MOLLIE_WEBHOOK_SECRET: str = Field(default='', env='MOLLIE_WEBHOOK_SECRET')

    # Public URL (for webhook callbacks)
    PUBLIC_BASE_URL: str = Field(default='http://localhost:8000', env='PUBLIC_BASE_URL')

    # Shopify Integration
    SHOPIFY_API_KEY: str = Field(default='', env='SHOPIFY_API_KEY')
    SHOPIFY_API_SECRET: str = Field(default='', env='SHOPIFY_API_SECRET')
    SHOPIFY_SCOPES: str = Field(default='read_products,write_products', env='SHOPIFY_SCOPES')

    # Etsy Integration
    ETSY_API_KEY: str = Field(default='', env='ETSY_API_KEY')

    # Encryption key for OAuth tokens at rest (Fernet, base64-encoded 32 bytes)
    ENCRYPTION_KEY: str = Field(default='', env='ENCRYPTION_KEY')


settings = Settings()



