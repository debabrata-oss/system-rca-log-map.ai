from mcp.server.mcpserver import MCPServer

from rca_log_map import audit
from rca_log_map.tools.log_tools import ALL_TOOLS

mcp = MCPServer("rca-log-map")

for _tool_fn in ALL_TOOLS:
    mcp.tool()(_tool_fn)


def main() -> None:
    audit.set_actor("mcp")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
