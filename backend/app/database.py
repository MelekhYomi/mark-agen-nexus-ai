import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

# SYNC ENGINE FOR SQLITE - Bypasses all async/postgres complexity
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create tables synchronously for immediate demo"""
    from app.models import Base
    Base.metadata.create_all(bind=engine)

def close_db():
    """Dispose of database connections on shutdown"""
    engine.dispose()
    logger.info("Database connections closed")
