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
- **Topology**: host `192.168.1.249` + **VM-APP** `192.168.122.10` (gunicorn + bridge WhatsApp) + **VM-DB** `192.168.122.20` (MySQL). El host conserva `cloudflared`, `nginx` (frontend LAN), `socat` (forwarder) y Ollama. Ver `PRPs/006--division-servicios-qemu.md`.
- **Primary Target**: Ubuntu Server (`192.168.1.249`) — la IP por DHCP cambió de `.41`.
- **Deployment Flow**: `git push origin main` $\rightarrow$ `deploy-ubuntu.yml` $\rightarrow$ webhook $\rightarrow$ `scripts/server_deploy.sh` (se ejecuta dentro de VM-APP) $\rightarrow$ `systemctl restart moscowle`.
- **Tunnel**: `api-centrojuanpabloii.online` $\rightarrow$ cloudflared (host) $\rightarrow$ `socat 127.0.0.1:5000` $\rightarrow$ VM-APP `:5000`.
- **Frontends**: LAN `/app/` (nginx del host) y `https://moscowle.centrojuanpabloii.com` (cPanel) apuntan al mismo backend a través del túnel.
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
