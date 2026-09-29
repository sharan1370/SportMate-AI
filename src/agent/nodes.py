'''import json
import re
from typing import Any

from groq import Groq

from src.agent.prompts import SYSTEM_PROMPT
from src.agent.state import AgentState
from src.agent.tools import ALL_TOOLS
from src.config.settings import GROQ_API_KEY, GROQ_MODEL


# ============================================================
# GROQ CLIENT
# ============================================================

client = Groq(
    api_key=GROQ_API_KEY,
    max_retries=0,
)


# ============================================================
# TOOL MAP
# ============================================================

TOOL_MAP = {
    tool.name: tool
    for tool in ALL_TOOLS
}


# ============================================================
# GROQ TOOL SCHEMAS
# ============================================================

GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.args,
        },
    }
    for tool in ALL_TOOLS
]


# ============================================================
# MESSAGE HELPERS
# ============================================================

def _convert_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    converted = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")

        converted.append(
            {
                "role": role,
                "content": content,
            }
        )

    return converted


def _clean_thinking(text: str) -> str:
    if not text:
        return ""

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    return text.strip()


# ============================================================
# TRANSIENT STATE RESET
# ============================================================

def _reset_transient_tool_state(
    state: AgentState,
) -> None:
    """
    Clear only the previous tool execution state.

    Persistent conversation state is preserved.
    """

    state["tool_name"] = ""
    state["tool_input"] = {}
    state["tool_result"] = None
    state["last_tool_name"] = ""
    state["last_tool_call_id"] = ""
    state["error"] = None
    state["final_answer"] = ""


# ============================================================
# GENERIC TOOL RESULT FORMATTER
# ============================================================

def _format_tool_result(result: Any) -> str:
    if result is None:
        return ""

    if isinstance(result, str):
        return result.strip()

    try:
        return json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    except TypeError:
        return str(result)


# ============================================================
# AVAILABILITY FORMATTER
# ============================================================

def _format_availability_result(
    result: Any,
) -> str:

    if not isinstance(result, dict):
        return _format_tool_result(result)

    if result.get("success") is False:
        reason = (
            result.get("reason")
            or result.get("message")
        )

        return (
            str(reason)
            if reason
            else "The requested facility is not available."
        )

    resource_id = (
        result.get("resource_id")
        or result.get("resource")
        or result.get("court_id")
    )

    resource_name = result.get("resource_name")
    available = result.get("available")
    booking_date = result.get("booking_date")
    start_time = result.get("start_time")
    duration = result.get("duration_minutes")
    end_time = result.get("end_time")

    if resource_name:
        if resource_id:
            facility = f"{resource_name} ({resource_id})"
        else:
            facility = str(resource_name)
    elif resource_id:
        facility = str(resource_id)
    else:
        facility = "The requested facility"

    if available is True:

        details = []

        if booking_date:
            details.append(str(booking_date))

        if start_time:
            details.append(str(start_time))

        suffix = ""

        if len(details) >= 2:
            suffix = (
                f" on {details[0]}"
                f" at {details[1]}"
            )
        elif len(details) == 1:
            suffix = f" on {details[0]}"

        if duration:
            suffix += f" for {duration} minutes"

        if end_time:
            suffix += f" (until {end_time})"

        return f"Yes, {facility} is available{suffix}."

    if available is False:

        reason = (
            result.get("reason")
            or result.get("message")
        )

        if reason:
            return (
                f"No, {facility} is not available. "
                f"{reason}"
            )

        return (
            f"No, {facility} is not available "
            "for the requested slot."
        )

    return _format_tool_result(result)


# ============================================================
# POLICY FORMATTER
# ============================================================

def _format_policy_result(
    result: Any,
) -> str:

    fallback = (
        "Answer not found in the "
        "SportMate knowledge base."
    )

    if result is None:
        return fallback

    if isinstance(result, str):
        text = result.strip()

        return text if text else fallback

    if isinstance(result, dict):

        if result.get("success") is False:
            return (
                result.get("reason")
                or fallback
            )

        answer = (
            result.get("answer")
            or result.get("message")
            or result.get("content")
        )

        if answer:
            return str(answer).strip()

        results = result.get("results")

        if isinstance(results, list) and results:

            formatted = []

            for item in results:

                if not isinstance(item, dict):
                    continue

                content = (
                    item.get("content")
                    or item.get("text")
                    or item.get("chunk")
                    or item.get("document")
                )

                page = (
                    item.get("page")
                    or item.get("page_number")
                )

                if content:
                    if page:
                        formatted.append(
                            f"{content}\n(Page {page})"
                        )
                    else:
                        formatted.append(
                            str(content)
                        )

            if formatted:
                return "\n\n".join(formatted)

        text = (
            result.get("text")
            or result.get("response")
        )

        if text:
            return str(text).strip()

    return _format_tool_result(result)


# ============================================================
# CUSTOMER NAME PARSING
# ============================================================

def _parse_customer_name(
    text: str,
) -> str | None:

    patterns = [
        r"\bmy\s+name\s+is\s+([A-Za-z]+(?:\s+[A-Za-z]+)+?)(?=\s+(?:and|with)\b|[,.;]|$)",
        r"\bname\s+(?:is|:)\s+([A-Za-z]+(?:\s+[A-Za-z]+)+?)(?=\s+(?:and|with)\b|[,.;]|$)",
        r"\bcustomer\s+name\s+(?:is|:)?\s*([A-Za-z]+(?:\s+[A-Za-z]+)+?)(?=\s+(?:and|with)\b|[,.;]|$)",
        r"\bfor\s+(?:customer\s+)?([A-Za-z]+(?:\s+[A-Za-z]+)+?)(?=\s+(?:and|with)\b|[,.;]|$)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        name = re.sub(
            r"\s+",
            " ",
            match.group(1),
        ).strip()

        name = re.split(
            r"\s+(?:phone|mobile|number)\b",
            name,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        if len(name.split()) >= 2:
            return name

    return None


# ============================================================
# PHONE PARSING
# ============================================================

def _parse_phone(
    text: str,
) -> str | None:

    patterns = [
        r"\b(?:phone|mobile|number|contact)\s*(?:number|no\.?)?\s*(?:is|:)?\s*(\+?\d[\d\s-]{8,14}\d)\b",
        r"\b(\+?\d{10,13})\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        phone = re.sub(
            r"[^\d+]",
            "",
            match.group(1),
        )

        digits = (
            phone[1:]
            if phone.startswith("+")
            else phone
        )

        if 10 <= len(digits) <= 13:
            return phone

    return None


# ============================================================
# RESOURCE ID PARSING
# ============================================================

def _parse_resource_id(
    text: str,
) -> str | None:
    """
    Extract resource IDs.

    Examples:
        BC1
        BC2
        FT1
        TC1
        MR1

    Booking IDs such as B001 and BKG1007
    are explicitly excluded.
    """

    match = re.search(
        r"\b(?!BKG\d+\b)(?!B\d+\b)([A-Za-z]{2,4}\d{1,3})\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1).upper()


# ============================================================
# DATE PARSING
# ============================================================

def _parse_booking_date(
    text: str,
) -> str | None:

    match = re.search(
        r"\b(20\d{2}-\d{2}-\d{2})\b",
        text,
    )

    if not match:
        return None

    return match.group(1)


# ============================================================
# TIME PARSING
# ============================================================

def _parse_start_time(
    text: str,
) -> str | None:

    # 12-hour format

    match = re.search(
        r"\b(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\b",
        text,
        re.IGNORECASE,
    )

    if match:

        hour = int(match.group(1))
        minute = int(match.group(2) or "00")
        meridiem = match.group(3).upper()

        if hour < 1 or hour > 12:
            return None

        if minute < 0 or minute > 59:
            return None

        if meridiem == "PM" and hour != 12:
            hour += 12

        if meridiem == "AM" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    # 24-hour format

    match = re.search(
        r"\b([01]?\d|2[0-3]):([0-5]\d)\b",
        text,
    )

    if match:

        hour = int(match.group(1))
        minute = int(match.group(2))

        return f"{hour:02d}:{minute:02d}"

    return None


# ============================================================
# DURATION PARSING
# ============================================================

def _parse_duration_minutes(
    text: str,
) -> int | None:

    # Hours

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|hr)\b",
        text,
        re.IGNORECASE,
    )

    if match:

        hours = float(match.group(1))

        if hours <= 0:
            return None

        return int(hours * 60)

    # Minutes

    match = re.search(
        r"\b(\d+)\s*(?:minutes?|mins?|min)\b",
        text,
        re.IGNORECASE,
    )

    if match:

        minutes = int(match.group(1))

        if minutes <= 0:
            return None

        return minutes

    return None


# ============================================================
# BOOKING ID PARSING
# ============================================================

def _parse_booking_id(
    text: str,
) -> str | None:

    match = re.search(
        r"\b(?:BKG|B)\d+\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(0).upper()


# ============================================================
# BOOKING DETAIL EXTRACTION
# ============================================================

def _extract_booking_details(
    text: str,
) -> dict[str, Any]:

    return {
        "resource_id": _parse_resource_id(text),
        "booking_date": _parse_booking_date(text),
        "start_time": _parse_start_time(text),
        "duration_minutes": _parse_duration_minutes(text),
        "customer_name": _parse_customer_name(text),
        "phone": _parse_phone(text),
    }


# ============================================================
# MERGE BOOKING DETAILS
# ============================================================

def _merge_booking_details(
    existing: dict[str, Any] | None,
    new_details: dict[str, Any],
) -> dict[str, Any]:

    merged = dict(existing or {})

    for key, value in new_details.items():

        if value not in (None, ""):
            merged[key] = value

    return merged


# ============================================================
# MISSING BOOKING FIELDS
# ============================================================

def _missing_booking_fields(
    details: dict[str, Any],
) -> list[str]:

    labels = {
        "resource_id": "resource/court ID",
        "booking_date": "booking date",
        "start_time": "start time",
        "duration_minutes": "duration",
        "customer_name": "customer name",
        "phone": "phone number",
    }

    return [
        label
        for key, label in labels.items()
        if details.get(key) in (None, "")
    ]


# ============================================================
# BOOKING SUMMARY
# ============================================================

def _build_booking_summary(
    details: dict[str, Any],
) -> str:

    return (
        "Please confirm this booking:\n"
        f"- Facility: {details.get('resource_id')}\n"
        f"- Date: {details.get('booking_date')}\n"
        f"- Start time: {details.get('start_time')}\n"
        f"- Duration: {details.get('duration_minutes')} minutes\n"
        f"- Customer: {details.get('customer_name')}\n"
        f"- Phone: {details.get('phone')}\n\n"
        "Please reply yes/no to confirm."
    )


# ============================================================
# BOOKING REQUEST
# ============================================================

def _handle_booking_request(
    state: AgentState,
) -> AgentState:

    user_message = state.get(
        "user_message",
        "",
    )

    extracted = _extract_booking_details(
        user_message,
    )

    existing = state.get(
        "pending_booking",
    )

    details = _merge_booking_details(
        existing,
        extracted,
    )

    state["intent"] = "booking"
    state["pending_booking"] = details

    missing = _missing_booking_fields(
        details,
    )

    if missing:

        state["tool_name"] = ""
        state["tool_input"] = {}
        state["confirmation_pending"] = False

        state["final_answer"] = (
            "I still need: "
            + ", ".join(missing)
            + "."
        )

        return state

    # All booking information is available.
    # Check availability first.

    state["tool_name"] = "availability_tool"

    state["tool_input"] = {
        "resource_id": details["resource_id"],
        "booking_date": details["booking_date"],
        "start_time": details["start_time"],
        "duration_minutes": details["duration_minutes"],
    }

    state["confirmation_pending"] = False

    return state


# ============================================================
# BOOKING CONFIRMATION
# ============================================================

def _confirm_pending_booking(
    state: AgentState,
) -> AgentState:

    pending = (
        state.get("pending_booking")
        or {}
    )

    if not pending:

        state["confirmation_pending"] = False
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "There is no pending booking to confirm."
        )

        return state

    text = state.get(
        "user_message",
        "",
    ).strip().lower()

    positive = {
        "yes",
        "y",
        "yes please",
        "confirm",
        "confirmed",
        "book it",
        "go ahead",
        "proceed",
    }

    negative = {
        "no",
        "n",
        "cancel",
        "don't",
        "do not",
        "no thanks",
    }

    if (
        text in positive
        or any(
            phrase in text
            for phrase in (
                "yes confirm",
                "yes, confirm",
                "confirm booking",
                "go ahead and book",
                "book it",
            )
        )
    ):

        state["confirmed"] = True
        state["confirmation_pending"] = False

        state["tool_result"] = None
        state["last_tool_name"] = ""
        state["last_tool_call_id"] = ""
        state["error"] = None

        state["tool_name"] = "booking_tool"

        state["tool_input"] = {
            "resource_id": pending["resource_id"],
            "booking_date": pending["booking_date"],
            "start_time": pending["start_time"],
            "duration_minutes": pending["duration_minutes"],
            "customer_name": pending["customer_name"],
            "phone": pending["phone"],
        }

        return state

    if (
        text in negative
        or any(
            phrase in text
            for phrase in (
                "don't book",
                "do not book",
                "cancel the booking",
                "no don't",
            )
        )
    ):

        state["confirmed"] = False
        state["confirmation_pending"] = False
        state["pending_booking"] = None
        state["pending_booking_price"] = None
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Okay, I did not create the booking."
        )

        return state

    state["confirmation_pending"] = True
    state["tool_name"] = ""
    state["tool_input"] = {}

    state["final_answer"] = (
        _build_booking_summary(
            pending,
        )
    )

    return state


# ============================================================
# PRICING SUBJECT EXTRACTION
# ============================================================

def _extract_pricing_subject(
    text: str,
) -> str | None:

    patterns = [
        r"\bprice\s+(?:of|for)\s+(?:a|an|the)?\s*(.+?)(?:\?|$)",
        r"\bcost\s+(?:of|for)\s+(?:a|an|the)?\s*(.+?)(?:\?|$)",
        r"\brate\s+(?:of|for)\s+(?:a|an|the)?\s*(.+?)(?:\?|$)",
        r"\bhow\s+much\s+(?:does|is)\s+(?:a|an|the)?\s*(.+?)(?:\?|$)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        subject = match.group(1).strip()

        subject = re.sub(
            r"\s+for\s+\d+(?:\.\d+)?\s*(?:hours?|hrs?|hr)$",
            "",
            subject,
            flags=re.IGNORECASE,
        ).strip()

        subject = re.sub(
            r"\s+for\s+\d+\s*(?:minutes?|mins?|min)$",
            "",
            subject,
            flags=re.IGNORECASE,
        ).strip()

        if subject:
            return subject

    return None


# ============================================================
# EQUIPMENT NAME EXTRACTION
# ============================================================

def _extract_equipment_items(
    text: str,
) -> list[dict[str, Any]]:

    lower = text.lower()

    equipment_name = None

    if (
        "badminton racket" in lower
        or "badminton racquet" in lower
    ):
        equipment_name = "badminton_racket"

    elif "shuttlecock" in lower:
        equipment_name = "shuttlecock"

    elif "football" in lower and (
        "equipment" in lower
        or "rental" in lower
        or "rent" in lower
    ):
        equipment_name = "football"

    elif (
        "tennis racket" in lower
        or "tennis racquet" in lower
    ):
        equipment_name = "tennis_racket"

    elif (
        "tennis ball" in lower
        or "tennis balls" in lower
    ):
        equipment_name = "tennis_balls"

    if equipment_name is None:
        return []

    quantity = 1

    quantity_patterns = [
        r"\b(\d+)\s+(?:x\s+)?(?:badminton\s+)?rackets?\b",
        r"\b(\d+)\s+shuttlecocks?\b",
        r"\b(\d+)\s+footballs?\b",
        r"\b(\d+)\s+(?:tennis\s+)?rackets?\b",
        r"\b(\d+)\s+(?:cans?\s+of\s+)?tennis\s+balls?\b",
    ]

    for pattern in quantity_patterns:

        match = re.search(
            pattern,
            lower,
        )

        if match:
            quantity = int(match.group(1))
            break

    return [
        {
            "name": equipment_name,
            "quantity": quantity,
        }
    ]


# ============================================================
# EQUIPMENT QUESTION
# ============================================================

def _handle_equipment_question(
    state: AgentState,
) -> AgentState:

    text = state.get(
        "user_message",
        "",
    )

    items = _extract_equipment_items(
        text,
    )

    if not items:

        state["tool_name"] = (
            "equipment_catalog_tool"
        )

        state["tool_input"] = {}

        return state

    state["tool_name"] = (
        "equipment_rental_tool"
    )

    state["tool_input"] = {
        "equipment_items": items,
    }

    return state


# ============================================================
# RESOURCES
# ============================================================

def _handle_resources_request(
    state: AgentState,
) -> AgentState:

    state["tool_name"] = "resources_tool"
    state["tool_input"] = {}

    return state


# ============================================================
# PRICING QUESTION
# ============================================================

def _handle_pricing_question(
    state: AgentState,
) -> AgentState:

    text = state.get(
        "user_message",
        "",
    )

    resource_id = _parse_resource_id(text)
    booking_date = _parse_booking_date(text)
    start_time = _parse_start_time(text)

    duration_minutes = _parse_duration_minutes(text)

    if duration_minutes is None:
        duration_minutes = 60

    equipment_items = _extract_equipment_items(
        text
    )

    if equipment_items:

        state["tool_name"] = (
            "equipment_rental_tool"
        )

        state["tool_input"] = {
            "equipment_items": equipment_items,
        }

        return state

    if resource_id is None:

        pricing_subject = (
            _extract_pricing_subject(text)
        )

        if pricing_subject:

            state["tool_name"] = ""
            state["tool_input"] = {}

            state["final_answer"] = (
                f"Information about "
                f"'{pricing_subject}' "
                "was not found in the "
                "SportMate knowledge base."
            )

            return state

        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Please specify the facility or "
            "equipment you want the price for."
        )

        return state

    if booking_date and start_time:

        state["tool_name"] = "pricing_tool"

        state["tool_input"] = {
            "resource_id": resource_id,
            "booking_date": booking_date,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "is_member": False,
        }

        state["entities"] = {
            **state.get("entities", {}),
            "pricing_resource_id": resource_id,
            "pricing_duration_minutes": duration_minutes,
        }

        return state

    if booking_date and not start_time:

        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Please provide the start time because "
            "pricing can vary by peak hours."
        )

        return state

    if start_time and not booking_date:

        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Please provide the booking date because "
            "pricing can vary by peak hours and weekends."
        )

        return state

    state["intent"] = "pricing"

    state["entities"] = {
        **state.get("entities", {}),
        "pricing_resource_id": resource_id,
        "pricing_duration_minutes": duration_minutes,
    }

    state["tool_name"] = "resources_tool"
    state["tool_input"] = {}

    return state


# ============================================================
# CANCELLATION REQUEST
# ============================================================

def _handle_cancellation_request(
    state: AgentState,
) -> AgentState:

    user_message = state.get(
        "user_message",
        "",
    )

    booking_id = _parse_booking_id(
        user_message
    )

    pending = (
        state.get("pending_cancellation")
        or {}
    )

    if not booking_id:
        booking_id = pending.get(
            "booking_id"
        )

    if not booking_id:

        state["pending_cancellation"] = None
        state["confirmation_pending"] = False
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Please provide the booking ID you want to cancel "
            "(for example, BKG1007)."
        )

        return state

    state["intent"] = "cancellation"

    state["pending_cancellation"] = {
        "booking_id": booking_id,
    }

    state["confirmation_pending"] = True
    state["confirmed"] = False

    state["tool_name"] = ""
    state["tool_input"] = {}

    state["final_answer"] = (
        f"You requested cancellation of booking "
        f"{booking_id}.\n\n"
        "Are you sure you want to cancel it? "
        "Please reply yes/no to confirm."
    )

    return state


# ============================================================
# CANCELLATION CONFIRMATION
# ============================================================

def _confirm_pending_cancellation(
    state: AgentState,
) -> AgentState:

    pending = (
        state.get("pending_cancellation")
        or {}
    )

    booking_id = pending.get(
        "booking_id"
    )

    if not booking_id:

        state["confirmation_pending"] = False
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "There is no pending cancellation to confirm."
        )

        return state

    text = state.get(
        "user_message",
        "",
    ).strip().lower()

    positive = {
        "yes",
        "y",
        "yes please",
        "confirm",
        "confirmed",
        "cancel it",
        "go ahead",
        "proceed",
    }

    negative = {
        "no",
        "n",
        "don't",
        "do not",
        "no thanks",
        "keep it",
        "don't cancel",
        "do not cancel",
    }

    if (
        text in positive
        or any(
            phrase in text
            for phrase in (
                "yes cancel",
                "yes, cancel",
                "yes confirm",
                "yes, confirm",
                "confirm cancellation",
                "cancel the booking",
                "go ahead and cancel",
            )
        )
    ):

        state["confirmed"] = True
        state["confirmation_pending"] = False

        state["tool_result"] = None
        state["last_tool_name"] = ""
        state["last_tool_call_id"] = ""
        state["error"] = None

        state["tool_name"] = (
            "cancellation_tool"
        )

        state["tool_input"] = {
            "booking_id": booking_id,
        }

        return state

    if (
        text in negative
        or any(
            phrase in text
            for phrase in (
                "don't cancel",
                "do not cancel",
                "keep the booking",
                "keep my booking",
                "no cancel",
            )
        )
    ):

        state["confirmed"] = False
        state["confirmation_pending"] = False
        state["pending_cancellation"] = None

        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Okay, I did not cancel the booking."
        )

        return state

    state["confirmation_pending"] = True
    state["tool_name"] = ""
    state["tool_input"] = {}

    state["final_answer"] = (
        f"Please reply yes/no to confirm "
        f"cancellation of booking {booking_id}."
    )

    return state


# ============================================================
# RESCHEDULING DETAIL EXTRACTION
# ============================================================

def _extract_rescheduling_details(
    text: str,
) -> dict[str, Any]:

    return {
        "booking_id": _parse_booking_id(text),
        "new_resource_id": _parse_rescheduling_resource_id(text),
        "new_booking_date": _parse_booking_date(text),
        "new_start_time": _parse_start_time(text),
        "new_duration_minutes": _parse_duration_minutes(text),
    }


# ============================================================
# RESCHEDULING RESOURCE ID PARSER
# ============================================================

def _parse_rescheduling_resource_id(
    text: str,
) -> str | None:

    patterns = [
        r"\bto\s+((?!BKG\d+\b)(?!B\d+\b)[A-Za-z]{2,4}\d{1,3})\b",
        r"\bnew\s+(?:resource|facility|court)\s+((?!BKG\d+\b)(?!B\d+\b)[A-Za-z]{2,4}\d{1,3})\b",
        r"\bresource\s+((?!BKG\d+\b)(?!B\d+\b)[A-Za-z]{2,4}\d{1,3})\b",
        r"\bfacility\s+((?!BKG\d+\b)(?!B\d+\b)[A-Za-z]{2,4}\d{1,3})\b",
        r"\bcourt\s+((?!BKG\d+\b)(?!B\d+\b)[A-Za-z]{2,4}\d{1,3})\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).upper()

    return _parse_resource_id(text)


# ============================================================
# MERGE RESCHEDULING DETAILS
# ============================================================

def _merge_rescheduling_details(
    existing: dict[str, Any] | None,
    new_details: dict[str, Any],
) -> dict[str, Any]:

    merged = dict(existing or {})

    for key, value in new_details.items():

        if value not in (None, ""):
            merged[key] = value

    return merged


# ============================================================
# MISSING RESCHEDULING FIELDS
# ============================================================

def _missing_rescheduling_fields(
    details: dict[str, Any],
) -> list[str]:

    labels = {
        "booking_id": "booking ID",
        "new_resource_id": "new resource/court ID",
        "new_booking_date": "new booking date",
        "new_start_time": "new start time",
        "new_duration_minutes": "new duration",
    }

    return [
        label
        for key, label in labels.items()
        if details.get(key) in (None, "")
    ]


# ============================================================
# RESCHEDULING SUMMARY
# ============================================================

def _build_rescheduling_summary(
    details: dict[str, Any],
) -> str:

    return (
        "Please confirm this rescheduling:\n"
        f"- Booking ID: {details.get('booking_id')}\n"
        f"- New facility: {details.get('new_resource_id')}\n"
        f"- New date: {details.get('new_booking_date')}\n"
        f"- New start time: {details.get('new_start_time')}\n"
        f"- New duration: "
        f"{details.get('new_duration_minutes')} minutes\n\n"
        "Please reply yes/no to confirm."
    )


# ============================================================
# RESCHEDULING REQUEST
# ============================================================

def _handle_rescheduling_request(
    state: AgentState,
) -> AgentState:

    user_message = state.get(
        "user_message",
        "",
    )

    extracted = _extract_rescheduling_details(
        user_message
    )

    existing = (
        state.get("pending_rescheduling")
        or {}
    )

    details = _merge_rescheduling_details(
        existing,
        extracted,
    )

    state["intent"] = "rescheduling"
    state["pending_rescheduling"] = details

    missing = _missing_rescheduling_fields(
        details
    )

    if missing:

        state["tool_name"] = ""
        state["tool_input"] = {}
        state["confirmation_pending"] = False

        state["final_answer"] = (
            "I still need: "
            + ", ".join(missing)
            + "."
        )

        return state

    state["confirmation_pending"] = True
    state["confirmed"] = False

    state["tool_name"] = ""
    state["tool_input"] = {}

    state["final_answer"] = (
        _build_rescheduling_summary(
            details
        )
    )

    return state


# ============================================================
# RESCHEDULING CONFIRMATION
# ============================================================

def _confirm_pending_rescheduling(
    state: AgentState,
) -> AgentState:

    pending = (
        state.get("pending_rescheduling")
        or {}
    )

    if not pending:

        state["confirmation_pending"] = False
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "There is no pending rescheduling request to confirm."
        )

        return state

    text = state.get(
        "user_message",
        "",
    ).strip().lower()

    positive = {
        "yes",
        "y",
        "yes please",
        "confirm",
        "confirmed",
        "go ahead",
        "proceed",
        "reschedule it",
    }

    negative = {
        "no",
        "n",
        "don't",
        "do not",
        "no thanks",
        "keep it",
        "don't reschedule",
        "do not reschedule",
    }

    if (
        text in positive
        or any(
            phrase in text
            for phrase in (
                "yes reschedule",
                "yes, reschedule",
                "confirm rescheduling",
                "go ahead and reschedule",
                "reschedule it",
            )
        )
    ):

        state["confirmed"] = True
        state["confirmation_pending"] = False

        state["tool_result"] = None
        state["last_tool_name"] = ""
        state["last_tool_call_id"] = ""
        state["error"] = None

        state["tool_name"] = (
            "rescheduling_tool"
        )

        state["tool_input"] = {
            "booking_id": pending["booking_id"],
            "new_resource_id": pending["new_resource_id"],
            "new_booking_date": pending["new_booking_date"],
            "new_start_time": pending["new_start_time"],
            "new_duration_minutes": pending[
                "new_duration_minutes"
            ],
        }

        return state

    if (
        text in negative
        or any(
            phrase in text
            for phrase in (
                "don't reschedule",
                "do not reschedule",
                "keep my booking",
                "keep the booking",
                "no reschedule",
            )
        )
    ):

        state["confirmed"] = False
        state["confirmation_pending"] = False
        state["pending_rescheduling"] = None

        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Okay, I did not reschedule the booking."
        )

        return state

    state["confirmation_pending"] = True
    state["tool_name"] = ""
    state["tool_input"] = {}

    state["final_answer"] = (
        _build_rescheduling_summary(
            pending
        )
    )

    return state


# ============================================================
# INTENT DETECTION
# ============================================================

def _detect_intent(
    text: str,
) -> str:

    lower = text.lower().strip()

    # Policy

    policy_phrases = [
        "cancellation policy",
        "cancel policy",
        "refund policy",
        "refund",
        "reschedule policy",
        "rescheduling policy",
        "membership",
        "member discount",
        "opening hours",
        "open time",
        "closing time",
        "payment policy",
        "payment methods",
        "equipment policy",
        "rental policy",
        "no show",
        "no-show",
        "late cancellation",
    ]

    if any(
        phrase in lower
        for phrase in policy_phrases
    ):
        return "policy"

    # Cancellation

    cancellation_phrases = [
        "cancel my booking",
        "cancel booking",
        "cancel the booking",
        "cancel my reservation",
        "cancel reservation",
    ]

    if any(
        phrase in lower
        for phrase in cancellation_phrases
    ):
        return "cancellation"

    # Rescheduling

    reschedule_phrases = [
        "reschedule my booking",
        "reschedule booking",
        "reschedule the booking",
        "change my booking",
        "change booking date",
        "move my booking",
    ]

    if any(
        phrase in lower
        for phrase in reschedule_phrases
    ):
        return "rescheduling"

    # Booking

    booking_phrases = [
        "book ",
        "booked",
        "booking",
        "reserve ",
        "reservation",
    ]

    if any(
        phrase in lower
        for phrase in booking_phrases
    ):
        return "booking"

    # Resources

    resource_listing_phrases = [
        "what sports facilities",
        "what facilities",
        "which facilities",
        "available facilities",
        "list facilities",
        "sports facilities do you have",
        "facilities do you have",
        "what courts do you have",
        "which courts do you have",
        "what sports do you have",
        "which sports do you have",
    ]

    if any(
        phrase in lower
        for phrase in resource_listing_phrases
    ):
        return "resources"

    # Availability

    availability_phrases = [
        "available",
        "availability",
        "is free",
        "free at",
        "free on",
        "is open at",
        "can i use",
    ]

    if any(
        phrase in lower
        for phrase in availability_phrases
    ):
        return "availability"

    # Pricing

    pricing_phrases = [
        "price",
        "pricing",
        "cost",
        "how much",
        "rate",
        "fee",
        "charge",
    ]

    if any(
        phrase in lower
        for phrase in pricing_phrases
    ):
        return "pricing"

    # Equipment

    equipment_phrases = [
        "racket",
        "racquet",
        "shuttlecock",
        "equipment",
        "rental",
        "tennis ball",
        "tennis balls",
    ]

    if any(
        phrase in lower
        for phrase in equipment_phrases
    ):
        return "equipment"

    # Customer

    customer_phrases = [
        "customer details",
        "customer information",
        "my customer details",
        "find customer",
        "customer lookup",
    ]

    if any(
        phrase in lower
        for phrase in customer_phrases
    ):
        return "customer"

    return "policy"


# ============================================================
# AGENT NODE
# ============================================================

def agent_node(
    state: AgentState,
) -> AgentState:

    _reset_transient_tool_state(state)

    user_message = state.get(
        "user_message",
        "",
    )

    # ========================================================
    # IMPORTANT:
    # CONTINUE PENDING MULTI-TURN WORKFLOWS FIRST
    # ========================================================

    # --------------------------------------------------------
    # 1. Confirmation workflow
    # --------------------------------------------------------

    if state.get("confirmation_pending"):

        if state.get("pending_cancellation"):
            state["intent"] = "cancellation"

            return _confirm_pending_cancellation(
                state
            )

        if state.get("pending_rescheduling"):
            state["intent"] = "rescheduling"

            return _confirm_pending_rescheduling(
                state
            )

        if state.get("pending_booking"):
            state["intent"] = "booking"

            return _confirm_pending_booking(
                state
            )

        state["confirmation_pending"] = False
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "There is no pending action to confirm."
        )

        return state

    # --------------------------------------------------------
    # 2. Continue an incomplete booking
    #
    # Example:
    #
    # User:
    # Book BC1 on 2026-09-20 at 7 PM for 1 hour
    #
    # Agent:
    # I still need customer name, phone number.
    #
    # User:
    # My name is Arjun Mehta and my phone number is ...
    #
    # The second message does NOT contain "booking".
    # Therefore normal intent detection would incorrectly
    # classify it as policy.
    #
    # We explicitly continue the pending booking here.
    # --------------------------------------------------------

    if state.get("pending_booking"):

        pending = (
            state.get("pending_booking")
            or {}
        )

        extracted = _extract_booking_details(
            user_message
        )

        updated = _merge_booking_details(
            pending,
            extracted,
        )

        state["intent"] = "booking"
        state["pending_booking"] = updated

        missing = _missing_booking_fields(
            updated
        )

        if missing:

            state["tool_name"] = ""
            state["tool_input"] = {}
            state["confirmation_pending"] = False

            state["final_answer"] = (
                "I still need: "
                + ", ".join(missing)
                + "."
            )

            return state

        # All fields are now complete.
        # Check availability.

        state["tool_name"] = (
            "availability_tool"
        )

        state["tool_input"] = {
            "resource_id": updated["resource_id"],
            "booking_date": updated["booking_date"],
            "start_time": updated["start_time"],
            "duration_minutes": updated[
                "duration_minutes"
            ],
        }

        state["confirmation_pending"] = False

        return state

    # --------------------------------------------------------
    # 3. Continue incomplete rescheduling
    # --------------------------------------------------------

    if state.get("pending_rescheduling"):

        pending = (
            state.get("pending_rescheduling")
            or {}
        )

        extracted = _extract_rescheduling_details(
            user_message
        )

        updated = _merge_rescheduling_details(
            pending,
            extracted,
        )

        state["intent"] = "rescheduling"
        state["pending_rescheduling"] = updated

        missing = _missing_rescheduling_fields(
            updated
        )

        if missing:

            state["tool_name"] = ""
            state["tool_input"] = {}
            state["confirmation_pending"] = False

            state["final_answer"] = (
                "I still need: "
                + ", ".join(missing)
                + "."
            )

            return state

        state["confirmation_pending"] = True
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            _build_rescheduling_summary(
                updated
            )
        )

        return state

    # ========================================================
    # NORMAL INTENT DETECTION
    # ========================================================

    intent = _detect_intent(
        user_message,
    )

    state["intent"] = intent

    # ========================================================
    # BOOKING
    # ========================================================

    if intent == "booking":
        return _handle_booking_request(
            state
        )

    # ========================================================
    # AVAILABILITY
    # ========================================================

    if intent == "availability":

        resource_id = _parse_resource_id(
            user_message
        )

        booking_date = _parse_booking_date(
            user_message
        )

        start_time = _parse_start_time(
            user_message
        )

        duration_minutes = (
            _parse_duration_minutes(
                user_message
            )
        )

        missing = []

        if not resource_id:
            missing.append(
                "resource/court ID"
            )

        if not booking_date:
            missing.append(
                "booking date"
            )

        if not start_time:
            missing.append(
                "start time"
            )

        if not duration_minutes:
            missing.append(
                "duration"
            )

        if missing:

            state["tool_name"] = ""
            state["tool_input"] = {}

            state["final_answer"] = (
                "I still need: "
                + ", ".join(missing)
                + "."
            )

            return state

        state["tool_name"] = (
            "availability_tool"
        )

        state["tool_input"] = {
            "resource_id": resource_id,
            "booking_date": booking_date,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
        }

        return state

    # ========================================================
    # PRICING
    # ========================================================

    if intent == "pricing":
        return _handle_pricing_question(
            state
        )

    # ========================================================
    # EQUIPMENT
    # ========================================================

    if intent == "equipment":
        return _handle_equipment_question(
            state
        )

    # ========================================================
    # RESOURCES
    # ========================================================

    if intent == "resources":
        return _handle_resources_request(
            state
        )

    # ========================================================
    # POLICY
    # ========================================================

    if intent == "policy":

        state["tool_name"] = "policy_tool"

        state["tool_input"] = {
            "query": user_message,
        }

        return state

    # ========================================================
    # CANCELLATION
    # ========================================================

    if intent == "cancellation":
        return _handle_cancellation_request(
            state
        )

    # ========================================================
    # RESCHEDULING
    # ========================================================

    if intent == "rescheduling":
        return _handle_rescheduling_request(
            state
        )

    # ========================================================
    # CUSTOMER
    # ========================================================

    if intent == "customer":

        phone = _parse_phone(
            user_message
        )

        if not phone:

            state["tool_name"] = ""
            state["tool_input"] = {}

            state["final_answer"] = (
                "Please provide the customer's "
                "phone number."
            )

            return state

        state["tool_name"] = (
            "customer_tool"
        )

        state["tool_input"] = {
            "phone": phone,
        }

        return state

    # ========================================================
    # FALLBACK
    # ========================================================

    state["tool_name"] = "policy_tool"

    state["tool_input"] = {
        "query": user_message,
    }

    return state


# ============================================================
# RESOURCE PRICE FORMATTER
# ============================================================

def _format_resource_price_result(
    result: Any,
    resource_id: str,
    duration_minutes: int = 60,
) -> str:

    resources = result

    if isinstance(resources, str):

        try:
            resources = json.loads(
                resources
            )

        except json.JSONDecodeError:

            return (
                f"Pricing information for "
                f"{resource_id} was not found "
                "in the SportMate knowledge base."
            )

    if isinstance(resources, dict):

        if "resources" in resources:
            resources = resources["resources"]
        else:
            resources = [resources]

    if not isinstance(resources, list):

        return (
            f"Pricing information for "
            f"{resource_id} was not found "
            "in the SportMate knowledge base."
        )

    target = None

    for resource in resources:

        if not isinstance(resource, dict):
            continue

        current_id = str(
            resource.get(
                "resource_id",
                "",
            )
        ).upper()

        if current_id == resource_id.upper():

            target = resource
            break

    if target is None:

        return (
            f"Pricing information for "
            f"{resource_id} was not found "
            "in the SportMate knowledge base."
        )

    hourly_rate = target.get(
        "hourly_rate"
    )

    if hourly_rate is None:

        return (
            f"Pricing information for "
            f"{resource_id} was not found "
            "in the SportMate knowledge base."
        )

    hourly_rate = float(
        hourly_rate
    )

    if duration_minutes == 60:

        return (
            f"{resource_id.upper()} costs "
            f"₹{hourly_rate:.0f} per hour."
        )

    total = (
        hourly_rate
        * (duration_minutes / 60)
    )

    return (
        f"{resource_id.upper()} costs "
        f"₹{total:.2f} for "
        f"{duration_minutes} minutes "
        "at the standard hourly rate."
    )


# ============================================================
# TOOL EXECUTION NODE
# ============================================================

def tool_execution_node(
    state: AgentState,
) -> AgentState:

    tool_name = state.get(
        "tool_name"
    )

    if not tool_name:
        return state

    tool = TOOL_MAP.get(
        tool_name
    )

    if tool is None:

        state["error"] = (
            f"Unknown tool: {tool_name}"
        )

        state["final_answer"] = (
            "Sorry, I could not execute "
            "the requested action."
        )

        state["tool_name"] = ""

        return state

    tool_input = state.get(
        "tool_input",
        {},
    )

    try:

        result = tool.invoke(
            tool_input
        )

        state["tool_result"] = result
        state["last_tool_name"] = tool_name
        state["last_tool_call_id"] = ""

    except Exception as exc:

        state["error"] = str(exc)

        state["final_answer"] = (
            "Sorry, something went wrong.\n"
            f"Error: {exc}"
        )

        state["tool_name"] = ""

        return state

    # ========================================================
    # AVAILABILITY RESULT
    # ========================================================

    if tool_name == "availability_tool":

        state["final_answer"] = (
            _format_availability_result(
                result
            )
        )

        is_booking_workflow = (
            state.get("intent") == "booking"
            and bool(
                state.get(
                    "pending_booking"
                )
            )
        )

        if not is_booking_workflow:

            state["tool_name"] = ""

            return state

        if (
            isinstance(result, dict)
            and result.get("available") is True
        ):

            pending = (
                state.get(
                    "pending_booking"
                )
                or {}
            )

            pricing_input = {
                "resource_id": pending.get(
                    "resource_id"
                ),
                "booking_date": pending.get(
                    "booking_date"
                ),
                "start_time": pending.get(
                    "start_time"
                ),
                "duration_minutes": pending.get(
                    "duration_minutes"
                ),
                "is_member": False,
            }

            required = [
                "resource_id",
                "booking_date",
                "start_time",
                "duration_minutes",
            ]

            if any(
                pricing_input.get(field)
                in (None, "")
                for field in required
            ):

                state["tool_name"] = ""

                state["final_answer"] = (
                    "I couldn't calculate the "
                    "booking price because some "
                    "booking details are missing."
                )

                return state

            state["tool_name"] = (
                "pricing_tool"
            )

            state["tool_input"] = pricing_input

            return state

        state["tool_name"] = ""

        return state

    # ========================================================
    # PRICING RESULT
    # ========================================================

    if tool_name == "pricing_tool":

        if isinstance(result, dict):

            if result.get("success") is False:

                state["final_answer"] = (
                    result.get("reason")
                    or "Unable to calculate "
                    "the booking price."
                )

                state["tool_name"] = ""

                return state

            pending = state.get(
                "pending_booking"
            )

            if (
                state.get("intent") == "booking"
                and pending
            ):

                state["pending_booking_price"] = (
                    result
                )

                state["confirmation_pending"] = True
                state["tool_name"] = ""

                resource_id = pending.get(
                    "resource_id"
                )

                booking_date = pending.get(
                    "booking_date"
                )

                start_time = pending.get(
                    "start_time"
                )

                duration = pending.get(
                    "duration_minutes"
                )

                total = result.get(
                    "total_payable"
                )

                if total is not None:

                    state["final_answer"] = (
                        "The requested slot is available.\n\n"
                        f"Booking: {resource_id}\n"
                        f"Date: {booking_date}\n"
                        f"Time: {start_time}\n"
                        f"Duration: {duration} minutes\n"
                        f"Total payable: ₹{float(total):.2f}\n\n"
                        "Please reply yes/no to confirm."
                    )

                else:

                    state["final_answer"] = (
                        _format_tool_result(
                            result
                        )
                        + "\n\n"
                        "Please reply yes/no to confirm."
                    )

                return state

        state["final_answer"] = (
            _format_tool_result(
                result
            )
        )

        state["tool_name"] = ""

        return state

    # ========================================================
    # EQUIPMENT RENTAL RESULT
    # ========================================================

    if tool_name == "equipment_rental_tool":

        if isinstance(result, dict):

            if result.get("success") is False:

                state["final_answer"] = (
                    result.get("reason")
                    or (
                        "Unable to calculate "
                        "equipment rental cost."
                    )
                )

                state["tool_name"] = ""

                return state

            items = result.get(
                "items",
                [],
            )

            rental_total = result.get(
                "rental_total",
                0.0,
            )

            refundable_deposit = result.get(
                "refundable_deposit",
                0.0,
            )

            total_payable = result.get(
                "total_payable",
                rental_total,
            )

            equipment_lines = []

            for item in items:

                if not isinstance(item, dict):
                    continue

                equipment_name = item.get(
                    "equipment",
                    "Equipment",
                )

                quantity = item.get(
                    "quantity",
                    1,
                )

                unit_price = item.get(
                    "unit_price",
                    0.0,
                )

                equipment_lines.append(
                    f"- {equipment_name}: "
                    f"{quantity} × "
                    f"₹{float(unit_price):.2f}"
                )

            if equipment_lines:

                answer = (
                    "Equipment rental:\n"
                    + "\n".join(
                        equipment_lines
                    )
                    + "\n\n"
                    f"Rental total: "
                    f"₹{float(rental_total):.2f}."
                )

            else:

                answer = (
                    "Equipment rental cost is "
                    f"₹{float(rental_total):.2f}."
                )

            if refundable_deposit:

                answer += (
                    " Refundable deposit: "
                    f"₹{float(refundable_deposit):.2f}."
                )

            if (
                refundable_deposit
                and total_payable is not None
            ):

                answer += (
                    " Total payable including "
                    "deposit: "
                    f"₹{float(total_payable):.2f}."
                )

            state["final_answer"] = answer

        else:

            state["final_answer"] = (
                _format_tool_result(
                    result
                )
            )

        state["tool_name"] = ""

        return state

    # ========================================================
    # RESOURCES RESULT
    # ========================================================

    if tool_name == "resources_tool":

        entities = state.get(
            "entities",
            {},
        )

        pricing_resource_id = entities.get(
            "pricing_resource_id"
        )

        if (
            state.get("intent") == "pricing"
            and pricing_resource_id
        ):

            duration = entities.get(
                "pricing_duration_minutes",
                60,
            )

            state["final_answer"] = (
                _format_resource_price_result(
                    result,
                    pricing_resource_id,
                    duration,
                )
            )

        else:

            state["final_answer"] = (
                _format_tool_result(
                    result
                )
            )

        state["tool_name"] = ""

        return state

    # ========================================================
    # POLICY RESULT
    # ========================================================

    if tool_name == "policy_tool":

        state["final_answer"] = (
            _format_policy_result(
                result
            )
        )

        state["tool_name"] = ""

        return state

    # ========================================================
    # CUSTOMER RESULT
    # ========================================================

    if tool_name == "customer_tool":

        state["final_answer"] = (
            _format_tool_result(
                result
            )
        )

        state["tool_name"] = ""

        return state

    # ========================================================
    # EQUIPMENT CATALOG RESULT
    # ========================================================

    if tool_name == "equipment_catalog_tool":

        state["final_answer"] = (
            _format_tool_result(
                result
            )
        )

        state["tool_name"] = ""

        return state

    # ========================================================
    # BOOKING RESULT
    # ========================================================

    if tool_name == "booking_tool":

        if isinstance(result, dict):

            if result.get("success") is True:

                booking_id = (
                    result.get("booking_id")
                    or result.get("id")
                )

                if booking_id:

                    state["final_answer"] = (
                        "Booking created successfully.\n"
                        f"Booking ID: {booking_id}"
                    )

                else:

                    state["final_answer"] = (
                        result.get("message")
                        or "Booking created successfully."
                    )

                state["pending_booking"] = None
                state["pending_booking_price"] = None
                state["confirmation_pending"] = False
                state["confirmed"] = True

            else:

                state["final_answer"] = (
                    result.get("reason")
                    or result.get("message")
                    or "The booking could not be created."
                )

        else:

            state["final_answer"] = (
                _format_tool_result(
                    result
                )
            )

        state["tool_name"] = ""

        return state

    # ========================================================
    # CANCELLATION RESULT
    # ========================================================

    if tool_name == "cancellation_tool":

        if isinstance(result, dict):

            if result.get("success") is True:

                booking_id = (
                    result.get("booking_id")
                    or result.get("id")
                )

                if booking_id:

                    state["final_answer"] = (
                        f"Booking {booking_id} "
                        "was cancelled successfully."
                    )

                else:

                    state["final_answer"] = (
                        result.get("message")
                        or "The booking was cancelled successfully."
                    )

            else:

                state["final_answer"] = (
                    result.get("reason")
                    or result.get("message")
                    or "The booking could not be cancelled."
                )

        else:

            state["final_answer"] = (
                _format_tool_result(
                    result
                )
            )

        state["tool_name"] = ""
        state["confirmation_pending"] = False
        state["pending_cancellation"] = None
        state["confirmed"] = False

        return state

    # ========================================================
    # RESCHEDULING RESULT
    # ========================================================

    if tool_name == "rescheduling_tool":

        if isinstance(result, dict):

            if result.get("success") is True:

                booking_id = (
                    result.get("booking_id")
                    or result.get("id")
                )

                if booking_id:

                    state["final_answer"] = (
                        f"Booking {booking_id} "
                        "was rescheduled successfully."
                    )

                else:

                    state["final_answer"] = (
                        result.get("message")
                        or "The booking was rescheduled successfully."
                    )

                state["pending_rescheduling"] = None
                state["confirmed"] = True

            else:

                state["final_answer"] = (
                    result.get("reason")
                    or result.get("message")
                    or "The booking could not be rescheduled."
                )

        else:

            state["final_answer"] = (
                _format_tool_result(
                    result
                )
            )

        state["tool_name"] = ""
        state["confirmation_pending"] = False

        return state

    # ========================================================
    # FALLBACK
    # ========================================================

    state["final_answer"] = (
        _format_tool_result(
            result
        )
    )

    state["tool_name"] = ""

    return state'''


