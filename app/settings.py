from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    ENV: str = "production"
    DB_URI: str = ""
    VSTORE_URI: str = ""
    VSTORE_EMBEDDING: str = "openai"
    VAULT_URI: str = ""
    # oauth
    OAUTH2_OPENID_CONFIGURATION: str = ""
    OAUTH2_AUDIENCE: str = ""
    # llm
    LLM_MODEL: str = "openai://gpt-4-turbo-preview"
    # messaging
    SLACK_CLIENT_ID: str = ""
    SLACK_CLIENT_SECRET: str = ""
    SLACK_SIGNING_SECRET: str = ""


settings = Settings()
