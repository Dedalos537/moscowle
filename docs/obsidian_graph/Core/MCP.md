# MCP (Model Context Protocol)
The MCP layer allows LLMs to interact with the system as an "operator" rather than just a "reviewer".

## Components
- **`app/routes/mcp_routes.py`**: Exposes `/mcp/chat` and `/mcp/execute`.
- **`app/services/mcp_service.py`**: Manages the AI's "thought" loop and the confirmation gates for write actions.
- **`app/services/tools_registry.py`**: The source of truth for all available tools.

## Execution Flow
LLM $\rightarrow$ Tool Call $\rightarrow$ `execute_tool()` $\rightarrow$ Service Method $\rightarrow$ DB.

Links: [[Services.ToolsRegistry]], [[Routes.MCPRoutes]], [[Core.LLM_Chain]]
