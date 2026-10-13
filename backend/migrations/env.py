"""Alembic environment — app ki apni settings aur tables use karta hai."""
from alembic import context
from sqlalchemy import create_engine, pool

import config as app_config
import db

target_metadata = db.Base.metadata
# Tests `sqlalchemy.url` khud set karte hain; warna wahi DATABASE_URL jo app use karti hai.
url = context.config.get_main_option("sqlalchemy.url") or app_config.DATABASE_URL

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    # NullPool: migration ke baad koi connection khula nahi rehta.
    with create_engine(url, poolclass=pool.NullPool).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
