from langchain_core.tools import StructuredTool

from src.tools.availability import check_availability
from src.tools.booking import create_booking
from src.tools.cancellation import cancel_booking
from src.tools.customer import get_customer
from src.tools.equipment import (
    calculate_equipment_rental,
    get_equipment_catalog,
)
from src.tools.policy import search_policy
from src.tools.pricing import calculate_booking_price
from src.tools.rescheduling import reschedule_booking
from src.tools.resources import get_resources


# ---------------------------------------------------------
# Availability
# ---------------------------------------------------------

availability_tool = StructuredTool.from_function(
    func=check_availability,
    name="availability_tool",
    description=(
        "Check whether a sports facility is available "
        "for a requested date, time, and duration."
    ),
)


# ---------------------------------------------------------
# Booking
# ---------------------------------------------------------

booking_tool = StructuredTool.from_function(
    func=create_booking,
    name="booking_tool",
    description=(
        "Create a confirmed sports facility booking. "
        "Only use after the user explicitly confirms."
    ),
)


# ---------------------------------------------------------
# Cancellation
# ---------------------------------------------------------

cancellation_tool = StructuredTool.from_function(
    func=cancel_booking,
    name="cancellation_tool",
    description=(
        "Cancel an existing sports facility booking. "
        "Only use after the user explicitly confirms."
    ),
)


# ---------------------------------------------------------
# Rescheduling
# ---------------------------------------------------------

rescheduling_tool = StructuredTool.from_function(
    func=reschedule_booking,
    name="rescheduling_tool",
    description=(
        "Reschedule an existing booking. "
        "Only use after the user explicitly confirms."
    ),
)


# ---------------------------------------------------------
# Pricing
# ---------------------------------------------------------

pricing_tool = StructuredTool.from_function(
    func=calculate_booking_price,
    name="pricing_tool",
    description=(
        "Calculate the exact booking price using "
        "SportMate's deterministic pricing rules."
    ),
)


# ---------------------------------------------------------
# Customer
# ---------------------------------------------------------

customer_tool = StructuredTool.from_function(
    func=get_customer,
    name="customer_tool",
    description=(
        "Look up a registered SportMate customer "
        "using their phone number."
    ),
)


# ---------------------------------------------------------
# Equipment Catalog
# ---------------------------------------------------------

equipment_catalog_tool = StructuredTool.from_function(
    func=get_equipment_catalog,
    name="equipment_catalog_tool",
    description=(
        "Return the SportMate equipment rental catalog "
        "and official equipment prices."
    ),
)


# ---------------------------------------------------------
# Equipment Rental
# ---------------------------------------------------------

equipment_rental_tool = StructuredTool.from_function(
    func=calculate_equipment_rental,
    name="equipment_rental_tool",
    description=(
        "Calculate equipment rental charges for "
        "requested equipment items."
    ),
)


# ---------------------------------------------------------
# Resources
# ---------------------------------------------------------

resources_tool = StructuredTool.from_function(
    func=get_resources,
    name="resources_tool",
    description=(
        "Return all available SportMate sports facilities "
        "and their details."
    ),
)


# ---------------------------------------------------------
# Policy / Knowledge Base
# ---------------------------------------------------------

policy_tool = StructuredTool.from_function(
    func=search_policy,
    name="policy_tool",
    description=(
        "Search the SportMate knowledge base for official "
        "information about cancellation policies, refunds, "
        "rescheduling rules, equipment rental, membership, "
        "opening hours, pricing, payments, and facility "
        "policies. Use this tool for policy or knowledge-base "
        "questions instead of guessing."
    ),
)


# ---------------------------------------------------------
# All Tools
# ---------------------------------------------------------

ALL_TOOLS = [
    availability_tool,
    booking_tool,
    cancellation_tool,
    rescheduling_tool,
    pricing_tool,
    customer_tool,
    equipment_catalog_tool,
    equipment_rental_tool,
    resources_tool,
    policy_tool,
]

