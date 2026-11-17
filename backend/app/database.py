from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# If sqlite, ensure parent directory exists and construct url
if settings.database_url.startswith("sqlite"):
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{settings.db_path.resolve()}"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # import models inside function to avoid circular import
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
