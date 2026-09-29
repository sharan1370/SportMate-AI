from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """
    State carried through the SportMate LangGraph workflow.

    The state persists across user messages so that multi-step
    operations such as booking, cancellation, and rescheduling
    confirmations can be handled deterministically.
    """

    # =========================================================
    # CONVERSATION
    # =========================================================

    user_message: str

    messages: list[dict[str, Any]]

    # =========================================================
    # REQUEST UNDERSTANDING
    # =========================================================

    intent: str

    entities: dict[str, Any]

    # =========================================================
    # TOOL EXECUTION
    # =========================================================

    tool_name: str

    tool_input: dict[str, Any]

    tool_result: dict[str, Any] | None

    last_tool_name: str

    last_tool_call_id: str

    # =========================================================
    # RAG / POLICY CONTEXT
    # =========================================================

    retrieved_context: list[dict[str, Any]]

    # =========================================================
    # CONFIRMATION
    # =========================================================

    confirmation_required: bool

    confirmation_pending: bool

    confirmed: bool

    # =========================================================
    # BOOKING CONFIRMATION
    # =========================================================

    pending_booking: dict[str, Any] | None

    pending_booking_price: dict[str, Any] | None

    # =========================================================
    # CANCELLATION CONFIRMATION
    # =========================================================

    pending_cancellation: dict[str, Any] | None

    # =========================================================
    # RESCHEDULING CONFIRMATION
    # =========================================================

    pending_rescheduling: dict[str, Any] | None

    # Example:
    #
    # {
    #     "booking_id": "BKG1007",
    #     "new_resource_id": "BC2",
    #     "new_booking_date": "2026-09-16",
    #     "new_start_time": "20:00",
    #     "new_duration_minutes": 60
    # }

    # =========================================================
    # MEMBERSHIP / BOOKING CONVERSATION STATE
    # =========================================================

    awaiting_membership: bool

    pending_is_member: bool | None

    # =========================================================
    # FINAL RESPONSE
    # =========================================================

    final_answer: str

    # =========================================================
    # ERROR HANDLING
    # =========================================================

    error: str | None