import json
import re
from datetime import date, timedelta
from typing import Any

from groq import Groq

from src.agent.prompts import SYSTEM_PROMPT
from src.agent.state import AgentState
from src.agent.tools import ALL_TOOLS
from src.config.settings import GROQ_API_KEY, GROQ_MODEL


# ============================================================
# GROQ CLIENT
# ============================================================

client = Groq(
    api_key=GROQ_API_KEY,
    max_retries=0,
)


# ============================================================
# TOOL MAP
# ============================================================

TOOL_MAP = {
    tool.name: tool
    for tool in ALL_TOOLS
}


# ============================================================
# GROQ TOOL SCHEMAS
# ============================================================

GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.args,
        },
    }
    for tool in ALL_TOOLS
]


# ============================================================
# MESSAGE HELPERS
# ============================================================

def _convert_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    converted = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")

        converted.append(
            {
                "role": role,
                "content": content,
            }
        )

    return converted


def _clean_thinking(text: str) -> str:
    if not text:
        return ""

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    return text.strip()


# ============================================================
# TRANSIENT STATE RESET
# ============================================================

def _reset_transient_tool_state(
    state: AgentState,
) -> None:
    """
    Clear only previous tool execution state.

    Persistent conversation state is preserved.
    """

    state["tool_name"] = ""
    state["tool_input"] = {}
    state["tool_result"] = None
    state["last_tool_name"] = ""
    state["last_tool_call_id"] = ""
    state["error"] = None
    state["final_answer"] = ""


