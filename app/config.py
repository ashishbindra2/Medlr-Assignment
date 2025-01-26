from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    upload_path: str
    db_name: str
    mongo_url: str
    scraping_schedule: str = "0 0 * * *"

    class Config:
        env_file = "app/.env"


settings = Settings()
