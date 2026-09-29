from typing import Any

from .connection import get_connection


class Repository:
    """Database access layer for SportMate."""

    # -------------------------
    # Resources
    # -------------------------

    def get_all_resources(self) -> list[dict[str, Any]]:
        connection = get_connection()

        try:
            rows = connection.execute(
                "SELECT * FROM resources ORDER BY resource_id"
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            connection.close()

    def get_resource(
        self,
        resource_id: str,
    ) -> dict[str, Any] | None:

        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM resources
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    # -------------------------
    # Customers
    # -------------------------

    def get_customer_by_phone(
        self,
        phone: str,
    ) -> dict[str, Any] | None:

        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM customers
                WHERE phone = ?
                """,
                (phone,),
            ).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    # -------------------------
    # Bookings
    # -------------------------

    def get_booking(
        self,
        booking_id: str,
    ) -> dict[str, Any] | None:

        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM bookings
                WHERE booking_id = ?
                """,
                (booking_id,),
            ).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    def get_bookings_for_resource(
        self,
        resource_id: str,
        booking_date: str,
    ) -> list[dict[str, Any]]:

        connection = get_connection()

        try:
            rows = connection.execute(
                """
                SELECT *
                FROM bookings
                WHERE resource_id = ?
                  AND booking_date = ?
                  AND status = 'confirmed'
                ORDER BY start_time
                """,
                (resource_id, booking_date),
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            connection.close()

    def get_bookings_for_customer(
        self,
        phone: str,
    ) -> list[dict[str, Any]]:

        connection = get_connection()

        try:
            rows = connection.execute(
                """
                SELECT *
                FROM bookings
                WHERE phone = ?
                ORDER BY booking_date, start_time
                """,
                (phone,),
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            connection.close()

    def get_next_booking_id(self) -> str:
        """
        Generate the next sequential booking ID.

        Example:
            BKG1001
            BKG1002
            BKG1003
            ...
            BKG1006
        """

        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT booking_id
                FROM bookings
                ORDER BY CAST(
                    SUBSTR(booking_id, 4) AS INTEGER
                ) DESC
                LIMIT 1
                """
            ).fetchone()

            if row is None:
                return "BKG1001"

            last_booking_id = row["booking_id"]

            last_number = int(last_booking_id[3:])

            next_number = last_number + 1

            return f"BKG{next_number:04d}"

        finally:
            connection.close()

    def get_booking_reschedule_count(
        self,
        booking_id: str,
    ) -> int | None:
        """
        Get the number of times a booking has been rescheduled.

        Returns:
            Integer reschedule count if booking exists.
            None if booking does not exist.
        """

        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT reschedule_count
                FROM bookings
                WHERE booking_id = ?
                """,
                (booking_id,),
            ).fetchone()

            if row is None:
                return None

            return row["reschedule_count"]

        finally:
            connection.close()

    def update_booking_reschedule(
        self,
        booking_id: str,
        resource_id: str,
        booking_date: str,
        start_time: str,
        duration_minutes: int,
    ) -> bool:
        """
        Update booking details during a reschedule.

        The reschedule count is automatically incremented by 1.
        """

        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                UPDATE bookings
                SET
                    resource_id = ?,
                    booking_date = ?,
                    start_time = ?,
                    duration_minutes = ?,
                    reschedule_count = reschedule_count + 1
                WHERE booking_id = ?
                """,
                (
                    resource_id,
                    booking_date,
                    start_time,
                    duration_minutes,
                    booking_id,
                ),
            )

            connection.commit()

            return cursor.rowcount > 0

        finally:
            connection.close()

    def insert_booking(
        self,
        booking: dict[str, Any],
    ) -> None:

        connection = get_connection()

        try:
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

            connection.commit()

        finally:
            connection.close()

    def update_booking_status(
        self,
        booking_id: str,
        status: str,
    ) -> bool:

        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                UPDATE bookings
                SET status = ?
                WHERE booking_id = ?
                """,
                (status, booking_id),
            )

            connection.commit()

            return cursor.rowcount > 0

        finally:
            connection.close()