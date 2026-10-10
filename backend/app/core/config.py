from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = 'NexusCare API'
    app_env: str = 'development'
    api_v1_prefix: str = '/api/v1'
    cors_origins: str = 'http://127.0.0.1:5173,http://localhost:5173'
    supabase_url: str = ''
    supabase_publishable_key: str = ''
    supabase_secret_key: str = ''
    database_url: str = ''
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False, extra='ignore')
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
