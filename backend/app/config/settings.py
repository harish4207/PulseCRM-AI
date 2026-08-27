from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/pulsecrm_ai"
    SECRET_KEY: str = "dev-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    AI_REASONING_PROVIDER: str = "gemini"
    GEMINI_MODEL: str = "gemini-3.7-flash"
    AI_FALLBACK_PROVIDER: str = "groq"
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="allow")

    @property
    def effective_gemini_api_key(self) -> str:
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY or ""


settings = Settings()