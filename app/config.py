# Configuración de la aplicación mediante variables de entorno
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_path: str = "partituras.db"
    scan_folders: list[str] = []
    anthropic_api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
