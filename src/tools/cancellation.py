from datetime import datetime, timedelta

from src.database.repository import Repository


CANCELLATION_CUTOFF_HOURS = 2
REFUND_PROCESSING_DAYS = "3–5 business days"


def cancel_booking(
    booking_id: str,
    current_time: str | None = None,
) -> dict:
    """
    Cancel an existing booking according to SportMate's
    cancellation and refund policy.

    Rules:
    - Free cancellation up to 2 hours before slot start.
    - Cancellation within 2 hours is non-refundable.
    - Already cancelled bookings cannot be cancelled again.
    """

    repository = Repository()

    # 1. Find booking
    booking = repository.get_booking(booking_id)

    if booking is None:
        return {
            "success": False,
            "reason": f"Booking '{booking_id}' does not exist.",
        }

    # 2. Check current status
    if booking["status"] == "cancelled":
        return {
            "success": False,
            "reason": f"Booking '{booking_id}' is already cancelled.",
        }

    # 3. Only confirmed bookings can be cancelled
    if booking["status"] != "confirmed":
        return {
            "success": False,
            "reason": (
                f"Booking '{booking_id}' cannot be cancelled "
                f"because its status is '{booking['status']}.'"
            ),
        }

    # 4. Parse booking start time
    try:
        booking_start = datetime.strptime(
            f"{booking['booking_date']} {booking['start_time']}",
            "%Y-%m-%d %H:%M",
        )
    except ValueError:
        return {
            "success": False,
            "reason": "Booking contains an invalid date or time.",
        }

    # 5. Determine current time
    if current_time is None:
        now = datetime.now()
    else:
        try:
            now = datetime.strptime(
                current_time,
                "%Y-%m-%d %H:%M",
            )
        except ValueError:
            return {
                "success": False,
                "reason": (
                    "Invalid current_time. "
                    "Use YYYY-MM-DD HH:MM."
                ),
            }

    # 6. Calculate time remaining
    time_until_booking = booking_start - now
    cutoff = timedelta(hours=CANCELLATION_CUTOFF_HOURS)

    # 7. Determine refund eligibility
    if time_until_booking >= cutoff:
        refund_eligible = True
        refund_message = (
            "Cancellation is eligible for a refund. "
            f"Refunds are processed within "
            f"{REFUND_PROCESSING_DAYS} to the original "
            "payment method."
        )
    else:
        refund_eligible = False
        refund_message = (
            "Cancellation is within 2 hours of the slot start "
            "time and is non-refundable."
        )

    # 8. Update booking status
    updated = repository.update_booking_status(
        booking_id,
        "cancelled",
    )

    if not updated:
        return {
            "success": False,
            "reason": "Unable to update the booking status.",
        }

    # 9. Return cancellation result
    return {
        "success": True,
        "booking_id": booking_id,
        "status": "cancelled",
        "resource_id": booking["resource_id"],
        "booking_date": booking["booking_date"],
        "start_time": booking["start_time"],
        "duration_minutes": booking["duration_minutes"],
        "customer_name": booking["customer_name"],
        "refund_eligible": refund_eligible,
        "refund_processing_time": (
            REFUND_PROCESSING_DAYS
            if refund_eligible
            else None
        ),
        "message": refund_message,
    }