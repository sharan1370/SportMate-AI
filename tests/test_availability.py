from src.tools.availability import check_availability


def test_existing_booking_conflict():
    result = check_availability(
        resource_id="BC1",
        booking_date="2026-09-08",
        start_time="18:00",
        duration_minutes=60,
    )

    assert result["available"] is False
    assert result["conflicting_booking_id"] == "BKG1001"


def test_available_slot():
    result = check_availability(
        resource_id="BC1",
        booking_date="2026-09-08",
        start_time="20:00",
        duration_minutes=60,
    )

    assert result["available"] is True


def test_cancelled_booking_does_not_block():
    result = check_availability(
        resource_id="TC1",
        booking_date="2026-09-09",
        start_time="07:00",
        duration_minutes=60,
    )

    assert result["available"] is True


def test_invalid_resource():
    result = check_availability(
        resource_id="XX99",
        booking_date="2026-09-09",
        start_time="07:00",
        duration_minutes=60,
    )

    assert result["available"] is False


def test_before_opening_time():
    result = check_availability(
        resource_id="BC1",
        booking_date="2026-09-09",
        start_time="05:00",
        duration_minutes=60,
    )

    assert result["available"] is False


def test_football_minimum_duration():
    result = check_availability(
        resource_id="FT1",
        booking_date="2026-09-09",
        start_time="10:00",
        duration_minutes=30,
    )

    assert result["available"] is False


def test_multipurpose_room_minimum_duration():
    result = check_availability(
        resource_id="MR1",
        booking_date="2026-09-09",
        start_time="10:00",
        duration_minutes=60,
    )

    assert result["available"] is False