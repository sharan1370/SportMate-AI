import sqlite3

connection = sqlite3.connect("db/booking.db")

tables = connection.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("Tables:")
for table in tables:
    print("-", table[0])

print("\nResources:")
for row in connection.execute("SELECT * FROM resources"):
    print(row)

print("\nCustomers:")
for row in connection.execute("SELECT * FROM customers"):
    print(row)

print("\nBookings:")
for row in connection.execute("SELECT * FROM bookings"):
    print(row)

connection.close()