from src.agent.graph import build_graph


def initial_state(user_message: str) -> dict:
    return {
        "user_message": user_message,
        "messages": [],
        "intent": "",
        "entities": {},
        "tool_name": "",
        "tool_input": {},
        "tool_result": None,
        "last_tool_name": "",
        "last_tool_call_id": "",
        "retrieved_context": [],
        "confirmation_required": False,
        "confirmation_pending": False,
        "confirmed": False,
        "pending_booking": None,
        "pending_booking_price": None,
        "awaiting_membership": False,
        "pending_is_member": None,
        "final_answer": "",
        "error": None,
    }


def run_agent(user_message: str) -> dict:
    graph = build_graph()

    state = initial_state(user_message)

    return graph.invoke(state)


def test_agent_availability():
    state = run_agent(
        "Is badminton court BC1 available on "
        "2026-09-19 at 7 PM for 1 hour?"
    )

    assert state["final_answer"]
    assert "BC1" in state["final_answer"]
    assert "available" in state["final_answer"].lower()


def test_agent_facility_pricing():
    state = run_agent(
        "How much does BC1 cost for 1 hour?"
    )

    assert state["final_answer"]
    assert "₹300" in state["final_answer"]


def test_agent_equipment_pricing():
    state = run_agent(
        "How much is a badminton racket rental?"
    )

    assert state["final_answer"]
    assert "₹50" in state["final_answer"]
    assert "badminton racket" in state["final_answer"].lower()


def test_agent_resources():
    state = run_agent(
        "What sports facilities are available?"
    )

    answer = state["final_answer"]

    assert answer
    assert "BC1" in answer
    assert "BC2" in answer
    assert "FT1" in answer
    assert "TC1" in answer
    assert "MR1" in answer


def test_agent_cancellation_policy():
    state = run_agent(
        "What is the cancellation policy?"
    )

    answer = state["final_answer"]

    assert answer
    assert "2 hours" in answer
    assert "non-refundable" in answer.lower()


def test_agent_unrelated_question():
    state = run_agent(
        "What is the weather today?"
    )

    answer = state["final_answer"]

    assert answer
    assert "not found" in answer.lower()


def test_agent_does_not_invent_information():
    state = run_agent(
        "Tell me the price of a swimming pool."
    )

    answer = state["final_answer"]

    assert answer
    assert "not found" in answer.lower()