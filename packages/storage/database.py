"""Database connection and session management"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
import structlog

from packages.core.config import settings

logger = structlog.get_logger(__name__)

# Create engine
engine = create_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def init_db() -> None:
    """Initialize database (create tables)"""
    logger.info("Initializing database")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


def get_db() -> Generator[Session, None, None]:
    """Get database session (for FastAPI dependency injection)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get database session (context manager)"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Database session error", error=str(e))
        raise
    finally:
        db.close()

