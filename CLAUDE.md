# Moscowle IA - Project Guide

## Overview
Moscowle IA is a comprehensive management system for a therapy center, integrated with an AI operational layer (MCP) that allows LLMs to perform administrative and therapeutic tasks.

### Core Architecture
- **Backend**: Flask (Python 3.11+)
- **Database**: SQLAlchemy with read-write routing (PostgreSQL/MySQL)
- **AI Layer**: MCP (Model Context Protocol) implemented as a tool-based API.
- **LLM Chain**: Ollama (Local Gemma 4) $\rightarrow$ Groq $\rightarrow$ GLM $\rightarrow$ Gemini.
- **Frontend**: Angular 20 + Tailwind 4.
- **Deployment**: Ubuntu Server via Cloudflare Tunnel.

## Infrastructure & Deployment
- **Primary Target**: Ubuntu Server (`192.168.1.41`)
- **Deployment Flow**: `git push origin main` $\rightarrow$ (Webhook/Manual) $\rightarrow$ `systemctl restart moscowle`.
- **Tunnel**: Cloudflare Tunnel connects `api-centrojuanpabloii.online` to local port `5000`.
- **Fallbacks**: Docker/Railway (Keep as backup, do not use for primary deploy).

## Development Guidelines
- **Naming**: Match existing snake_case for Python and camelCase for Angular.
- **MCP Tools**: New tools must be registered in `app/services/tools_registry.py` and mapped in `CORE_TOOL_NAMES`.
- **Writing Tools**: All "write" tools (modifying data) must have a confirmation gate in `mcp_service.py` or be added to `SAFE_WRITE_TOOLS`.
- **LLM Provider**: Default to `ollama` (Gemma 4) for local execution, with circuit-breaking fallbacks.

## Critical Commands
- **Run Local**: `python server_local.py`
- **Test MCP**: Use the `/mcp/tools` endpoint to verify tool visibility.
- **Logs**: Use `get_server_logs` tool or `journalctl -u moscowle -f`.

## Knowledge Graph
The project architecture is mapped in Obsidian format at `docs/obsidian_graph/`.
**AI Instruction**: Before making structural changes, read `docs/obsidian_graph/MAP.md` to understand class dependencies and data flow.
