"""db.py - SQLite database setup using SQLAlchemy for Trademark DSS."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# SQLite database file path in the project root
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dss_users.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    """User model for authentication and role-based access."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="lawyer")  # "lawyer", "company", "admin"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Case(Base):
    """Case model for storing submitted dispute evaluations."""

    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(String, unique=True, index=True, nullable=False)
    user_email = Column(String, index=True, nullable=False)
    party_a = Column(String, nullable=False)
    party_b = Column(String, nullable=False)
    trademark_name = Column(String, nullable=False)
    dispute_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")  # "pending", "approved", "rejected"
    arbitrability = Column(String, nullable=True)
    report_filename = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "user_email": self.user_email,
            "parties": f"{self.party_a} v. {self.party_b}",
            "party_a": self.party_a,
            "party_b": self.party_b,
            "trademark": self.trademark_name,
            "trademark_name": self.trademark_name,
            "dispute_type": self.dispute_type,
            "status": self.status,
            "arbitrability": self.arbitrability,
            "created": self.created_at.strftime("%d %b %Y") if self.created_at else "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "report_filename": self.report_filename,
            "download_url": f"/download/{self.report_filename}" if self.report_filename else None,
        }


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
