from dataclasses import dataclass


@dataclass
class Resource:
    resource_id: str
    name: str
    type: str
    capacity: int
    hourly_rate: float
    opening_time: str
    closing_time: str


@dataclass
class Customer:
    phone: str
    name: str
    email: str
    member_since: str


@dataclass
class Booking:
    booking_id: str
    resource_id: str
    booking_date: str
    start_time: str
    duration_minutes: int
    customer_name: str
    phone: str
    status: str
    created_at: str