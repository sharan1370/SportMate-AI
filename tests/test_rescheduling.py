from src.database.connection import get_connection
from src.tools.rescheduling import reschedule_booking


def create_test_booking(
    booking_id: str,
    resource_id: str,
    booking_date: str,
    start_time: str,
    duration_minutes: int,
    customer_name: str,
    phone: str,
    reschedule_count: int = 0,
):
    connection = get_connection()

    try:
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
                created_at,
                reschedule_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                booking_id,
                resource_id,
                booking_date,
                start_time,
                duration_minutes,
                customer_name,
                phone,
                "confirmed",
                "2026-09-01T10:00:00",
                reschedule_count,
            ),
        )

        connection.commit()

    finally:
        connection.close()


def test_successful_reschedule():

    create_test_booking(
        "TESTRES001",
        "BC1",
        "2026-09-15",
        "18:00",
        60,
        "Arjun Mehta",
        "9876543210",
    )

    result = reschedule_booking(
        "TESTRES001",
        "BC2",
        "2026-09-15",
        "19:00",
        60,
        "2026-09-15 10:00",
    )

    assert result["success"] is True
    assert result["booking_id"] == "TESTRES001"
    assert result["resource_id"] == "BC2"
    assert result["start_time"] == "19:00"
    assert result["reschedule_count"] == 1


def test_reschedule_only_allowed_once():

    create_test_booking(
        "TESTRES002",
        "BC1",
        "2026-09-16",
        "18:00",
        60,
        "Arjun Mehta",
        "9876543210",
        reschedule_count=1,
    )

    result = reschedule_booking(
        "TESTRES002",
        "BC2",
        "2026-09-16",
        "19:00",
        60,
        "2026-09-16 10:00",
    )

    assert result["success"] is False
    assert "already been rescheduled" in result["reason"]


def test_reschedule_within_two_hours_rejected():

    create_test_booking(
        "TESTRES003",
        "BC1",
        "2026-09-17",
        "18:00",
        60,
        "Arjun Mehta",
        "9876543210",
    )

    result = reschedule_booking(
        "TESTRES003",
        "BC2",
        "2026-09-17",
        "19:00",
        60,
        "2026-09-17 16:30",
    )

    assert result["success"] is False
    assert "within 2 hours" in result["reason"]


def test_reschedule_conflicting_slot_rejected():

    # Original booking
    create_test_booking(
        "TESTRES004",
        "BC1",
        "2026-09-18",
        "18:00",
        60,
        "Arjun Mehta",
        "9876543210",
    )

    # Existing booking occupying the target slot.
    # 2026-09-18 is intentionally used because
    # the seed data does not contain a BC2 booking on this date.
    create_test_booking(
        "TESTRES005",
        "BC2",
        "2026-09-18",
        "20:00",
        60,
        "Priya Nair",
        "9822011234",
    )

    result = reschedule_booking(
        "TESTRES004",
        "BC2",
        "2026-09-18",
        "20:00",
        60,
        "2026-09-18 10:00",
    )

    assert result["success"] is False
    assert result["conflicting_booking_id"] == "TESTRES005"


def test_reschedule_unknown_booking_rejected():

    result = reschedule_booking(
        "DOES_NOT_EXIST",
        "BC1",
        "2026-09-20",
        "18:00",
        60,
        "2026-09-20 10:00",
    )

    assert result["success"] is False
    assert "does not exist" in result["reason"]