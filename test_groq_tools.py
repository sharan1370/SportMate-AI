from src.agent.nodes import TOOL_SCHEMAS


print("=" * 70)
print("GROQ TOOL SCHEMAS")
print("=" * 70)


for tool in TOOL_SCHEMAS:
    function = tool["function"]

    print("\nTool:", function["name"])
    print("Description:", function["description"])
    print("Parameters:")

    print(function["parameters"])