# ============================================================
# GENERIC TOOL RESULT FORMATTER
# ============================================================

def _format_tool_result(result: Any) -> str:
    if result is None:
        return ""

    if isinstance(result, str):
        return result.strip()

    try:
        return json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    except TypeError:
        return str(result)


# ============================================================
# AVAILABILITY FORMATTER
# ============================================================

def _format_availability_result(
    result: Any,
) -> str:

    if not isinstance(result, dict):
        return _format_tool_result(result)

    if result.get("success") is False:
        reason = (
            result.get("reason")
            or result.get("message")
        )

        return (
            str(reason)
            if reason
            else "The requested facility is not available."
        )

    resource_id = (
        result.get("resource_id")
        or result.get("resource")
        or result.get("court_id")
    )

    resource_name = result.get("resource_name")
    available = result.get("available")
    booking_date = result.get("booking_date")
    start_time = result.get("start_time")
    duration = result.get("duration_minutes")
    end_time = result.get("end_time")

    if resource_name:
        if resource_id:
            facility = f"{resource_name} ({resource_id})"
        else:
            facility = str(resource_name)
    elif resource_id:
        facility = str(resource_id)
    else:
        facility = "The requested facility"

    if available is True:

        details = []

        if booking_date:
            details.append(str(booking_date))

        if start_time:
            details.append(str(start_time))

        suffix = ""

        if len(details) >= 2:
            suffix = (
                f" on {details[0]}"
                f" at {details[1]}"
            )
        elif len(details) == 1:
            suffix = f" on {details[0]}"

        if duration:
            suffix += f" for {duration} minutes"

        if end_time:
            suffix += f" (until {end_time})"

        return f"Yes, {facility} is available{suffix}."

    if available is False:

        reason = (
            result.get("reason")
            or result.get("message")
        )

        if reason:
            return (
                f"No, {facility} is not available. "
                f"{reason}"
            )

        return (
            f"No, {facility} is not available "
            "for the requested slot."
        )

    return _format_tool_result(result)


