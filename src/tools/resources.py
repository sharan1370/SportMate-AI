from typing import Any

from src.database.connection import get_connection


def get_resources() -> list[dict[str, Any]]:
    """
    Return all sports facility resources.
    """

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                resource_id,
                name,
                type,
                capacity,
                hourly_rate,
                opening_time,
                closing_time
            FROM resources
            ORDER BY resource_id
            """
        ).fetchall()

        return [
            {
                "resource_id": row["resource_id"],
                "name": row["name"],
                "type": row["type"],
                "capacity": row["capacity"],
                "hourly_rate": row["hourly_rate"],
                "opening_time": row["opening_time"],
                "closing_time": row["closing_time"],
            }
            for row in rows
        ]

    finally:
        connection.close()