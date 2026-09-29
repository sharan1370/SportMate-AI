from datetime import datetime

from src.database.repository import Repository
from src.tools.availability import check_availability


def create_booking(
    resource_id: str,
    booking_date: str,
    start_time: str,
    duration_minutes: int,
    customer_name: str,
    phone: str,
) -> dict:
    """
    Create a new booking after validating the customer
    and confirming resource availability.
    """

    repository = Repository()

    # 1. Validate customer
    customer = repository.get_customer_by_phone(phone)

    if customer is None:
        return {
            "success": False,
            "reason": f"No customer found with phone number {phone}.",
        }

    # 2. Validate customer name
    if customer["name"].strip().lower() != customer_name.strip().lower():
        return {
            "success": False,
            "reason": (
                "Customer name does not match the registered "
                "customer record."
            ),
        }

    # 3. Check availability
    availability = check_availability(
        resource_id=resource_id,
        booking_date=booking_date,
        start_time=start_time,
        duration_minutes=duration_minutes,
    )

    if not availability["available"]:
        return {
            "success": False,
            "reason": availability["reason"],
            "conflicting_booking_id": availability.get(
                "conflicting_booking_id"
            ),
        }

    # 4. Generate booking ID
    booking_id = repository.get_next_booking_id()

    # 5. Generate creation timestamp
    created_at = datetime.now().isoformat(timespec="seconds")

    # 6. Prepare booking record
    booking = {
        "booking_id": booking_id,
        "resource_id": resource_id,
        "booking_date": booking_date,
        "start_time": start_time,
        "duration_minutes": duration_minutes,
        "customer_name": customer["name"],
        "phone": customer["phone"],
        "status": "confirmed",
        "created_at": created_at,
    }

    # 7. Save booking
    repository.insert_booking(booking)

    # 8. Return confirmation
    return {
        "success": True,
        "booking_id": booking_id,
        "resource_id": resource_id,
        "resource_name": availability["resource_name"],
        "booking_date": booking_date,
        "start_time": start_time,
        "duration_minutes": duration_minutes,
        "end_time": availability["end_time"],
        "customer_name": customer["name"],
        "phone": customer["phone"],
        "status": "confirmed",
        "message": f"Booking {booking_id} created successfully.",
    }