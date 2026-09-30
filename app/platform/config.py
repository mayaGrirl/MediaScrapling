from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    redis_url: str = "redis://127.0.0.1:6379/0"
    mysql_url: str = "mysql+pymysql://root:root@127.0.0.1:3306/crawler"
    mediacrawler_home: str = "third_party/MediaCrawler"
    media_timeout_seconds: int = 900


def get_settings() -> Settings:
    return Settings()