# ============================================================
# POLICY FORMATTER
# ============================================================

def _format_policy_result(
    result: Any,
) -> str:

    fallback = (
        "Answer not found in the "
        "SportMate knowledge base."
    )

    if result is None:
        return fallback

    if isinstance(result, str):
        text = result.strip()
        return text if text else fallback

    if isinstance(result, dict):

        if result.get("success") is False:
            return (
                result.get("reason")
                or fallback
            )

        answer = (
            result.get("answer")
            or result.get("message")
            or result.get("content")
        )

        if answer:
            return str(answer).strip()

        results = result.get("results")

        if isinstance(results, list) and results:

            formatted = []

            for item in results:

                if not isinstance(item, dict):
                    continue

                content = (
                    item.get("content")
                    or item.get("text")
                    or item.get("chunk")
                    or item.get("document")
                )

                page = (
                    item.get("page")
                    or item.get("page_number")
                )

                if content:
                    if page:
                        formatted.append(
                            f"{content}\n(Page {page})"
                        )
                    else:
                        formatted.append(
                            str(content)
                        )

            if formatted:
                return "\n\n".join(formatted)

        text = (
            result.get("text")
            or result.get("response")
        )

        if text:
            return str(text).strip()

    return _format_tool_result(result)


# ============================================================
# CUSTOMER NAME PARSING
# ============================================================

