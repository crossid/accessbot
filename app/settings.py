from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DB_URI: str = ""
    VSTORE_URI: str = ""
    VSTORE_EMBEDDING: str = ""
    # oauth
    OAUTH2_OPENID_CONFIGURATION: str = ""
    OAUTH2_AUDIENCE: str = ""
    # extensions
    ORG_FACADE_HOOKS: str = ""


settings = Settings()
