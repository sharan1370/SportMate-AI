from src.agent.state import AgentState


def test_agent_state_can_store_user_message():
    state: AgentState = {
        "user_message": "Is badminton court available tomorrow?"
    }

    assert state["user_message"] == "Is badminton court available tomorrow?"


def test_agent_state_can_store_tool_result():
    state: AgentState = {
        "tool_name": "check_availability",
        "tool_result": {
            "available": True,
            "resource_id": "BC1",
        },
    }

    assert state["tool_name"] == "check_availability"
    assert state["tool_result"]["available"] is True