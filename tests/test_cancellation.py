from src.tools.cancellation import cancel_booking


def test_already_cancelled_booking():
    result = cancel_booking(
        booking_id="BKG1003",
        current_time="2026-09-08 10:00",
    )

    assert result["success"] is False
    assert "already cancelled" in result["reason"]


def test_free_cancellation_before_two_hour_cutoff():
    result = cancel_booking(
        booking_id="BKG1004",
        current_time="2026-09-10 17:00",
    )

    assert result["success"] is True
    assert result["refund_eligible"] is True
    assert result["status"] == "cancelled"


def test_late_cancellation_is_non_refundable():
    result = cancel_booking(
        booking_id="BKG1005",
        current_time="2026-09-11 09:00",
    )

    assert result["success"] is True
    assert result["refund_eligible"] is False
    assert result["status"] == "cancelled"