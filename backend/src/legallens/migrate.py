"""Runs the Alembic migrations: `python -m legallens.migrate` (DATABASE_URL must be set).

Run it before starting the Space. The migrations live inside the package, so no alembic.ini
is needed and the same command works in the Docker image.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from .db import driver_url


def upgrade(url: str, revision: str = "head") -> None:
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    # env.py reads the URL from here; "%" must be doubled for ConfigParser interpolation.
    cfg.set_main_option("sqlalchemy.url", driver_url(url).replace("%", "%%"))
    command.upgrade(cfg, revision)


if __name__ == "__main__":
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        sys.exit("DATABASE_URL is not set.")
    upgrade(database_url)
