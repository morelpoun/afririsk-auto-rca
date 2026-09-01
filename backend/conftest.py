import os
from pathlib import Path

TEST_DB_PATH = Path(__file__).parent / "test_afririsk.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()
