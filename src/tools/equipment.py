from typing import Any


EQUIPMENT = {
    "badminton_racket": {
        "name": "Badminton racket",
        "sport": "badminton",
        "pricing_type": "per_session",
        "price": 50.0,
        "replacement_cost": 1000.0,
    },
    "shuttlecock": {
        "name": "Shuttlecock",
        "sport": "badminton",
        "pricing_type": "per_item",
        "price": 20.0,
        "replacement_cost": 50.0,
    },
    "football": {
        "name": "Football",
        "sport": "football",
        "pricing_type": "per_session",
        "price": 100.0,
        "deposit": 500.0,
        "replacement_cost": 2500.0,
    },
    "tennis_racket": {
        "name": "Tennis racket",
        "sport": "tennis",
        "pricing_type": "per_session",
        "price": 100.0,
        "replacement_cost": 5000.0,
    },
    "tennis_balls": {
        "name": "Tennis balls",
        "sport": "tennis",
        "pricing_type": "per_can",
        "price": 150.0,
        "quantity_per_unit": 3,
        "replacement_cost": 150.0,
    },
}


def get_equipment_catalog() -> dict[str, dict[str, Any]]:
    """Return the complete equipment catalog."""

    return EQUIPMENT.copy()


def get_equipment(
    equipment_name: str,
) -> dict[str, Any] | None:
    """
    Find equipment by name or common identifier.
    """

    normalized_name = (
        equipment_name
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    return EQUIPMENT.get(normalized_name)


def calculate_equipment_cost(
    equipment_name: str,
    quantity: int = 1,
) -> dict[str, Any]:
    """
    Calculate rental cost for equipment.

    Supported pricing:
    - per_session
    - per_item
    - per_can
    """

    if quantity <= 0:
        return {
            "success": False,
            "reason": "Quantity must be greater than 0.",
        }

    equipment = get_equipment(equipment_name)

    if equipment is None:
        return {
            "success": False,
            "reason": (
                f"Equipment '{equipment_name}' is not available "
                "in the SportMate equipment catalog."
            ),
        }

    unit_price = equipment["price"]
    total_price = unit_price * quantity

    result = {
        "success": True,
        "equipment": equipment["name"],
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": total_price,
        "pricing_type": equipment["pricing_type"],
    }

    if "deposit" in equipment:
        result["refundable_deposit"] = (
            equipment["deposit"] * quantity
        )
    else:
        result["refundable_deposit"] = 0.0

    if "quantity_per_unit" in equipment:
        result["items_per_unit"] = equipment[
            "quantity_per_unit"
        ]

    return result


def calculate_equipment_rental(
    equipment_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate the total cost for multiple equipment items.
    """

    if not equipment_items:
        return {
            "success": True,
            "items": [],
            "rental_total": 0.0,
            "refundable_deposit": 0.0,
            "total_payable": 0.0,
        }

    results = []
    rental_total = 0.0
    refundable_deposit = 0.0

    for item in equipment_items:

        equipment_name = item.get("name")
        quantity = int(item.get("quantity", 1))

        result = calculate_equipment_cost(
            equipment_name,
            quantity,
        )

        if not result["success"]:
            return result

        results.append(result)

        rental_total += result["total_price"]
        refundable_deposit += result["refundable_deposit"]

    return {
        "success": True,
        "items": results,
        "rental_total": round(rental_total, 2),
        "refundable_deposit": round(
            refundable_deposit,
            2,
        ),
        "total_payable": round(
            rental_total + refundable_deposit,
            2,
        ),
    }


def calculate_damage_charge(
    equipment_name: str,
    quantity: int = 1,
) -> dict[str, Any]:
    """
    Calculate replacement charge for damaged equipment.
    """

    if quantity <= 0:
        return {
            "success": False,
            "reason": "Quantity must be greater than 0.",
        }

    equipment = get_equipment(equipment_name)

    if equipment is None:
        return {
            "success": False,
            "reason": (
                f"Equipment '{equipment_name}' is not available "
                "in the SportMate equipment catalog."
            ),
        }

    replacement_cost = (
        equipment["replacement_cost"] * quantity
    )

    return {
        "success": True,
        "equipment": equipment["name"],
        "quantity": quantity,
        "replacement_cost_per_item": (
            equipment["replacement_cost"]
        ),
        "damage_charge": replacement_cost,
        "message": (
            f"Damaged {equipment['name']} is charged at "
            "replacement cost."
        ),
    }