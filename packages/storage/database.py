"""Database connection and session management"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base
import structlog

from packages.core.config import settings

logger = structlog.get_logger(__name__)

# Create declarative base for models
Base = declarative_base()

# Create engine with DB-specific settings
connect_args = {}
engine_kwargs = {
    "echo": settings.debug,
}

if settings.database_url.startswith("postgresql"):
    # Fail fast if Postgres is down/misconfigured
    connect_args["connect_timeout"] = 2
    engine_kwargs.update({
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_pre_ping": True,  # Drop stale connections instead of blocking
        "connect_args": connect_args,
    })
elif settings.database_url.startswith("sqlite"):
    # SQLite in paper mode; allow multithreaded access from uvicorn workers
    connect_args["check_same_thread"] = False
    engine_kwargs.update({
        "connect_args": connect_args,
        "pool_pre_ping": True,  # lightweight check; SQLite ignores pools
    })
else:
    # Default to pooled config for other engines
    engine_kwargs.update({
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_pre_ping": True,
        "connect_args": connect_args,
    })

engine = create_engine(settings.database_url, **engine_kwargs)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database (create tables)"""
    logger.info("Initializing database")
    Base.metadata.create_all(bind=engine)
    
    # Enable WAL mode for SQLite to reduce writer locks
    if settings.database_url.startswith("sqlite"):
        with engine.connect() as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.commit()
                logger.info("SQLite WAL mode enabled")
            except Exception as e:
                logger.warning("Failed to enable SQLite WAL mode", error=str(e))
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


def order_exists(client_order_id: str, status_in: tuple = None) -> bool:
    """Check if an order with given client_order_id exists (for idempotency)"""
    from packages.storage.models import Order, OrderStatusEnum
    
    db = SessionLocal()
    try:
        query = db.query(Order).filter_by(client_order_id=client_order_id)
        if status_in:
            status_enums = [OrderStatusEnum(s) for s in status_in]
            query = query.filter(Order.status.in_(status_enums))
        return query.first() is not None
    finally:
        db.close()
