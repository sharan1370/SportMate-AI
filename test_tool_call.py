from src.agent.tools import ALL_TOOLS


print("Registered tools:")
print()

for tool in ALL_TOOLS:
    print(f"Name: {tool.name}")
    print(f"Description: {tool.description}")
    print()