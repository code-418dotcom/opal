from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Azure AI Vision
    AZURE_VISION_ENDPOINT: str = Field(default='', env='AZURE_VISION_ENDPOINT')
    AZURE_VISION_KEY: str = Field(default='', env='AZURE_VISION_KEY')
    
    # Background Removal Provider
    BACKGROUND_REMOVAL_PROVIDER: str = Field(default='rembg', env='BACKGROUND_REMOVAL_PROVIDER')
    REMOVEBG_API_KEY: str = Field(default='', env='REMOVEBG_API_KEY')
    
    # Image Generation
    IMAGE_GEN_PROVIDER: str = Field(default='fal', env='IMAGE_GEN_PROVIDER')
    FAL_API_KEY: str = Field(default='', env='FAL_API_KEY')
    REPLICATE_API_KEY: str = Field(default='', env='REPLICATE_API_KEY')
    HUGGINGFACE_API_KEY: str = Field(default='', env='HUGGINGFACE_API_KEY')
    
    # Image Upscaling
    UPSCALE_PROVIDER: str = Field(default='realesrgan', env='UPSCALE_PROVIDER')
    UPSCALE_ENABLED: bool = Field(default=True, env='UPSCALE_ENABLED')
    
    # Load from .env file in development, env vars in production
    # Look for .env in current directory or project root
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )

    ENV_NAME: str = "dev"

    # Database (optional when using Supabase)
    DATABASE_URL: str = Field(default='', env='DATABASE_URL')

    # Supabase (Preferred)
    SUPABASE_URL: str = Field(default='', env='SUPABASE_URL')
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default='', env='SUPABASE_SERVICE_ROLE_KEY')
    SUPABASE_ANON_KEY: str = Field(default='', env='SUPABASE_ANON_KEY')

    # Storage Backend Selection
    STORAGE_BACKEND: str = Field(default='supabase', env='STORAGE_BACKEND')  # 'supabase' or 'azure'

    # Azure Storage (Legacy)
    STORAGE_ACCOUNT_NAME: str = Field(default='', env='STORAGE_ACCOUNT_NAME')
    STORAGE_RAW_CONTAINER: str = "raw"
    STORAGE_OUTPUTS_CONTAINER: str = "outputs"
    STORAGE_EXPORTS_CONTAINER: str = "exports"

    # Queue Backend Selection
    QUEUE_BACKEND: str = Field(default='database', env='QUEUE_BACKEND')  # 'database' or 'azure'

    # Azure Service Bus (Legacy)
    SERVICEBUS_NAMESPACE: str = Field(default='', env='SERVICEBUS_NAMESPACE')
    SERVICEBUS_JOBS_QUEUE: str = "jobs"
    SERVICEBUS_EXPORTS_QUEUE: str = "exports"

    # Azure ML endpoint (OPTIONAL for now)
    AML_ENDPOINT_URL: str | None = None
    AML_ENDPOINT_KEY: str | None = None

    # App behavior
    LOG_LEVEL: str = "INFO"

    # API Security
    API_KEYS: str = Field(default='', env='API_KEYS')


settings = Settings()



