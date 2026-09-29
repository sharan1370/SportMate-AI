from src.database.repository import Repository


repository = Repository()

booking_id = repository.get_next_booking_id()

print("Next booking ID:", booking_id)