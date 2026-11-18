"""
One-off fix: add the missing 'PROGRESSING' label to the completion_status_options
Postgres enum type.

Why: this repo has no Alembic/migrations (see CLAUDE.md) - tables/types are created
once via SQLAlchemy's create_all and never altered afterward. CompletionStatus.PROGRESSING
was added to the Python enum after the Postgres type already existed, so starting an
interview fails with:
    invalid input value for enum completion_status_options: "PROGRESSING"

Run once per environment (dev, staging, prod) against that environment's database:
    python scripts/fix_completion_status_enum.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.postgres.postgres_manager import PostgresManager

ENUM_TYPE = "completion_status_options"
LABEL = "PROGRESSING"


def main():
    db = PostgresManager.get_instance()

    # ALTER TYPE ... ADD VALUE cannot run inside an implicit transaction on
    # older Postgres, and even on 12+ the new value can't be used in the same
    # transaction it was added in - autocommit sidesteps both issues.
    with db.db_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        existing = conn.execute(
            text(
                """
                SELECT enumlabel FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = :type_name
                """
            ),
            {"type_name": ENUM_TYPE},
        ).scalars().all()

        if not existing:
            print(f"Type '{ENUM_TYPE}' not found in this database - nothing to fix.")
            return

        print(f"Current labels on {ENUM_TYPE}: {existing}")

        if LABEL in existing:
            print(f"'{LABEL}' already present - nothing to do.")
            return

        conn.execute(text(f"ALTER TYPE {ENUM_TYPE} ADD VALUE :label"), {"label": LABEL}) \
            if False else conn.execute(text(f"ALTER TYPE {ENUM_TYPE} ADD VALUE '{LABEL}'"))
        print(f"Added '{LABEL}' to {ENUM_TYPE}.")


if __name__ == "__main__":
    main()
