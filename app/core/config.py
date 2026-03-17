from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "StockiTrade API"
    app_description: str = "Portfolio tracking and market data API powered by KIS"
    app_version: str = "0.1.0"

    db_path: str = str(BASE_DIR / "data" / "trades.db")
    upload_dir: str = str(BASE_DIR / "data" / "uploads")

    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_base_url: str = ""

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


settings = Settings()
