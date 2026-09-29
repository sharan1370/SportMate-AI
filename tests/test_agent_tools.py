from src.agent.tools import ALL_TOOLS


def test_all_agent_tools_are_registered():
    tool_names = {tool.name for tool in ALL_TOOLS}

    assert "availability_tool" in tool_names
    assert "booking_tool" in tool_names
    assert "cancellation_tool" in tool_names
    assert "rescheduling_tool" in tool_names
    assert "pricing_tool" in tool_names
    assert "customer_tool" in tool_names
    assert "equipment_catalog_tool" in tool_names
    assert "equipment_rental_tool" in tool_names
    assert "resources_tool" in tool_names


def test_agent_tool_count():
    assert len(ALL_TOOLS) == 10