def _parse_customer_name(
    text: str,
) -> str | None:

    patterns = [
        r"\bmy\s+name\s+is\s+([A-Za-z]+(?:\s+[A-Za-z]+)+?)(?=\s+(?:and|with)\b|[,.;]|$)",
        r"\bname\s+(?:is|:)\s+([A-Za-z]+(?:\s+[A-Za-z]+)+?)(?=\s+(?:and|with)\b|[,.;]|$)",
        r"\bcustomer\s+name\s+(?:is|:)?\s*([A-Za-z]+(?:\s+[A-Za-z]+)+?)(?=\s+(?:and|with)\b|[,.;]|$)",
        r"\bfor\s+(?:customer\s+)?([A-Za-z]+(?:\s+[A-Za-z]+)+?)(?=\s+(?:and|with)\b|[,.;]|$)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        name = re.sub(
            r"\s+",
            " ",
            match.group(1),
        ).strip()

        name = re.split(
            r"\s+(?:phone|mobile|number)\b",
            name,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        if len(name.split()) >= 2:
            return name

    return None


# ============================================================
# PHONE PARSING
# ============================================================

def _parse_phone(
    text: str,
) -> str | None:

    patterns = [
        r"\b(?:phone|mobile|number|contact)\s*(?:number|no\.?)?\s*(?:is|:)?\s*(\+?\d[\d\s-]{8,14}\d)\b",
        r"\b(\+?\d{10,13})\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        phone = re.sub(
            r"[^\d+]",
            "",
            match.group(1),
        )

        digits = (
            phone[1:]
            if phone.startswith("+")
            else phone
        )

        if 10 <= len(digits) <= 13:
            return phone

    return None


# ============================================================
# RESOURCE ID PARSING
# ============================================================

def _parse_resource_id(
    text: str,
) -> str | None:
    """
    Parse resource IDs and natural facility names.

    Examples:
        BC1
        BC2
        FT1
        TC1
        MR1

        badminton court 1 -> BC1
        badminton court 2 -> BC2
        badminton court   -> BC1
        tennis court      -> TC1
        football turf     -> FT1
        multipurpose room -> MR1
    """

    lower = text.lower()

    # --------------------------------------------------------
    # Explicit resource ID
    # --------------------------------------------------------

    match = re.search(
        r"\b(?!BKG\d+\b)(?!B\d+\b)"
        r"([A-Za-z]{2,4}\d{1,3})\b",
        text,
        re.IGNORECASE,
    )

    if match:
        return match.group(1).upper()

    # --------------------------------------------------------
    # Badminton
    # --------------------------------------------------------

    if (
        "badminton court 1" in lower
        or "badminton court one" in lower
    ):
        return "BC1"

    if (
        "badminton court 2" in lower
        or "badminton court two" in lower
    ):
        return "BC2"

    if "badminton court" in lower:
        return "BC1"

    # --------------------------------------------------------
    # Tennis
    # --------------------------------------------------------

    if "tennis court" in lower:
        return "TC1"

    # --------------------------------------------------------
    # Football
    # --------------------------------------------------------

    if (
        "football turf" in lower
        or "football field" in lower
        or "football ground" in lower
    ):
        return "FT1"

    # --------------------------------------------------------
    # Multipurpose room
    # --------------------------------------------------------

    if (
        "multipurpose room" in lower
        or "multi purpose room" in lower
    ):
        return "MR1"

    return None


# ============================================================
# DATE PARSING
# ============================================================

def _parse_booking_date(
    text: str,
) -> str | None:
    """
    Parse explicit and relative dates.

    Examples:
        2026-09-22 -> 2026-09-22
        tomorrow   -> current date + 1 day
        today      -> current date
    """

    lower = text.lower()

    # Explicit ISO date
    match = re.search(
        r"\b(20\d{2}-\d{2}-\d{2})\b",
        text,
    )

    if match:
        return match.group(1)

    today = date.today()

    if re.search(r"\btomorrow\b", lower):
        return (
            today + timedelta(days=1)
        ).isoformat()

    if re.search(r"\btoday\b", lower):
        return today.isoformat()

    return None


# ============================================================
# TIME PARSING
# ============================================================

def _parse_start_time(
    text: str,
) -> str | None:

    # --------------------------------------------------------
    # 12-hour format
    # --------------------------------------------------------

    match = re.search(
        r"(?<!\d)(\d{1,2})(?::([0-5]\d))?\s*(AM|PM)\b",
        text,
        re.IGNORECASE,
    )

    if match:

        hour = int(match.group(1))
        minute = int(match.group(2) or "00")
        meridiem = match.group(3).upper()

        if hour < 1 or hour > 12:
            return None

        if meridiem == "PM" and hour != 12:
            hour += 12

        if meridiem == "AM" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    # --------------------------------------------------------
    # 24-hour format
    # --------------------------------------------------------

    match = re.search(
        r"(?<!\d)([01]\d|2[0-3]):([0-5]\d)(?!\d)",
        text,
    )

    if match:

        hour = int(match.group(1))
        minute = int(match.group(2))

        return f"{hour:02d}:{minute:02d}"

    return None


# ============================================================
# DURATION PARSING
# ============================================================

def _parse_duration_minutes(
    text: str,
) -> int | None:

    # Hours
    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|hr)\b",
        text,
        re.IGNORECASE,
    )

    if match:

        hours = float(match.group(1))

        if hours <= 0:
            return None

        return int(hours * 60)

    # Minutes
    match = re.search(
        r"\b(\d+)\s*(?:minutes?|mins?|min)\b",
        text,
        re.IGNORECASE,
    )

    if match:

        minutes = int(match.group(1))

        if minutes <= 0:
            return None

        return minutes

    return None


# ============================================================
# BOOKING ID PARSING
# ============================================================

def _parse_booking_id(
    text: str,
) -> str | None:

    match = re.search(
        r"\b(?:BKG|B)\d+\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(0).upper()


# ============================================================
# BOOKING DETAIL EXTRACTION
# ============================================================

def _extract_booking_details(
    text: str,
) -> dict[str, Any]:

    return {
        "resource_id": _parse_resource_id(text),
        "booking_date": _parse_booking_date(text),
        "start_time": _parse_start_time(text),
        "duration_minutes": _parse_duration_minutes(text),
        "customer_name": _parse_customer_name(text),
        "phone": _parse_phone(text),
    }


# ============================================================
# MERGE BOOKING DETAILS
# ============================================================

def _merge_booking_details(
    existing: dict[str, Any] | None,
    new_details: dict[str, Any],
) -> dict[str, Any]:

    merged = dict(existing or {})

    for key, value in new_details.items():

        if value not in (None, ""):
            merged[key] = value

    return merged


# ============================================================
# MISSING BOOKING FIELDS
# ============================================================

def _missing_booking_fields(
    details: dict[str, Any],
) -> list[str]:

    labels = {
        "resource_id": "resource/court ID",
        "booking_date": "booking date",
        "start_time": "start time",
        "duration_minutes": "duration",
        "customer_name": "customer name",
        "phone": "phone number",
    }

    return [
        label
        for key, label in labels.items()
        if details.get(key) in (None, "")
    ]


# ============================================================
# BOOKING SUMMARY
# ============================================================

def _build_booking_summary(
    details: dict[str, Any],
) -> str:

    return (
        "Please confirm this booking:\n"
        f"- Facility: {details.get('resource_id')}\n"
        f"- Date: {details.get('booking_date')}\n"
        f"- Start time: {details.get('start_time')}\n"
        f"- Duration: {details.get('duration_minutes')} minutes\n"
        f"- Customer: {details.get('customer_name')}\n"
        f"- Phone: {details.get('phone')}\n\n"
        "Please reply yes/no to confirm."
    )


# ============================================================
# BOOKING REQUEST
# ============================================================

def _handle_booking_request(
    state: AgentState,
) -> AgentState:

    user_message = state.get(
        "user_message",
        "",
    )

    extracted = _extract_booking_details(
        user_message,
    )

    existing = state.get(
        "pending_booking",
    )

    details = _merge_booking_details(
        existing,
        extracted,
    )

    state["intent"] = "booking"
    state["pending_booking"] = details

    missing = _missing_booking_fields(
        details,
    )

    if missing:

        state["tool_name"] = ""
        state["tool_input"] = {}
        state["confirmation_pending"] = False

        state["final_answer"] = (
            "I still need: "
            + ", ".join(missing)
            + "."
        )

        return state

    state["tool_name"] = "availability_tool"

    state["tool_input"] = {
        "resource_id": details["resource_id"],
        "booking_date": details["booking_date"],
        "start_time": details["start_time"],
        "duration_minutes": details["duration_minutes"],
    }

    state["confirmation_pending"] = False

    return state


# ============================================================
# BOOKING CONFIRMATION
# ============================================================

def _confirm_pending_booking(
    state: AgentState,
) -> AgentState:

    pending = (
        state.get("pending_booking")
        or {}
    )

    if not pending:

        state["confirmation_pending"] = False
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "There is no pending booking to confirm."
        )

        return state

    text = state.get(
        "user_message",
        "",
    ).strip().lower()

    positive = {
        "yes",
        "y",
        "yes please",
        "confirm",
        "confirmed",
        "book it",
        "go ahead",
        "proceed",
    }

    negative = {
        "no",
        "n",
        "cancel",
        "don't",
        "do not",
        "no thanks",
    }

    if (
        text in positive
        or any(
            phrase in text
            for phrase in (
                "yes confirm",
                "yes, confirm",
                "confirm booking",
                "go ahead and book",
                "book it",
            )
        )
    ):

        state["confirmed"] = True
        state["confirmation_pending"] = False

        state["tool_result"] = None
        state["last_tool_name"] = ""
        state["last_tool_call_id"] = ""
        state["error"] = None

        state["tool_name"] = "booking_tool"

        state["tool_input"] = {
            "resource_id": pending["resource_id"],
            "booking_date": pending["booking_date"],
            "start_time": pending["start_time"],
            "duration_minutes": pending["duration_minutes"],
            "customer_name": pending["customer_name"],
            "phone": pending["phone"],
        }

        return state

    if (
        text in negative
        or any(
            phrase in text
            for phrase in (
                "don't book",
                "do not book",
                "cancel the booking",
                "no don't",
            )
        )
    ):

        state["confirmed"] = False
        state["confirmation_pending"] = False
        state["pending_booking"] = None
        state["pending_booking_price"] = None
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Okay, I did not create the booking."
        )

        return state

    state["confirmation_pending"] = True
    state["tool_name"] = ""
    state["tool_input"] = {}

    state["final_answer"] = (
        _build_booking_summary(
            pending,
        )
    )

    return state


# ============================================================
# PRICING SUBJECT EXTRACTION
# ============================================================

