from src.agent.tools import ALL_TOOLS


for tool in ALL_TOOLS:
    print("=" * 70)
    print("Tool name:", tool.name)
    print("Tool description:", tool.description)
    print("Tool args schema:")
    print(tool.args)