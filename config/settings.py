from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    alpha_vantage_api_key: str = ""
    cache_db_path: Path = Path("data/cache.db")
    cache_ttl_hours: int = 24
    log_level: str = "INFO"

    @property
    def cache_db_url(self) -> str:
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
        return str(self.cache_db_path)


settings = Settings()
