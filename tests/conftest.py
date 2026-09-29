import csv
import json
from pathlib import Path

import pytest

from src.database.schema import create_tables


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SEED_RESOURCES = PROJECT_ROOT / "data" / "resources.json"
SEED_BOOKINGS = PROJECT_ROOT / "data" / "bookings_seed.json"
SEED_CUSTOMERS = PROJECT_ROOT / "data" / "customers.csv"


@pytest.fixture(autouse=True)
def reset_test_database(monkeypatch, tmp_path):
    """
    Create a fresh SQLite database for every test.

    This prevents tests from modifying the real application database.
    """

    test_db_path = tmp_path / "test_booking.db"

    # Patch the database path used by the connection module.
    monkeypatch.setattr(
        "src.database.connection.DB_PATH",
        test_db_path,
    )

    create_tables()

    from src.database.connection import get_connection

    connection = None

    try:
        connection = get_connection()

        # -------------------------
        # Seed resources
        # -------------------------

        with open(
            SEED_RESOURCES,
            "r",
            encoding="utf-8",
        ) as file:
            resources = json.load(file)

        for resource in resources:
            connection.execute(
                """
                INSERT INTO resources (
                    resource_id,
                    name,
                    type,
                    capacity,
                    hourly_rate,
                    opening_time,
                    closing_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resource["resource_id"],
                    resource["name"],
                    resource["type"],
                    resource["capacity"],
                    resource["hourly_rate"],
                    resource["opening_time"],
                    resource["closing_time"],
                ),
            )

        # -------------------------
        # Seed customers
        # -------------------------

        with open(
            SEED_CUSTOMERS,
            "r",
            encoding="utf-8",
            newline="",
        ) as file:

            customers = csv.DictReader(file)

            for customer in customers:
                connection.execute(
                    """
                    INSERT INTO customers (
                        phone,
                        name,
                        email,
                        member_since
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        customer["phone"],
                        customer["customer_name"],
                        customer["email"],
                        customer["member_since"],
                    ),
                )

        # -------------------------
        # Seed bookings
        # -------------------------

        with open(
            SEED_BOOKINGS,
            "r",
            encoding="utf-8",
        ) as file:
            bookings = json.load(file)

        for booking in bookings:
            connection.execute(
                """
                INSERT INTO bookings (
                    booking_id,
                    resource_id,
                    booking_date,
                    start_time,
                    duration_minutes,
                    customer_name,
                    phone,
                    status,
                    created_at,
                    reschedule_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    booking["booking_id"],
                    booking["resource_id"],
                    booking["booking_date"],
                    booking["start_time"],
                    booking["duration_minutes"],
                    booking["customer_name"],
                    booking["phone"],
                    booking["status"],
                    booking["created_at"],
                    booking.get("reschedule_count", 0),
                ),
            )

        connection.commit()

    finally:
        if connection is not None:
            connection.close()