def _extract_pricing_subject(
    text: str,
) -> str | None:

    patterns = [
        r"\bprice\s+(?:of|for)\s+(?:a|an|the)?\s*(.+?)(?:\?|$)",
        r"\bcost\s+(?:of|for)\s+(?:a|an|the)?\s*(.+?)(?:\?|$)",
        r"\brate\s+(?:of|for)\s+(?:a|an|the)?\s*(.+?)(?:\?|$)",
        r"\bhow\s+much\s+(?:does|is)\s+(?:a|an|the)?\s*(.+?)(?:\?|$)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        subject = match.group(1).strip()

        subject = re.sub(
            r"\s+for\s+\d+(?:\.\d+)?\s*(?:hours?|hrs?|hr)$",
            "",
            subject,
            flags=re.IGNORECASE,
        ).strip()

        subject = re.sub(
            r"\s+for\s+\d+\s*(?:minutes?|mins?|min)$",
            "",
            subject,
            flags=re.IGNORECASE,
        ).strip()

        if subject:
            return subject

    return None


# ============================================================
# EQUIPMENT NAME EXTRACTION
# ============================================================

def _extract_equipment_items(
    text: str,
) -> list[dict[str, Any]]:

    lower = text.lower()

    equipment_name = None

    if (
        "badminton racket" in lower
        or "badminton racquet" in lower
    ):
        equipment_name = "badminton_racket"

    elif "shuttlecock" in lower:
        equipment_name = "shuttlecock"

    elif "football" in lower and (
        "equipment" in lower
        or "rental" in lower
        or "rent" in lower
    ):
        equipment_name = "football"

    elif (
        "tennis racket" in lower
        or "tennis racquet" in lower
    ):
        equipment_name = "tennis_racket"

    elif (
        "tennis ball" in lower
        or "tennis balls" in lower
    ):
        equipment_name = "tennis_balls"

    if equipment_name is None:
        return []

    quantity = 1

    quantity_patterns = [
        r"\b(\d+)\s+(?:x\s+)?(?:badminton\s+)?rackets?\b",
        r"\b(\d+)\s+shuttlecocks?\b",
        r"\b(\d+)\s+footballs?\b",
        r"\b(\d+)\s+(?:tennis\s+)?rackets?\b",
        r"\b(\d+)\s+(?:cans?\s+of\s+)?tennis\s+balls?\b",
    ]

    for pattern in quantity_patterns:

        match = re.search(
            pattern,
            lower,
        )

        if match:
            quantity = int(match.group(1))
            break

    return [
        {
            "name": equipment_name,
            "quantity": quantity,
        }
    ]


# ============================================================
# EQUIPMENT QUESTION
# ============================================================

def _handle_equipment_question(
    state: AgentState,
) -> AgentState:

    text = state.get(
        "user_message",
        "",
    )

    items = _extract_equipment_items(
        text,
    )

    if not items:

        state["tool_name"] = (
            "equipment_catalog_tool"
        )

        state["tool_input"] = {}

        return state

    state["tool_name"] = (
        "equipment_rental_tool"
    )

    state["tool_input"] = {
        "equipment_items": items,
    }

    return state


# ============================================================
# RESOURCES
# ============================================================

def _handle_resources_request(
    state: AgentState,
) -> AgentState:

    state["tool_name"] = "resources_tool"
    state["tool_input"] = {}

    return state


# ============================================================
# PRICING QUESTION
# ============================================================

def _handle_pricing_question(
    state: AgentState,
) -> AgentState:

    text = state.get(
        "user_message",
        "",
    )

    resource_id = _parse_resource_id(text)
    booking_date = _parse_booking_date(text)
    start_time = _parse_start_time(text)

    duration_minutes = _parse_duration_minutes(text)

    if duration_minutes is None:
        duration_minutes = 60

    equipment_items = _extract_equipment_items(
        text
    )

    if equipment_items:

        state["tool_name"] = (
            "equipment_rental_tool"
        )

        state["tool_input"] = {
            "equipment_items": equipment_items,
        }

        return state

    if resource_id is None:

        pricing_subject = (
            _extract_pricing_subject(text)
        )

        if pricing_subject:

            state["tool_name"] = ""
            state["tool_input"] = {}

            state["final_answer"] = (
                f"Information about "
                f"'{pricing_subject}' "
                "was not found in the "
                "SportMate knowledge base."
            )

            return state

        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Please specify the facility or "
            "equipment you want the price for."
        )

        return state

    # --------------------------------------------------------
    # If date and time are provided, use pricing_tool.
    # --------------------------------------------------------

    if booking_date and start_time:

        state["tool_name"] = "pricing_tool"

        state["tool_input"] = {
            "resource_id": resource_id,
            "booking_date": booking_date,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "is_member": False,
        }

        state["entities"] = {
            **state.get("entities", {}),
            "pricing_resource_id": resource_id,
            "pricing_duration_minutes": duration_minutes,
        }

        return state

    # --------------------------------------------------------
    # For simple resource price questions, resources_tool
    # provides the standard hourly rate.
    # --------------------------------------------------------

    state["intent"] = "pricing"

    state["entities"] = {
        **state.get("entities", {}),
        "pricing_resource_id": resource_id,
        "pricing_duration_minutes": duration_minutes,
    }

    state["tool_name"] = "resources_tool"
    state["tool_input"] = {}

    return state


# ============================================================
# CANCELLATION REQUEST
# ============================================================

def _handle_cancellation_request(
    state: AgentState,
) -> AgentState:

    user_message = state.get(
        "user_message",
        "",
    )

    booking_id = _parse_booking_id(
        user_message
    )

    pending = (
        state.get("pending_cancellation")
        or {}
    )

    if not booking_id:
        booking_id = pending.get(
            "booking_id"
        )

    if not booking_id:

        state["pending_cancellation"] = None
        state["confirmation_pending"] = False
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Please provide the booking ID you want to cancel "
            "(for example, BKG1007)."
        )

        return state

    state["intent"] = "cancellation"

    state["pending_cancellation"] = {
        "booking_id": booking_id,
    }

    state["confirmation_pending"] = True
    state["confirmed"] = False

    state["tool_name"] = ""
    state["tool_input"] = {}

    state["final_answer"] = (
        f"You requested cancellation of booking "
        f"{booking_id}.\n\n"
        "Are you sure you want to cancel it? "
        "Please reply yes/no to confirm."
    )

    return state


# ============================================================
# CANCELLATION CONFIRMATION
# ============================================================

def _confirm_pending_cancellation(
    state: AgentState,
) -> AgentState:

    pending = (
        state.get("pending_cancellation")
        or {}
    )

    booking_id = pending.get(
        "booking_id"
    )

    if not booking_id:

        state["confirmation_pending"] = False
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "There is no pending cancellation to confirm."
        )

        return state

    text = state.get(
        "user_message",
        "",
    ).strip().lower()

    positive = {
        "yes",
        "y",
        "yes please",
        "confirm",
        "confirmed",
        "cancel it",
        "go ahead",
        "proceed",
    }

    negative = {
        "no",
        "n",
        "don't",
        "do not",
        "no thanks",
        "keep it",
        "don't cancel",
        "do not cancel",
    }

    if (
        text in positive
        or any(
            phrase in text
            for phrase in (
                "yes cancel",
                "yes, cancel",
                "yes confirm",
                "yes, confirm",
                "confirm cancellation",
                "cancel the booking",
                "go ahead and cancel",
            )
        )
    ):

        state["confirmed"] = True
        state["confirmation_pending"] = False

        state["tool_result"] = None
        state["last_tool_name"] = ""
        state["last_tool_call_id"] = ""
        state["error"] = None

        state["tool_name"] = (
            "cancellation_tool"
        )

        state["tool_input"] = {
            "booking_id": booking_id,
        }

        return state

    if (
        text in negative
        or any(
            phrase in text
            for phrase in (
                "don't cancel",
                "do not cancel",
                "keep the booking",
                "keep my booking",
                "no cancel",
            )
        )
    ):

        state["confirmed"] = False
        state["confirmation_pending"] = False
        state["pending_cancellation"] = None

        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Okay, I did not cancel the booking."
        )

        return state

    state["confirmation_pending"] = True
    state["tool_name"] = ""
    state["tool_input"] = {}

    state["final_answer"] = (
        f"Please reply yes/no to confirm "
        f"cancellation of booking {booking_id}."
    )

    return state


# ============================================================
# RESCHEDULING RESOURCE PARSER
# ============================================================

def _parse_rescheduling_resource_id(
    text: str,
) -> str | None:
    """
    Parse destination resource for rescheduling.

    Examples:
        Move BKG1001 to BC2
        Move BKG1001 to tennis court
        Reschedule to BC2
        Change my booking to tennis court
    """

    lower = text.lower()

    # --------------------------------------------------------
    # Explicit resource ID after "to"
    # --------------------------------------------------------

    match = re.search(
        r"\bto\s+((?!BKG\d+\b)(?!B\d+\b)"
        r"[A-Za-z]{2,4}\d{1,3})\b",
        text,
        re.IGNORECASE,
    )

    if match:
        return match.group(1).upper()

    # --------------------------------------------------------
    # Natural destination after "to"
    # --------------------------------------------------------

    to_match = re.search(
        r"\bto\s+(.+?)(?=\s+(?:tomorrow|today|on|at|for)\b|$)",
        lower,
        re.IGNORECASE,
    )

    if to_match:

        destination = (
            to_match.group(1).strip()
        )

        if (
            "badminton court 1"
            in destination
        ):
            return "BC1"

        if (
            "badminton court 2"
            in destination
        ):
            return "BC2"

        if "badminton court" in destination:
            return "BC1"

        if "tennis court" in destination:
            return "TC1"

        if "football turf" in destination:
            return "FT1"

        if "multipurpose room" in destination:
            return "MR1"

    # --------------------------------------------------------
    # Other explicit patterns
    # --------------------------------------------------------

    patterns = [
        r"\bnew\s+(?:resource|facility|court)\s+"
        r"((?!BKG\d+\b)(?!B\d+\b)[A-Za-z]{2,4}\d{1,3})\b",

        r"\bresource\s+"
        r"((?!BKG\d+\b)(?!B\d+\b)[A-Za-z]{2,4}\d{1,3})\b",

        r"\bfacility\s+"
        r"((?!BKG\d+\b)(?!B\d+\b)[A-Za-z]{2,4}\d{1,3})\b",

        r"\bcourt\s+"
        r"((?!BKG\d+\b)(?!B\d+\b)[A-Za-z]{2,4}\d{1,3})\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).upper()

    return None


# ============================================================
# RESCHEDULING DETAIL EXTRACTION
# ============================================================

def _extract_rescheduling_details(
    text: str,
) -> dict[str, Any]:

    return {
        "booking_id": _parse_booking_id(text),
        "new_resource_id": _parse_rescheduling_resource_id(text),
        "new_booking_date": _parse_booking_date(text),
        "new_start_time": _parse_start_time(text),
        "new_duration_minutes": _parse_duration_minutes(text),
    }


# ============================================================
# MERGE RESCHEDULING DETAILS
# ============================================================

def _merge_rescheduling_details(
    existing: dict[str, Any] | None,
    new_details: dict[str, Any],
) -> dict[str, Any]:

    merged = dict(existing or {})

    for key, value in new_details.items():

        if value not in (None, ""):
            merged[key] = value

    return merged


# ============================================================
# MISSING RESCHEDULING FIELDS
# ============================================================

def _missing_rescheduling_fields(
    details: dict[str, Any],
) -> list[str]:

    labels = {
        "booking_id": "booking ID",
        "new_resource_id": "new resource/court ID",
        "new_booking_date": "new booking date",
        "new_start_time": "new start time",
        "new_duration_minutes": "new duration",
    }

    return [
        label
        for key, label in labels.items()
        if details.get(key) in (None, "")
    ]


# ============================================================
# RESCHEDULING SUMMARY
# ============================================================

def _build_rescheduling_summary(
    details: dict[str, Any],
) -> str:

    return (
        "Please confirm this rescheduling:\n"
        f"- Booking ID: {details.get('booking_id')}\n"
        f"- New facility: {details.get('new_resource_id')}\n"
        f"- New date: {details.get('new_booking_date')}\n"
        f"- New start time: {details.get('new_start_time')}\n"
        f"- New duration: "
        f"{details.get('new_duration_minutes')} minutes\n\n"
        "Please reply yes/no to confirm."
    )


# ============================================================
# RESCHEDULING REQUEST
# ============================================================

def _handle_rescheduling_request(
    state: AgentState,
) -> AgentState:

    user_message = state.get(
        "user_message",
        "",
    )

    extracted = _extract_rescheduling_details(
        user_message
    )

    existing = (
        state.get("pending_rescheduling")
        or {}
    )

    details = _merge_rescheduling_details(
        existing,
        extracted,
    )

    state["intent"] = "rescheduling"
    state["pending_rescheduling"] = details

    missing = _missing_rescheduling_fields(
        details
    )

    if missing:

        state["tool_name"] = ""
        state["tool_input"] = {}
        state["confirmation_pending"] = False

        state["final_answer"] = (
            "I still need: "
            + ", ".join(missing)
            + "."
        )

        return state

    state["confirmation_pending"] = True
    state["confirmed"] = False

    state["tool_name"] = ""
    state["tool_input"] = {}

    state["final_answer"] = (
        _build_rescheduling_summary(
            details
        )
    )

    return state


# ============================================================
# RESCHEDULING CONFIRMATION
# ============================================================

def _confirm_pending_rescheduling(
    state: AgentState,
) -> AgentState:

    pending = (
        state.get("pending_rescheduling")
        or {}
    )

    if not pending:

        state["confirmation_pending"] = False
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "There is no pending rescheduling request to confirm."
        )

        return state

    text = state.get(
        "user_message",
        "",
    ).strip().lower()

    positive = {
        "yes",
        "y",
        "yes please",
        "confirm",
        "confirmed",
        "go ahead",
        "proceed",
        "reschedule it",
    }

    negative = {
        "no",
        "n",
        "don't",
        "do not",
        "no thanks",
        "keep it",
        "don't reschedule",
        "do not reschedule",
    }

    if (
        text in positive
        or any(
            phrase in text
            for phrase in (
                "yes reschedule",
                "yes, reschedule",
                "confirm rescheduling",
                "go ahead and reschedule",
                "reschedule it",
            )
        )
    ):

        state["confirmed"] = True
        state["confirmation_pending"] = False

        state["tool_result"] = None
        state["last_tool_name"] = ""
        state["last_tool_call_id"] = ""
        state["error"] = None

        state["tool_name"] = (
            "rescheduling_tool"
        )

        state["tool_input"] = {
            "booking_id": pending["booking_id"],
            "new_resource_id": pending["new_resource_id"],
            "new_booking_date": pending["new_booking_date"],
            "new_start_time": pending["new_start_time"],
            "new_duration_minutes": pending[
                "new_duration_minutes"
            ],
        }

        return state

    if (
        text in negative
        or any(
            phrase in text
            for phrase in (
                "don't reschedule",
                "do not reschedule",
                "keep my booking",
                "keep the booking",
                "no reschedule",
            )
        )
    ):

        state["confirmed"] = False
        state["confirmation_pending"] = False
        state["pending_rescheduling"] = None

        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "Okay, I did not reschedule the booking."
        )

        return state

    state["confirmation_pending"] = True
    state["tool_name"] = ""
    state["tool_input"] = {}

    state["final_answer"] = (
        _build_rescheduling_summary(
            pending
        )
    )

    return state


