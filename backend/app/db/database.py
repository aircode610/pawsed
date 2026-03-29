"""SQLite database setup with SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

DATABASE_URL = f"sqlite:///{settings.db_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """Create all tables and apply any missing column migrations."""
    from sqlalchemy import inspect, text
    Base.metadata.create_all(bind=engine)

    # Additive migrations for columns added after initial deploy
    _MIGRATIONS = [
        ("sessions", "transcript_json", "TEXT"),
        ("sessions", "scoring_json",    "TEXT"),
    ]
    inspector = inspect(engine)
    with engine.connect() as conn:
        for table, col, col_type in _MIGRATIONS:
            existing = {c["name"] for c in inspector.get_columns(table)}
            if col not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
