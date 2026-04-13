"""Application settings management."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = Field(default="MedFlow", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    mysql_host: str = Field(default="mysql", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_db: str = Field(default="opd_vertex", alias="MYSQL_DB")
    mysql_user: str = Field(default="opd_user", alias="MYSQL_USER")
    mysql_password: str = Field(default="opd_password", alias="MYSQL_PASSWORD")
    mongo_uri: str = Field(default="mongodb://mongo:27017", alias="MONGO_URI")
    mongo_db: str = Field(default="opd_vertex", alias="MONGO_DB")
    local_llm_endpoint: str = Field(
        default="http://localhost:11434", alias="LOCAL_LLM_ENDPOINT"
    )
    whisper_model_name: str = Field(default="base", alias="WHISPER_MODEL_NAME")
    llm_model_name: str = Field(default="llama3.1", alias="LLM_MODEL_NAME")
    smtp_host: str = Field(default="localhost", alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="noreply@example.local", alias="SMTP_FROM")
    pdf_output_dir: str = Field(default="./storage/pdfs", alias="PDF_OUTPUT_DIR")
    transcripts_dir: str = Field(
        default="./storage/transcripts", alias="TRANSCRIPTS_DIR"
    )
    generated_docs_dir: str = Field(
        default="./storage/generated", alias="GENERATED_DOCS_DIR"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    use_mock_adapters: bool = Field(default=True, alias="USE_MOCK_ADAPTERS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
