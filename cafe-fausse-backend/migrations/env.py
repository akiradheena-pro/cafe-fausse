from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine 
from alembic import context
import os
import sys

config = context.config


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api.extensions import db
import api.models

target_metadata = db.metadata

def get_database_url():
    """Gets the database URL from the environment, raising an error if not found."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(get_database_url())

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()