from typing import Any

from src.database.connection import get_connection


def get_customer(phone: str) -> dict[str, Any]:
    """
    Find a registered customer by phone number.
    """

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT phone, name, email, member_since
            FROM customers
            WHERE phone = ?
            """,
            (phone,),
        ).fetchone()

        if row is None:
            return {
                "success": False,
                "message": "Customer not found.",
            }

        return {
            "success": True,
            "customer": {
                "phone": row["phone"],
                "name": row["name"],
                "email": row["email"],
                "member_since": row["member_since"],
            },
        }

    finally:
        connection.close()