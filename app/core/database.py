from functools import lru_cache
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app.core.config import database_url


@lru_cache
def engine():
    return create_engine(database_url(), pool_pre_ping=True, hide_parameters=True,
                         connect_args={"connect_timeout": 3, "options": "-c statement_timeout=10000 -c lock_timeout=5000"})


def session():
    return sessionmaker(engine(), expire_on_commit=False)()


def now(db):
    return db.scalar(select(func.clock_timestamp()))
