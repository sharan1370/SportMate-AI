from src.tools.equipment import (
    calculate_damage_charge,
    calculate_equipment_cost,
    calculate_equipment_rental,
    get_equipment,
    get_equipment_catalog,
)


def test_get_equipment_catalog():

    catalog = get_equipment_catalog()

    assert "badminton_racket" in catalog
    assert "shuttlecock" in catalog
    assert "football" in catalog
    assert "tennis_racket" in catalog
    assert "tennis_balls" in catalog


def test_get_badminton_racket():

    equipment = get_equipment(
        "badminton_racket"
    )

    assert equipment is not None
    assert equipment["price"] == 50.0


def test_badminton_racket_cost():

    result = calculate_equipment_cost(
        "badminton_racket",
        2,
    )

    assert result["success"] is True
    assert result["unit_price"] == 50.0
    assert result["total_price"] == 100.0
    assert result["refundable_deposit"] == 0.0


def test_shuttlecock_cost():

    result = calculate_equipment_cost(
        "shuttlecock",
        3,
    )

    assert result["success"] is True
    assert result["total_price"] == 60.0


def test_football_cost_and_deposit():

    result = calculate_equipment_cost(
        "football",
        1,
    )

    assert result["success"] is True
    assert result["total_price"] == 100.0
    assert result["refundable_deposit"] == 500.0


def test_tennis_racket_cost():

    result = calculate_equipment_cost(
        "tennis_racket",
        2,
    )

    assert result["success"] is True
    assert result["total_price"] == 200.0


def test_tennis_balls_cost():

    result = calculate_equipment_cost(
        "tennis_balls",
        2,
    )

    assert result["success"] is True
    assert result["total_price"] == 300.0
    assert result["items_per_unit"] == 3


def test_multiple_equipment_rental():

    result = calculate_equipment_rental(
        [
            {
                "name": "badminton_racket",
                "quantity": 2,
            },
            {
                "name": "shuttlecock",
                "quantity": 3,
            },
        ]
    )

    assert result["success"] is True
    assert result["rental_total"] == 160.0
    assert result["refundable_deposit"] == 0.0
    assert result["total_payable"] == 160.0


def test_football_rental():

    result = calculate_equipment_rental(
        [
            {
                "name": "football",
                "quantity": 1,
            }
        ]
    )

    assert result["success"] is True
    assert result["rental_total"] == 100.0
    assert result["refundable_deposit"] == 500.0
    assert result["total_payable"] == 600.0


def test_damaged_equipment():

    result = calculate_damage_charge(
        "football",
        1,
    )

    assert result["success"] is True
    assert result["damage_charge"] == 2500.0


def test_unknown_equipment():

    result = calculate_equipment_cost(
        "cricket_bat",
        1,
    )

    assert result["success"] is False


def test_invalid_quantity():

    result = calculate_equipment_cost(
        "football",
        0,
    )

    assert result["success"] is False