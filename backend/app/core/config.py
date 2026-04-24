# This file defines the configuration settings for the LitSpace application using Pydantic's BaseSettings.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LitSpace"
    app_env: str = "development"
    app_version: str = "0.1.0"

    data_dir: str = "../data"
    raw_pdf_dir: str = "../data/raw"
    processed_dir: str = "../data/processed"
    index_dir: str = "../data/indexes"
    eval_dir: str = "../data/eval"
    sqlite_path: str = "../data/litspace.db"

    embedding_model: str = "BAAI/bge-base-en-v1.5"

    llm_provider: str = "openai"
    llm_fallback_enabled: bool = True
    llm_provider_chain: str | None = "openai,ollama"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"
    anthropic_base_url: str = "https://api.anthropic.com/v1"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b-instruct"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b-instruct"

    default_answer_top_k: int = 6
    default_answer_max_tokens: int = 500
    default_answer_temperature: float = 0.1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
