from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


CLASS_NAMES = ["REAL", "FAKE"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    model_path: str = "ml/artifacts/best.pt"
    model_arch: str = "mobilenet_v2"
    max_upload_mb: int = 5
    rate_limit: str = "10/minute"
    allowed_origins: str = "http://localhost:5173"
    db_path: str = "data/truthlens.db"

    @property
    def cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
        return [origin for origin in origins if origin != "*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
