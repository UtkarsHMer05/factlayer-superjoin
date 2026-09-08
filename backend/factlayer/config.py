from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='FACT_', env_file='.env', extra='ignore')
    data_dir: Path = Path('data')
    model: str = 'gpt-oss:120b-cloud'
    model_url: str = 'http://127.0.0.1:11434'
    # Empty key selects local Ollama; a key selects any OpenAI-compatible endpoint.
    api_key: str = ''
    request_timeout: int = 180
    max_requests: int = 1000
    max_tokens: int = 1000000
    enable_ocr: bool = False
    max_upload_mb: int = 50
    max_pages: int = 500


settings = Settings()
PIPELINE_VERSION = 'layout-2.claims-2.verify-1.compare-1'
