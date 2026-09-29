from src.tools.pricing import calculate_booking_price


def test_regular_badminton_price():

    result = calculate_booking_price(
        resource_id="BC1",
        booking_date="2026-09-10",
        start_time="10:00",
        duration_minutes=60,
    )

    assert result["success"] is True
    assert result["base_price"] == 300.0
    assert result["peak_surcharge"] == 0.0
    assert result["membership_discount"] == 0.0
    assert result["booking_price"] == 300.0
    assert result["total_payable"] == 300.0


def test_weekday_peak_badminton_price():

    result = calculate_booking_price(
        resource_id="BC1",
        booking_date="2026-09-10",
        start_time="18:00",
        duration_minutes=60,
    )

    assert result["success"] is True
    assert result["base_price"] == 300.0
    assert result["peak_surcharge"] == 30.0
    assert result["booking_price"] == 330.0
    assert result["total_payable"] == 330.0


def test_member_peak_discount():

    result = calculate_booking_price(
        resource_id="BC1",
        booking_date="2026-09-10",
        start_time="18:00",
        duration_minutes=60,
        is_member=True,
    )

    assert result["success"] is True
    assert result["base_price"] == 300.0
    assert result["peak_surcharge"] == 30.0
    assert result["membership_discount"] == 49.5
    assert result["booking_price"] == 280.5
    assert result["total_payable"] == 280.5


def test_weekend_peak_price():

    result = calculate_booking_price(
        resource_id="TC1",
        booking_date="2026-09-12",
        start_time="10:00",
        duration_minutes=60,
    )

    assert result["success"] is True
    assert result["base_price"] == 500.0
    assert result["peak_surcharge"] == 50.0
    assert result["booking_price"] == 550.0


def test_football_deposit():

    result = calculate_booking_price(
        resource_id="FT1",
        booking_date="2026-09-10",
        start_time="10:00",
        duration_minutes=90,
    )

    assert result["success"] is True
    assert result["base_price"] == 1800.0
    assert result["peak_surcharge"] == 0.0
    assert result["booking_price"] == 1800.0
    assert result["refundable_deposit"] == 500.0
    assert result["total_payable"] == 2300.0


def test_equipment_charges():

    equipment = [
        {
            "name": "Badminton racket",
            "quantity": 2,
            "unit_price": 50,
        },
        {
            "name": "Shuttlecock",
            "quantity": 3,
            "unit_price": 20,
        },
    ]

    result = calculate_booking_price(
        resource_id="BC1",
        booking_date="2026-09-10",
        start_time="10:00",
        duration_minutes=60,
        equipment=equipment,
    )

    assert result["success"] is True
    assert result["base_price"] == 300.0
    assert result["equipment_total"] == 160.0
    assert result["total_payable"] == 460.0


def test_invalid_resource():

    result = calculate_booking_price(
        resource_id="INVALID",
        booking_date="2026-09-10",
        start_time="10:00",
        duration_minutes=60,
    )

    assert result["success"] is False