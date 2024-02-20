from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DB_URI: str = ""
    # extensions
    ORG_FACADE_HOOKS: str = ""


settings = Settings()
