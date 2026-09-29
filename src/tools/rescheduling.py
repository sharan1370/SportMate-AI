from datetime import datetime, timedelta

from src.database.repository import Repository
from src.tools.availability import check_availability


RESCHEDULE_CUTOFF_HOURS = 2
MAX_RESCHEDULE_COUNT = 1


def reschedule_booking(
    booking_id: str,
    new_resource_id: str,
    new_booking_date: str,
    new_start_time: str,
    new_duration_minutes: int,
    current_time: str | None = None,
) -> dict:
    """
    Reschedule an existing confirmed booking.

    Rules:
    - Booking must exist.
    - Booking must be confirmed.
    - A booking can be rescheduled only once.
    - Rescheduling must happen at least 2 hours
      before the original slot start time.
    - New slot must be available.
    - New slot must satisfy all availability rules.
    - Existing booking ID is retained.
    """

    repository = Repository()

    booking = repository.get_booking(booking_id)

    # -------------------------
    # Booking existence
    # -------------------------

    if booking is None:
        return {
            "success": False,
            "reason": f"Booking '{booking_id}' does not exist.",
        }

    # -------------------------
    # Booking status
    # -------------------------

    if booking["status"] != "confirmed":
        return {
            "success": False,
            "reason": (
                f"Booking '{booking_id}' cannot be rescheduled "
                f"because its status is '{booking['status']}'."
            ),
        }

    # -------------------------
    # Reschedule count
    # -------------------------

    reschedule_count = repository.get_booking_reschedule_count(
        booking_id
    )

    if reschedule_count is None:
        return {
            "success": False,
            "reason": f"Booking '{booking_id}' does not exist.",
        }

    if reschedule_count >= MAX_RESCHEDULE_COUNT:
        return {
            "success": False,
            "reason": (
                f"Booking '{booking_id}' has already been rescheduled "
                "once. Only one reschedule is allowed per booking."
            ),
        }

    # -------------------------
    # Parse original booking time
    # -------------------------

    try:
        original_start = datetime.strptime(
            f"{booking['booking_date']} {booking['start_time']}",
            "%Y-%m-%d %H:%M",
        )
    except ValueError:
        return {
            "success": False,
            "reason": "Booking contains an invalid date or time.",
        }

    # -------------------------
    # Parse current time
    # -------------------------

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

    # -------------------------
    # Two-hour cutoff
    # -------------------------

    time_until_booking = original_start - now
    cutoff = timedelta(hours=RESCHEDULE_CUTOFF_HOURS)

    if time_until_booking < cutoff:
        return {
            "success": False,
            "reason": (
                "Rescheduling is not allowed within 2 hours "
                "of the original slot start time."
            ),
        }

    # -------------------------
    # Check new slot
    # -------------------------

    availability = check_availability(
        resource_id=new_resource_id,
        booking_date=new_booking_date,
        start_time=new_start_time,
        duration_minutes=new_duration_minutes,
        exclude_booking_id=booking_id,
    )

    if not availability["available"]:
        return {
            "success": False,
            "reason": availability["reason"],
            "conflicting_booking_id": availability.get(
                "conflicting_booking_id"
            ),
        }

    # -------------------------
    # Update booking
    # -------------------------

    updated = repository.update_booking_reschedule(
        booking_id=booking_id,
        resource_id=new_resource_id,
        booking_date=new_booking_date,
        start_time=new_start_time,
        duration_minutes=new_duration_minutes,
    )

    if not updated:
        return {
            "success": False,
            "reason": "Unable to update the booking.",
        }

    # -------------------------
    # Success
    # -------------------------

    return {
        "success": True,
        "booking_id": booking_id,
        "resource_id": new_resource_id,
        "resource_name": availability["resource_name"],
        "booking_date": new_booking_date,
        "start_time": new_start_time,
        "duration_minutes": new_duration_minutes,
        "end_time": availability["end_time"],
        "status": "confirmed",
        "reschedule_count": reschedule_count + 1,
        "message": (
            f"Booking {booking_id} was rescheduled successfully."
        ),
    }