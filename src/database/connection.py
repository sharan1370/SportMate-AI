from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parents[2]
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "booking.db"


def get_connection() -> sqlite3.Connection:
    """Create and return a SQLite database connection."""
    DB_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection