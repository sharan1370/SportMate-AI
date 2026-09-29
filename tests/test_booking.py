from src.tools.booking import create_booking


def test_create_booking_for_registered_customer():
    result = create_booking(
        resource_id="BC1",
        booking_date="2026-09-12",
        start_time="10:00",
        duration_minutes=60,
        customer_name="Fatima Sheikh",
        phone="9988776655",
    )

    assert result["success"] is True
    assert result["booking_id"].startswith("BKG")
    assert result["status"] == "confirmed"


def test_create_booking_rejects_unknown_customer():
    result = create_booking(
        resource_id="BC1",
        booking_date="2026-09-12",
        start_time="11:00",
        duration_minutes=60,
        customer_name="Unknown Customer",
        phone="9000000000",
    )

    assert result["success"] is False
    assert "No customer found" in result["reason"]


def test_create_booking_rejects_name_mismatch():
    result = create_booking(
        resource_id="BC1",
        booking_date="2026-09-12",
        start_time="12:00",
        duration_minutes=60,
        customer_name="Wrong Name",
        phone="9988776655",
    )

    assert result["success"] is False
    assert "does not match" in result["reason"]


def test_create_booking_rejects_unavailable_slot():
    result = create_booking(
        resource_id="BC1",
        booking_date="2026-09-08",
        start_time="18:00",
        duration_minutes=60,
        customer_name="Fatima Sheikh",
        phone="9988776655",
    )

    assert result["success"] is False
    assert result["conflicting_booking_id"] == "BKG1001"