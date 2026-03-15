from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/simulation_engine"
    REDIS_URL: str = "redis://localhost:6379/0"
    GROQ_API_KEY: str = ""
    WORKER_ID: str = "worker-1"


settings = Settings()
