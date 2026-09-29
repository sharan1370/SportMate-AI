from .connection import get_connection


SCHEMA = """
CREATE TABLE IF NOT EXISTS resources (
    resource_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    capacity INTEGER NOT NULL,
    hourly_rate REAL NOT NULL,
    opening_time TEXT NOT NULL,
    closing_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    phone TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    member_since TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL,
    booking_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    customer_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    reschedule_count INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (resource_id)
        REFERENCES resources(resource_id),

    FOREIGN KEY (phone)
        REFERENCES customers(phone)
);

CREATE INDEX IF NOT EXISTS idx_bookings_resource_date
ON bookings(resource_id, booking_date);

CREATE INDEX IF NOT EXISTS idx_bookings_phone
ON bookings(phone);
"""


def column_exists(
    connection,
    table_name: str,
    column_name: str,
) -> bool:
    """Check whether a column exists in a SQLite table."""

    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        row["name"] == column_name
        for row in rows
    )


def migrate_bookings_table(connection) -> None:
    """Apply required migrations to the bookings table."""

    if not column_exists(
        connection,
        "bookings",
        "reschedule_count",
    ):
        connection.execute(
            """
            ALTER TABLE bookings
            ADD COLUMN reschedule_count INTEGER NOT NULL DEFAULT 0
            """
        )


def create_tables() -> None:
    """Create all required database tables and apply migrations."""

    connection = get_connection()

    try:
        # Create tables and indexes
        connection.executescript(SCHEMA)

        # Apply migrations to existing tables
        migrate_bookings_table(connection)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    create_tables()
    print("Database tables created and migrations applied successfully.")