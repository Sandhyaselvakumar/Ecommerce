"""
Database configuration.
Uses SQLite for local/demo simplicity, but the SQLAlchemy models are
fully MySQL-compatible — just swap SQLALCHEMY_DATABASE_URL to a
mysql+pymysql:// connection string for production deployment.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./ecom_sync.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
