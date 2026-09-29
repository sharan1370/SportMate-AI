
import csv
import json
from pathlib import Path

from .connection import get_connection
from .schema import create_tables


BASE_DIR = Path(__file__).resolve().parents[2]

RESOURCES_FILE = BASE_DIR / "data" / "resources.json"
BOOKINGS_FILE = BASE_DIR / "data" / "bookings_seed.json"
CUSTOMERS_FILE = BASE_DIR / "data" / "customers.csv"


def load_resources(connection):
    with open(RESOURCES_FILE, "r", encoding="utf-8") as file:
        resources = json.load(file)

    for resource in resources:
        connection.execute(
            """
            INSERT OR REPLACE INTO resources (
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

    print(f"Loaded {len(resources)} resources.")


def load_customers(connection):
    with open(CUSTOMERS_FILE, "r", encoding="utf-8") as file:
        customers = list(csv.DictReader(file))

    for customer in customers:
        connection.execute(
            """
            INSERT OR REPLACE INTO customers (
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

    print(f"Loaded {len(customers)} customers.")


def load_bookings(connection):
    with open(BOOKINGS_FILE, "r", encoding="utf-8") as file:
        bookings = json.load(file)

    for booking in bookings:
        connection.execute(
            """
            INSERT OR REPLACE INTO bookings (
                booking_id,
                resource_id,
                booking_date,
                start_time,
                duration_minutes,
                customer_name,
                phone,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )

    print(f"Loaded {len(bookings)} bookings.")


def seed_database():
    create_tables()

    connection = get_connection()

    try:
        load_resources(connection)
        load_customers(connection)
        load_bookings(connection)

        connection.commit()

        print("Database seeded successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    seed_database()

