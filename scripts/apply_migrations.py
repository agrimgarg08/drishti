"""Apply SQL migrations to DATABASE_URL using SQLAlchemy.
Usage:
  set DATABASE_URL=postgresql://user:pass@host:5432/dbname
  python scripts/apply_migrations.py

This runs all .sql files in the migrations/ directory (alphabetical order).
"""
import os
from sqlalchemy import create_engine

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    print("ERROR: set DATABASE_URL environment variable (e.g., postgres URL from Supabase)")
    raise SystemExit(1)

engine = create_engine(DB_URL)

migrations_dir = os.path.join(os.path.dirname(__file__), "..", "migrations")
files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
if not files:
    print("No migrations found")
    raise SystemExit(0)

for f in files:
    path = os.path.join(migrations_dir, f)
    print(f"Applying {f}...")
    with open(path, "r", encoding="utf-8") as fh:
        sql = fh.read()
    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()
print("Migrations applied.")
