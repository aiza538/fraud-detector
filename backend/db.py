"""Database tables aur session.

Timestamps epoch seconds (integer) hain — SQLite (local/tests) aur Postgres
(production) dono par ek jaisa behave karte hain, timezone ka koi jhagra nahi.

Production me schema sirf Alembic migrations se banta/badalta hai
(`alembic upgrade head`). Local dev aur tests me `create_all` kaafi hai.
"""
from typing import Optional

from flask import g
from sqlalchemy import (BigInteger, Boolean, ForeignKey, Integer, String,
                        UniqueConstraint, create_engine)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[int] = mapped_column(BigInteger)
    signup_ip_hash: Mapped[str] = mapped_column(String(32), index=True)
    # NULL = anonymous. Sirf normalized email ka hash — raw email store nahi hota.
    email_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    verified_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    # Badhane se user ke sab purane tokens invalid ho jate hain.
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def is_verified(self):
        return self.email_hash is not None


class NumberReport(Base):
    """Ek user ka ek number par ek vote."""
    __tablename__ = "number_reports"
    __table_args__ = (UniqueConstraint("number", "user_id", name="uq_report_number_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(String(13), index=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ip_hash: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(String(280), default="")
    created_at: Mapped[int] = mapped_column(BigInteger)


class UsageCounter(Base):
    """Rozana ginti (UTC din) — daily limits isi par chalti hain.

    `subject` user id hota hai, ya "ip:<hash>" / "email:<hash>": sirf per-user
    limit kaafi nahi, kyunke naya anonymous account banana muft hai.
    """
    __tablename__ = "usage_counters"

    subject: Mapped[str] = mapped_column(String(40), primary_key=True)
    day: Mapped[str] = mapped_column(String(10), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)


class EmailChallenge(Base):
    """User ka abhi chalta hua email code. Ek user = ek row; naya code purane
    ko replace kar deta hai."""
    __tablename__ = "email_challenges"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    email_hash: Mapped[str] = mapped_column(String(64))
    code_hash: Mapped[str] = mapped_column(String(64))
    ip_hash: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[int] = mapped_column(BigInteger)
    expires_at: Mapped[int] = mapped_column(BigInteger)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


engine = None
SessionLocal = sessionmaker(expire_on_commit=False)


def init_engine(url):
    global engine
    options = {"pool_pre_ping": True}
    if url.startswith("postgresql"):
        # Neon ka pooled connection (PgBouncer) server-side prepared statements
        # ke saath theek nahi chalta — psycopg ko auto-prepare se rok do.
        options["connect_args"] = {"prepare_threshold": None}
    engine = create_engine(url, **options)
    SessionLocal.configure(bind=engine)
    return engine


def get_session():
    """Request ka session — teardown par `close_session` band karta hai."""
    if "db" not in g:
        g.db = SessionLocal()
    return g.db


def close_session(exc=None):
    session = g.pop("db", None)
    if session is not None:
        session.close()
