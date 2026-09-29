from src.agent.prompts import SYSTEM_PROMPT, POLICY_FALLBACK_MESSAGE


def test_system_prompt_exists():
    assert SYSTEM_PROMPT.strip()


def test_prompt_prevents_invented_information():
    assert "NEVER INVENT INFORMATION" in SYSTEM_PROMPT


def test_prompt_requires_booking_confirmation():
    assert "DO NOT create the booking until the user explicitly confirms" in SYSTEM_PROMPT


def test_prompt_requires_cancellation_confirmation():
    assert "DO NOT execute cancellation until the user explicitly confirms" in SYSTEM_PROMPT


def test_prompt_requires_rescheduling_confirmation():
    assert "DO NOT execute the rescheduling until the user explicitly confirms" in SYSTEM_PROMPT


def test_policy_fallback_message():
    assert POLICY_FALLBACK_MESSAGE == (
        "Answer not found in the SportMate knowledge base."
    )