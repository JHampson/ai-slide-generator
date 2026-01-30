#!/usr/bin/env python3
"""Databricks App startup script.

Handles database initialization and seeding before starting the FastAPI server.
Called from app.yaml command.
"""

import os
import subprocess
import sys


def ensure_schema_exists():
    """Create the database schema if it doesn't exist."""
    from sqlalchemy import text

    from src.core.database import get_engine

    schema = os.getenv("LAKEBASE_SCHEMA", "app_data")
    engine = get_engine()

    print(f"Ensuring schema '{schema}' exists...")
    with engine.connect() as conn:
        # Create schema if not exists (PostgreSQL syntax)
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        conn.commit()
    print(f"Schema '{schema}' ready.")


def main():
    """Initialize database, seed defaults, then start uvicorn."""
    # Create schema first
    ensure_schema_exists()

    # Initialize database tables
    print("Initializing database tables...")
    # Import all models to ensure they're registered with Base.metadata
    # This must happen before init_db() is called
    import src.database.models  # noqa: F401
    from src.core.database import init_db

    init_db()
    print("Database initialized.")

    # Seed default profiles and settings
    print("Seeding defaults...")
    from src.core.init_default_profile import seed_defaults

    seed_defaults()
    print("Defaults seeded.")

    # Start uvicorn
    print("Starting uvicorn server...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--workers",
            "4",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
