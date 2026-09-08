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
    stream_idle_timeout: int = 60
    # Non-OpenRouter GLM routes require thinking to stay enabled. OpenRouter's
    # free router receives only universally supported request parameters.
    thinking_mode: str = 'enabled'
    reasoning_effort: str = "low"
    # GLM supports up to 128k output tokens, but this compact JSON contract only
    # needs a small bounded answer per source unit.
    max_output_tokens: int = 8192
    # A free provider can return a short request-window limit. Preserve the
    # source state and retry after this bounded cooldown instead of making the
    # user manually resume every few pages.
    model_retry_cooldown_seconds: int = 65
    max_requests: int = 1000
    max_tokens: int = 1000000
    sample_mode: bool = False
    # Public Vercel deployments use an immutable saved-results database. Live
    # uploads require durable object storage and a worker-capable service.
    read_only: bool = False
    max_upload_mb: int = 50
    max_pages: int = 500
    upload_rate_limit: int = 5
    resume_rate_limit: int = 6
    rate_limit_window_seconds: int = 60


settings = Settings()
PIPELINE_VERSION = 'layout-5.claims-9.verify-3.compare-2'
