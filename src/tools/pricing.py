from math import ceil

from src.database.repository import Repository


PEAK_SURCHARGE_RATE = 0.10
MEMBERSHIP_DISCOUNT_RATE = 0.15
FOOTBALL_DEPOSIT = 500.0


def is_peak_hour(
    booking_date: str,
    start_time: str,
) -> bool:
    """
    Determine whether a booking starts during peak hours.

    Peak hours:
    - Weekdays: 6 PM to 9 PM
    - Weekends: all day
    """

    from datetime import datetime

    booking_datetime = datetime.strptime(
        f"{booking_date} {start_time}",
        "%Y-%m-%d %H:%M",
    )

    weekday = booking_datetime.weekday()
    hour = booking_datetime.hour

    # Saturday = 5, Sunday = 6
    if weekday >= 5:
        return True

    return 18 <= hour < 21


def calculate_booking_price(
    resource_id: str,
    booking_date: str,
    start_time: str,
    duration_minutes: int,
    is_member: bool = False,
    equipment: list[dict] | None = None,
) -> dict:
    """
    Calculate the complete booking price.

    Pricing order:
    1. Base booking price
    2. Peak-hour surcharge
    3. Membership discount
    4. Equipment charges
    5. Football refundable deposit
    """

    repository = Repository()

    resource = repository.get_resource(resource_id)

    if resource is None:
        return {
            "success": False,
            "reason": f"Resource '{resource_id}' does not exist.",
        }

    if duration_minutes <= 0:
        return {
            "success": False,
            "reason": "Duration must be greater than 0 minutes.",
        }

    # ---------------------------------
    # Base booking price
    # ---------------------------------

    hourly_rate = float(resource["hourly_rate"])

    base_price = hourly_rate * (duration_minutes / 60)

    # ---------------------------------
    # Peak-hour surcharge
    # ---------------------------------

    peak = is_peak_hour(
        booking_date,
        start_time,
    )

    peak_surcharge = (
        base_price * PEAK_SURCHARGE_RATE
        if peak
        else 0.0
    )

    price_after_peak = base_price + peak_surcharge

    # ---------------------------------
    # Membership discount
    # ---------------------------------

    membership_discount = (
        price_after_peak * MEMBERSHIP_DISCOUNT_RATE
        if is_member
        else 0.0
    )

    booking_price = (
        price_after_peak - membership_discount
    )

    # ---------------------------------
    # Equipment
    # ---------------------------------

    equipment_total = 0.0
    equipment_details = []

    if equipment is not None:

        for item in equipment:

            item_name = item.get("name")
            quantity = int(item.get("quantity", 1))
            unit_price = float(item.get("unit_price", 0))

            if quantity <= 0:
                return {
                    "success": False,
                    "reason": (
                        f"Invalid quantity for equipment "
                        f"'{item_name}'."
                    ),
                }

            item_total = unit_price * quantity

            equipment_total += item_total

            equipment_details.append(
                {
                    "name": item_name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total": item_total,
                }
            )

    # ---------------------------------
    # Football deposit
    # ---------------------------------

    deposit = (
        FOOTBALL_DEPOSIT
        if resource["type"] == "football"
        else 0.0
    )

    # ---------------------------------
    # Final amount
    # ---------------------------------

    total_before_deposit = (
        booking_price + equipment_total
    )

    total_payable = (
        total_before_deposit + deposit
    )

    return {
        "success": True,
        "resource_id": resource_id,
        "resource_name": resource["name"],
        "booking_date": booking_date,
        "start_time": start_time,
        "duration_minutes": duration_minutes,

        "hourly_rate": hourly_rate,

        "base_price": round(base_price, 2),

        "is_peak_hour": peak,
        "peak_surcharge": round(
            peak_surcharge,
            2,
        ),

        "is_member": is_member,
        "membership_discount": round(
            membership_discount,
            2,
        ),

        "booking_price": round(
            booking_price,
            2,
        ),

        "equipment": equipment_details,
        "equipment_total": round(
            equipment_total,
            2,
        ),

        "refundable_deposit": round(
            deposit,
            2,
        ),

        "total_before_deposit": round(
            total_before_deposit,
            2,
        ),

        "total_payable": round(
            total_payable,
            2,
        ),

        "message": (
            f"Total payable amount is "
            f"₹{total_payable:.2f}."
        ),
    }