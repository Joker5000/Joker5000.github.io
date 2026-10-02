from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bot_token: str
    owner_telegram_id: int
    extra_admin_ids: str = ""
    moderation_mode: str = "assist"
    database_url: str
    redis_url: str
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-5-mini"
    ai_enabled: bool = False
    web_session_secret: str = "change-me"
    web_port: int = 8080
    web_public_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def bootstrap_admin_ids(self) -> set[int]:
        ids = {self.owner_telegram_id}
        for raw in self.extra_admin_ids.split(","):
            raw = raw.strip()
            if raw.isdigit():
                ids.add(int(raw))
        return ids

settings = Settings()
