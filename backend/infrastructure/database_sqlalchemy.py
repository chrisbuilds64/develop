"""
SQLAlchemy Database Setup

Zentrale Stelle für SQLAlchemy Engine, Session, Base.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from infrastructure.config import config
from infrastructure.logging import get_logger

logger = get_logger("infrastructure.database")

# SQLAlchemy Base für alle Models
Base = declarative_base()

# Engine Setup
def get_engine():
    """
    Create SQLAlchemy engine based on config.

    Handles different connection strings (PostgreSQL, SQLite, etc.)
    """
    engine_kwargs = {}

    # SQLite in-memory needs special config
    if config.DATABASE_URL.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(
        config.DATABASE_URL,
        echo=config.DEBUG,  # Log SQL queries in debug mode
        **engine_kwargs
    )

    logger.info("Database engine created", extra={
        "dialect": engine.dialect.name,
        "debug": config.DEBUG
    })

    return engine


# Create engine
engine = get_engine()

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def init_db():
    """
    Initialize database (create tables).

    Only for development. Use Alembic migrations in production.
    """
    logger.info("Initializing database tables")
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_session() as session:
            session.query(...)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
