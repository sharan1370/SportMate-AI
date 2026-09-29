from datetime import datetime, timedelta

from src.database.repository import Repository


def check_availability(
    resource_id: str,
    booking_date: str,
    start_time: str,
    duration_minutes: int,
    exclude_booking_id: str | None = None,
) -> dict:
    """
    Check whether a resource is available.

    Checks:
    - Resource exists
    - Date/time is valid
    - Minimum duration rules
    - Opening hours
    - Existing confirmed bookings
    - Optionally excludes a booking being rescheduled

    Booking intervals use the standard rule:

        new_start < existing_end
        AND
        new_end > existing_start

    Therefore, a booking ending at exactly 19:00 does not
    conflict with another booking starting at exactly 19:00.
    """

    repository = Repository()

    # ========================================================
    # RESOURCE
    # ========================================================

    resource = repository.get_resource(resource_id)

    if resource is None:
        return {
            "available": False,
            "reason": f"Resource '{resource_id}' does not exist.",
        }

    # ========================================================
    # DATE / TIME
    # ========================================================

    try:
        requested_start = datetime.strptime(
            f"{booking_date} {start_time}",
            "%Y-%m-%d %H:%M",
        )
    except ValueError:
        return {
            "available": False,
            "reason": "Invalid date or time. Use YYYY-MM-DD and HH:MM.",
        }

    # ========================================================
    # DURATION
    # ========================================================

    if duration_minutes <= 0:
        return {
            "available": False,
            "reason": "Duration must be greater than 0 minutes.",
        }

    resource_type = resource["type"]

    if resource_type == "football" and duration_minutes < 60:
        return {
            "available": False,
            "reason": (
                "Football bookings require a minimum duration of "
                "60 minutes."
            ),
        }

    if resource_type == "multipurpose_room" and duration_minutes < 120:
        return {
            "available": False,
            "reason": (
                "Multipurpose Room event bookings require a minimum "
                "duration of 120 minutes."
            ),
        }

    # ========================================================
    # OPENING HOURS
    # ========================================================

    opening_time = datetime.strptime(
        resource["opening_time"],
        "%H:%M",
    ).time()

    closing_time = datetime.strptime(
        resource["closing_time"],
        "%H:%M",
    ).time()

    requested_start_time = requested_start.time()

    requested_end = requested_start + timedelta(
        minutes=duration_minutes
    )

    # Cannot start before opening.
    if requested_start_time < opening_time:
        return {
            "available": False,
            "reason": (
                f"{resource['name']} opens at "
                f"{resource['opening_time']}."
            ),
        }

    # Cannot start at or after closing.
    if requested_start_time >= closing_time:
        return {
            "available": False,
            "reason": (
                f"{resource['name']} closes at "
                f"{resource['closing_time']}."
            ),
        }

    # Cannot finish after closing.
    closing_datetime = datetime.combine(
        requested_start.date(),
        closing_time,
    )

    if requested_end > closing_datetime:
        return {
            "available": False,
            "reason": (
                f"The booking would extend past the closing time "
                f"of {resource['closing_time']}."
            ),
        }

    # ========================================================
    # EXISTING BOOKINGS
    # ========================================================

    existing_bookings = repository.get_bookings_for_resource(
        resource_id,
        booking_date,
    )

    for booking in existing_bookings:

        # Ignore the same booking during rescheduling.
        if (
            exclude_booking_id is not None
            and booking["booking_id"] == exclude_booking_id
        ):
            continue

        existing_start = datetime.strptime(
            f"{booking['booking_date']} {booking['start_time']}",
            "%Y-%m-%d %H:%M",
        )

        existing_end = existing_start + timedelta(
            minutes=booking["duration_minutes"]
        )

        # ====================================================
        # OVERLAP CHECK
        # ====================================================
        #
        # Example:
        #
        # Existing: 18:00 -> 19:00
        # New:      19:00 -> 20:00
        #
        # 19:00 < 19:00 -> False
        #
        # Therefore there is NO conflict.
        #
        # Example:
        #
        # Existing: 18:00 -> 19:00
        # New:      18:30 -> 19:30
        #
        # 18:30 < 19:00 -> True
        # 19:30 > 18:00 -> True
        #
        # Therefore there IS a conflict.
        #

        if (
            requested_start < existing_end
            and requested_end > existing_start
        ):
            return {
                "available": False,
                "reason": (
                    f"Requested slot conflicts with booking "
                    f"{booking['booking_id']}."
                ),
                "conflicting_booking_id": booking["booking_id"],
            }

    # ========================================================
    # AVAILABLE
    # ========================================================

    return {
        "available": True,
        "resource_id": resource_id,
        "resource_name": resource["name"],
        "booking_date": booking_date,
        "start_time": start_time,
        "duration_minutes": duration_minutes,
        "end_time": requested_end.strftime("%H:%M"),
        "message": "Resource is available.",
    }