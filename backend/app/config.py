from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    database_url: str = "sqlite:///./data/app.db"
    kb_dir: str = "data/kb"
    embedding_provider: str = "tfidf"
    num_questions: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def backend_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def kb_dir_path(self) -> Path:
        path = Path(self.kb_dir)
        if not path.is_absolute():
            path = self.backend_dir / path
        return path

    @property
    def db_path(self) -> Path:
        raw = self.database_url
        prefix = "sqlite:///"
        if raw.startswith(prefix):
            db_file = raw[len(prefix):]
            path = Path(db_file)
            if not path.is_absolute():
                path = self.backend_dir / path
            return path
        path = Path(raw)
        if not path.is_absolute():
            path = self.backend_dir / path
        return path


settings = Settings()
