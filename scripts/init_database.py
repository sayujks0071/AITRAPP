#!/usr/bin/env python3
"""Initialize database tables"""
import sys
sys.path.insert(0, '.')

from packages.storage.database import init_db
from packages.storage.models import Base
import structlog

logger = structlog.get_logger(__name__)

if __name__ == "__main__":
    logger.info("Initializing database tables...")
    try:
        init_db()
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}", exc_info=True)
        sys.exit(1)