# ============================================================
# INTENT DETECTION
# ============================================================

def _detect_intent(
    text: str,
) -> str:

    lower = text.lower().strip()

    # ========================================================
    # RESCHEDULING
    # IMPORTANT: BEFORE BOOKING/POLICY
    # ========================================================

    reschedule_patterns = [
        r"\bmove\s+(?:booking\s+)?(?:bkg|b)\d+\b",
        r"\bmove\s+my\s+booking\b",
        r"\bmove\s+the\s+booking\b",
        r"\breschedule\b",
        r"\brescheduling\b",
        r"\bchange\s+my\s+booking\b",
        r"\bchange\s+the\s+booking\b",
        r"\bchange\s+booking\b",
    ]

    if any(
        re.search(
            pattern,
            lower,
            re.IGNORECASE,
        )
        for pattern in reschedule_patterns
    ):
        return "rescheduling"

    # ========================================================
    # CANCELLATION
    # ========================================================

    cancellation_phrases = [
        "cancel my booking",
        "cancel booking",
        "cancel the booking",
        "cancel my reservation",
        "cancel reservation",
    ]

    if any(
        phrase in lower
        for phrase in cancellation_phrases
    ):
        return "cancellation"

    # ========================================================
    # GENERAL EQUIPMENT RESERVATION QUESTION
    # ========================================================

    equipment_policy_phrases = [
        "can i reserve equipment",
        "reserve equipment with my booking",
        "reserve equipment during booking",
        "can equipment be reserved",
        "equipment with my booking",
    ]

    if any(
        phrase in lower
        for phrase in equipment_policy_phrases
    ):
        return "policy"

    # ========================================================
    # POLICY
    # ========================================================

    policy_phrases = [
        "cancellation policy",
        "cancel policy",
        "refund policy",
        "refund",
        "reschedule policy",
        "rescheduling policy",
        "membership",
        "member discount",
        "membership benefits",
        "opening hours",
        "open time",
        "closing time",
        "payment policy",
        "payment methods",
        "equipment policy",
        "rental policy",
        "no show",
        "no-show",
        "late cancellation",
        "holiday closure",
        "holiday closures",
        "non-marking shoes",
        "outside food",
        "10-minute buffer",
    ]

    if any(
        phrase in lower
        for phrase in policy_phrases
    ):
        return "policy"

    # ========================================================
    # BOOKING
    # ========================================================

    booking_phrases = [
        "book ",
        "booked",
        "booking",
        "reserve ",
        "reservation",
    ]

    if any(
        phrase in lower
        for phrase in booking_phrases
    ):
        return "booking"

    # ========================================================
    # RESOURCES
    # ========================================================

    resource_listing_phrases = [
        "what sports facilities",
        "what facilities",
        "which facilities",
        "available facilities",
        "list facilities",
        "sports facilities do you have",
        "facilities do you have",
        "what courts do you have",
        "which courts do you have",
        "what sports do you have",
        "which sports do you have",
    ]

    if any(
        phrase in lower
        for phrase in resource_listing_phrases
    ):
        return "resources"

    # ========================================================
    # AVAILABILITY
    # ========================================================

    availability_phrases = [
        "available",
        "availability",
        "is free",
        "free at",
        "free on",
        "is open at",
        "can i use",
        "new slot",
    ]

    if any(
        phrase in lower
        for phrase in availability_phrases
    ):
        return "availability"

    # ========================================================
    # PRICING
    # ========================================================

    pricing_phrases = [
        "price",
        "pricing",
        "cost",
        "how much",
        "rate",
        "fee",
        "charge",
    ]

    if any(
        phrase in lower
        for phrase in pricing_phrases
    ):
        return "pricing"

    # ========================================================
    # EQUIPMENT
    # ========================================================

    equipment_phrases = [
        "racket",
        "racquet",
        "shuttlecock",
        "equipment",
        "rental",
        "tennis ball",
        "tennis balls",
    ]

    if any(
        phrase in lower
        for phrase in equipment_phrases
    ):
        return "equipment"

    # ========================================================
    # CUSTOMER
    # ========================================================

    customer_phrases = [
        "customer details",
        "customer information",
        "my customer details",
        "find customer",
        "customer lookup",
    ]

    if any(
        phrase in lower
        for phrase in customer_phrases
    ):
        return "customer"

    return "policy"


# ============================================================
# AGENT NODE
# ============================================================

def agent_node(
    state: AgentState,
) -> AgentState:

    _reset_transient_tool_state(state)

    user_message = state.get(
        "user_message",
        "",
    )

    # ========================================================
    # 1. CONFIRMATION WORKFLOW
    # ========================================================

    if state.get("confirmation_pending"):

        if state.get("pending_cancellation"):
            state["intent"] = "cancellation"

            return _confirm_pending_cancellation(
                state
            )

        if state.get("pending_rescheduling"):
            state["intent"] = "rescheduling"

            return _confirm_pending_rescheduling(
                state
            )

        if state.get("pending_booking"):
            state["intent"] = "booking"

            return _confirm_pending_booking(
                state
            )

        state["confirmation_pending"] = False
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            "There is no pending action to confirm."
        )

        return state

    # ========================================================
    # 2. CONTINUE PENDING BOOKING
    # ========================================================

    if state.get("pending_booking"):

        pending = (
            state.get("pending_booking")
            or {}
        )

        extracted = _extract_booking_details(
            user_message
        )

        updated = _merge_booking_details(
            pending,
            extracted,
        )

        state["intent"] = "booking"
        state["pending_booking"] = updated

        missing = _missing_booking_fields(
            updated
        )

        if missing:

            state["tool_name"] = ""
            state["tool_input"] = {}
            state["confirmation_pending"] = False

            state["final_answer"] = (
                "I still need: "
                + ", ".join(missing)
                + "."
            )

            return state

        state["tool_name"] = (
            "availability_tool"
        )

        state["tool_input"] = {
            "resource_id": updated["resource_id"],
            "booking_date": updated["booking_date"],
            "start_time": updated["start_time"],
            "duration_minutes": updated[
                "duration_minutes"
            ],
        }

        state["confirmation_pending"] = False

        return state

    # ========================================================
    # 3. CONTINUE PENDING RESCHEDULING
    # ========================================================

    if state.get("pending_rescheduling"):

        pending = (
            state.get("pending_rescheduling")
            or {}
        )

        extracted = _extract_rescheduling_details(
            user_message
        )

        updated = _merge_rescheduling_details(
            pending,
            extracted,
        )

        state["intent"] = "rescheduling"
        state["pending_rescheduling"] = updated

        missing = _missing_rescheduling_fields(
            updated
        )

        if missing:

            state["tool_name"] = ""
            state["tool_input"] = {}
            state["confirmation_pending"] = False

            state["final_answer"] = (
                "I still need: "
                + ", ".join(missing)
                + "."
            )

            return state

        state["confirmation_pending"] = True
        state["confirmed"] = False
        state["tool_name"] = ""
        state["tool_input"] = {}

        state["final_answer"] = (
            _build_rescheduling_summary(
                updated
            )
        )

        return state

    # ========================================================
    # 4. CONTINUE PENDING AVAILABILITY
    # ========================================================

    if state.get("pending_availability"):

        pending = (
            state.get("pending_availability")
            or {}
        )

        extracted_resource = _parse_resource_id(
            user_message
        )

        extracted_date = _parse_booking_date(
            user_message
        )

        extracted_time = _parse_start_time(
            user_message
        )

        extracted_duration = (
            _parse_duration_minutes(
                user_message
            )
        )

        updated = dict(pending)

        if extracted_resource:
            updated["resource_id"] = (
                extracted_resource
            )

        if extracted_date:
            updated["booking_date"] = (
                extracted_date
            )

        if extracted_time:
            updated["start_time"] = (
                extracted_time
            )

        if extracted_duration:
            updated["duration_minutes"] = (
                extracted_duration
            )

        state["pending_availability"] = updated
        state["intent"] = "availability"

        missing = []

        if not updated.get("resource_id"):
            missing.append(
                "resource/court ID"
            )

        if not updated.get("booking_date"):
            missing.append(
                "booking date"
            )

        if not updated.get("start_time"):
            missing.append(
                "start time"
            )

        if not updated.get("duration_minutes"):
            missing.append(
                "duration"
            )

        if missing:

            state["tool_name"] = ""
            state["tool_input"] = {}

            state["final_answer"] = (
                "I still need: "
                + ", ".join(missing)
                + "."
            )

            return state

        state["tool_name"] = (
            "availability_tool"
        )

        state["tool_input"] = {
            "resource_id": updated["resource_id"],
            "booking_date": updated["booking_date"],
            "start_time": updated["start_time"],
            "duration_minutes": updated[
                "duration_minutes"
            ],
        }

        state["pending_availability"] = None

        return state

    # ========================================================
    # NORMAL INTENT DETECTION
    # ========================================================

    intent = _detect_intent(
        user_message,
    )

    state["intent"] = intent

    # ========================================================
    # BOOKING
    # ========================================================

    if intent == "booking":

        return _handle_booking_request(
            state
        )

    # ========================================================
    # AVAILABILITY
    # ========================================================

    if intent == "availability":

        resource_id = _parse_resource_id(
            user_message
        )

        booking_date = _parse_booking_date(
            user_message
        )

        start_time = _parse_start_time(
            user_message
        )

        duration_minutes = (
            _parse_duration_minutes(
                user_message
            )
        )

        pending = (
            state.get("pending_availability")
            or {}
        )

        if resource_id:
            pending["resource_id"] = (
                resource_id
            )

        if booking_date:
            pending["booking_date"] = (
                booking_date
            )

        if start_time:
            pending["start_time"] = (
                start_time
            )

        if duration_minutes:
            pending["duration_minutes"] = (
                duration_minutes
            )

        state["pending_availability"] = pending

        missing = []

        if not pending.get("resource_id"):
            missing.append(
                "resource/court ID"
            )

        if not pending.get("booking_date"):
            missing.append(
                "booking date"
            )

        if not pending.get("start_time"):
            missing.append(
                "start time"
            )

        if not pending.get("duration_minutes"):
            missing.append(
                "duration"
            )

        if missing:

            state["tool_name"] = ""
            state["tool_input"] = {}

            state["final_answer"] = (
                "I still need: "
                + ", ".join(missing)
                + "."
            )

            return state

        state["tool_name"] = (
            "availability_tool"
        )

        state["tool_input"] = {
            "resource_id": pending[
                "resource_id"
            ],
            "booking_date": pending[
                "booking_date"
            ],
            "start_time": pending[
                "start_time"
            ],
            "duration_minutes": pending[
                "duration_minutes"
            ],
        }

        state["pending_availability"] = None

        return state

    # ========================================================
    # PRICING
    # ========================================================

    if intent == "pricing":

        return _handle_pricing_question(
            state
        )

    # ========================================================
    # EQUIPMENT
    # ========================================================

    if intent == "equipment":

        return _handle_equipment_question(
            state
        )

    # ========================================================
    # RESOURCES
    # ========================================================

    if intent == "resources":

        return _handle_resources_request(
            state
        )

    # ========================================================
    # POLICY
    # ========================================================

    if intent == "policy":

        state["tool_name"] = "policy_tool"

        state["tool_input"] = {
            "query": user_message,
        }

        return state

    # ========================================================
    # CANCELLATION
    # ========================================================

    if intent == "cancellation":

        return _handle_cancellation_request(
            state
        )

    # ========================================================
    # RESCHEDULING
    # ========================================================

    if intent == "rescheduling":

        return _handle_rescheduling_request(
            state
        )

    # ========================================================
    # CUSTOMER
    # ========================================================

    if intent == "customer":

        phone = _parse_phone(
            user_message
        )

        if not phone:

            state["tool_name"] = ""
            state["tool_input"] = {}

            state["final_answer"] = (
                "Please provide the customer's "
                "phone number."
            )

            return state

        state["tool_name"] = (
            "customer_tool"
        )

        state["tool_input"] = {
            "phone": phone,
        }

        return state

    # ========================================================
    # FALLBACK
    # ========================================================

    state["tool_name"] = "policy_tool"

    state["tool_input"] = {
        "query": user_message,
    }

    return state


