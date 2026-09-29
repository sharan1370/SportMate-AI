from src.tools.availability import check_availability


tests = [
    {
        "name": "Existing BC1 booking",
        "resource_id": "BC1",
        "date": "2026-09-08",
        "time": "18:00",
        "duration": 60,
    },
    {
        "name": "Available BC1 slot",
        "resource_id": "BC1",
        "date": "2026-09-08",
        "time": "20:00",
        "duration": 60,
    },
    {
        "name": "Cancelled TC1 booking",
        "resource_id": "TC1",
        "date": "2026-09-09",
        "time": "07:00",
        "duration": 60,
    },
]


for test in tests:
    result = check_availability(
        resource_id=test["resource_id"],
        booking_date=test["date"],
        start_time=test["time"],
        duration_minutes=test["duration"],
    )

    print(f"\n{test['name']}")
    print(result)