# ============================================================
# RESOURCE PRICE FORMATTER
# ============================================================

def _format_resource_price_result(
    result: Any,
    resource_id: str,
    duration_minutes: int = 60,
) -> str:

    resources = result

    if isinstance(resources, str):

        try:
            resources = json.loads(
                resources
            )

        except json.JSONDecodeError:

            return (
                f"Pricing information for "
                f"{resource_id} was not found "
                "in the SportMate knowledge base."
            )

    if isinstance(resources, dict):

        if "resources" in resources:
            resources = resources["resources"]
        else:
            resources = [resources]

    if not isinstance(resources, list):

        return (
            f"Pricing information for "
            f"{resource_id} was not found "
            "in the SportMate knowledge base."
        )

    target = None

    for resource in resources:

        if not isinstance(resource, dict):
            continue

        current_id = str(
            resource.get(
                "resource_id",
                "",
            )
        ).upper()

        if current_id == resource_id.upper():

            target = resource
            break

    if target is None:

        return (
            f"Pricing information for "
            f"{resource_id} was not found "
            "in the SportMate knowledge base."
        )

    hourly_rate = target.get(
        "hourly_rate"
    )

    if hourly_rate is None:

        return (
            f"Pricing information for "
            f"{resource_id} was not found "
            "in the SportMate knowledge base."
        )

    hourly_rate = float(
        hourly_rate
    )

    if duration_minutes == 60:

        return (
            f"{resource_id.upper()} costs "
            f"₹{hourly_rate:.0f} per hour."
        )

    total = (
        hourly_rate
        * (duration_minutes / 60)
    )

    return (
        f"{resource_id.upper()} costs "
        f"₹{total:.2f} for "
        f"{duration_minutes} minutes "
        "at the standard hourly rate."
    )


# ============================================================
# TOOL EXECUTION NODE
# ============================================================

def tool_execution_node(
    state: AgentState,
) -> AgentState:

    tool_name = state.get(
        "tool_name"
    )

    if not tool_name:
        return state

    tool = TOOL_MAP.get(
        tool_name
    )

    if tool is None:

        state["error"] = (
            f"Unknown tool: {tool_name}"
        )

        state["final_answer"] = (
            "Sorry, I could not execute "
            "the requested action."
        )

        state["tool_name"] = ""

        return state

    tool_input = state.get(
        "tool_input",
        {},
    )

    try:

        result = tool.invoke(
            tool_input
        )

        state["tool_result"] = result
        state["last_tool_name"] = tool_name
        state["last_tool_call_id"] = ""

    except Exception as exc:

        state["error"] = str(exc)

        state["final_answer"] = (
            "Sorry, something went wrong.\n"
            f"Error: {exc}"
        )

        state["tool_name"] = ""

        return state

    # ========================================================
    # AVAILABILITY RESULT
    # ========================================================

    if tool_name == "availability_tool":

        state["final_answer"] = (
            _format_availability_result(
                result
            )
        )

        is_booking_workflow = (
            state.get("intent") == "booking"
            and bool(
                state.get(
                    "pending_booking"
                )
            )
        )

        if not is_booking_workflow:

            state["tool_name"] = ""

            return state

        if (
            isinstance(result, dict)
            and result.get("available") is True
        ):

            pending = (
                state.get(
                    "pending_booking"
                )
                or {}
            )

            pricing_input = {
                "resource_id": pending.get(
                    "resource_id"
                ),
                "booking_date": pending.get(
                    "booking_date"
                ),
                "start_time": pending.get(
                    "start_time"
                ),
                "duration_minutes": pending.get(
                    "duration_minutes"
                ),
                "is_member": False,
            }

            required = [
                "resource_id",
                "booking_date",
                "start_time",
                "duration_minutes",
            ]

            if any(
                pricing_input.get(field)
                in (None, "")
                for field in required
            ):

                state["tool_name"] = ""

                state["final_answer"] = (
                    "I couldn't calculate the "
                    "booking price because some "
                    "booking details are missing."
                )

                return state

            state["tool_name"] = (
                "pricing_tool"
            )

            state["tool_input"] = pricing_input

            return state

        state["tool_name"] = ""

        return state

    # ========================================================
    # PRICING RESULT
    # ========================================================

    if tool_name == "pricing_tool":

        if isinstance(result, dict):

            if result.get("success") is False:

                state["final_answer"] = (
                    result.get("reason")
                    or "Unable to calculate "
                    "the booking price."
                )

                state["tool_name"] = ""

                return state

            pending = state.get(
                "pending_booking"
            )

            if (
                state.get("intent") == "booking"
                and pending
            ):

                state["pending_booking_price"] = (
                    result
                )

                state["confirmation_pending"] = True
                state["tool_name"] = ""

                resource_id = pending.get(
                    "resource_id"
                )

                booking_date = pending.get(
                    "booking_date"
                )

                start_time = pending.get(
                    "start_time"
                )

                duration = pending.get(
                    "duration_minutes"
                )

                total = result.get(
                    "total_payable"
                )

                if total is not None:

                    state["final_answer"] = (
                        "The requested slot is available.\n\n"
                        f"Booking: {resource_id}\n"
                        f"Date: {booking_date}\n"
                        f"Time: {start_time}\n"
                        f"Duration: {duration} minutes\n"
                        f"Total payable: ₹{float(total):.2f}\n\n"
                        "Please reply yes/no to confirm."
                    )

                else:

                    state["final_answer"] = (
                        _format_tool_result(
                            result
                        )
                        + "\n\n"
                        "Please reply yes/no to confirm."
                    )

                return state

        state["final_answer"] = (
            _format_tool_result(
                result
            )
        )

        state["tool_name"] = ""

        return state

    # ========================================================
    # EQUIPMENT RENTAL RESULT
    # ========================================================

    if tool_name == "equipment_rental_tool":

        if isinstance(result, dict):

            if result.get("success") is False:

                state["final_answer"] = (
                    result.get("reason")
                    or (
                        "Unable to calculate "
                        "equipment rental cost."
                    )
                )

                state["tool_name"] = ""

                return state

            items = result.get(
                "items",
                [],
            )

            rental_total = result.get(
                "rental_total",
                0.0,
            )

            refundable_deposit = result.get(
                "refundable_deposit",
                0.0,
            )

            total_payable = result.get(
                "total_payable",
                rental_total,
            )

            equipment_lines = []

            for item in items:

                if not isinstance(item, dict):
                    continue

                equipment_name = item.get(
                    "equipment",
                    "Equipment",
                )

                quantity = item.get(
                    "quantity",
                    1,
                )

                unit_price = item.get(
                    "unit_price",
                    0.0,
                )

                equipment_lines.append(
                    f"- {equipment_name}: "
                    f"{quantity} × "
                    f"₹{float(unit_price):.2f}"
                )

            if equipment_lines:

                answer = (
                    "Equipment rental:\n"
                    + "\n".join(
                        equipment_lines
                    )
                    + "\n\n"
                    f"Rental total: "
                    f"₹{float(rental_total):.2f}."
                )

            else:

                answer = (
                    "Equipment rental cost is "
                    f"₹{float(rental_total):.2f}."
                )

            if refundable_deposit:

                answer += (
                    " Refundable deposit: "
                    f"₹{float(refundable_deposit):.2f}."
                )

            if (
                refundable_deposit
                and total_payable is not None
            ):

                answer += (
                    " Total payable including "
                    "deposit: "
                    f"₹{float(total_payable):.2f}."
                )

            state["final_answer"] = answer

        else:

            state["final_answer"] = (
                _format_tool_result(
                    result
                )
            )

        state["tool_name"] = ""

        return state

    # ========================================================
    # RESOURCES RESULT
    # ========================================================

    if tool_name == "resources_tool":

        entities = state.get(
            "entities",
            {},
        )

        pricing_resource_id = entities.get(
            "pricing_resource_id"
        )

        if (
            state.get("intent") == "pricing"
            and pricing_resource_id
        ):

            duration = entities.get(
                "pricing_duration_minutes",
                60,
            )

            state["final_answer"] = (
                _format_resource_price_result(
                    result,
                    pricing_resource_id,
                    duration,
                )
            )

        else:

            state["final_answer"] = (
                _format_tool_result(
                    result
                )
            )

        state["tool_name"] = ""

        return state

    # ========================================================
    # POLICY RESULT
    # ========================================================

    if tool_name == "policy_tool":

        state["final_answer"] = (
            _format_policy_result(
                result
            )
        )

        state["tool_name"] = ""

        return state

    # ========================================================
    # CUSTOMER RESULT
    # ========================================================

    if tool_name == "customer_tool":

        state["final_answer"] = (
            _format_tool_result(
                result
            )
        )

        state["tool_name"] = ""

        return state

    # ========================================================
    # EQUIPMENT CATALOG RESULT
    # ========================================================

    if tool_name == "equipment_catalog_tool":

        state["final_answer"] = (
            _format_tool_result(
                result
            )
        )

        state["tool_name"] = ""

        return state

    # ========================================================
    # BOOKING RESULT
    # ========================================================

    if tool_name == "booking_tool":

        if isinstance(result, dict):

            if result.get("success") is True:

                booking_id = (
                    result.get("booking_id")
                    or result.get("id")
                )

                if booking_id:

                    state["final_answer"] = (
                        "Booking created successfully.\n"
                        f"Booking ID: {booking_id}"
                    )

                else:

                    state["final_answer"] = (
                        result.get("message")
                        or "Booking created successfully."
                    )

                state["pending_booking"] = None
                state["pending_booking_price"] = None
                state["confirmation_pending"] = False
                state["confirmed"] = True

            else:

                state["final_answer"] = (
                    result.get("reason")
                    or result.get("message")
                    or "The booking could not be created."
                )

        else:

            state["final_answer"] = (
                _format_tool_result(
                    result
                )
            )

        state["tool_name"] = ""

        return state

    # ========================================================
    # CANCELLATION RESULT
    # ========================================================

    if tool_name == "cancellation_tool":

        if isinstance(result, dict):

            if result.get("success") is True:

                booking_id = (
                    result.get("booking_id")
                    or result.get("id")
                )

                if booking_id:

                    state["final_answer"] = (
                        f"Booking {booking_id} "
                        "was cancelled successfully."
                    )

                else:

                    state["final_answer"] = (
                        result.get("message")
                        or "The booking was cancelled successfully."
                    )

            else:

                state["final_answer"] = (
                    result.get("reason")
                    or result.get("message")
                    or "The booking could not be cancelled."
                )

        else:

            state["final_answer"] = (
                _format_tool_result(
                    result
                )
            )

        state["tool_name"] = ""
        state["confirmation_pending"] = False
        state["pending_cancellation"] = None
        state["confirmed"] = False

        return state

    # ========================================================
    # RESCHEDULING RESULT
    # ========================================================

    if tool_name == "rescheduling_tool":

        if isinstance(result, dict):

            if result.get("success") is True:

                booking_id = (
                    result.get("booking_id")
                    or result.get("id")
                )

                if booking_id:

                    state["final_answer"] = (
                        f"Booking {booking_id} "
                        "was rescheduled successfully."
                    )

                else:

                    state["final_answer"] = (
                        result.get("message")
                        or "The booking was rescheduled successfully."
                    )

                state["pending_rescheduling"] = None
                state["confirmed"] = True

            else:

                state["final_answer"] = (
                    result.get("reason")
                    or result.get("message")
                    or "The booking could not be rescheduled."
                )

        else:

            state["final_answer"] = (
                _format_tool_result(
                    result
                )
            )

        state["tool_name"] = ""
        state["confirmation_pending"] = False

        return state

    # ========================================================
    # FALLBACK
    # ========================================================

    state["final_answer"] = (
        _format_tool_result(
            result
        )
    )

    state["tool_name"] = ""

    return state