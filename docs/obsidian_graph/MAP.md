# 🗺️ Moscowle IA Knowledge Map

Welcome to the architectural map of Moscowle IA. Use these links to navigate the system's logic.

## 🏗️ Core Architecture
- [[Core.Backend]] - Flask application structure and bootstrap.
- [[Core.MCP]] - The Model Context Protocol implementation.
- [[Core.LLM_Chain]] - Provider chain and fallback logic.

## 📦 Data Models ([[Models]])
- [[Models.User]] - The central User/Patient/Therapist entity.
- [[Models.Appointment]] - Therapy session and scheduling logic.
- [[Models.Contract]] - Financial contracts and installments.
- [[Models.Payment]] - Payment records and evidence.
- [[Models.Sede]] - Physical location management.

## ⚙️ Business Logic ([[Services]])
- [[Services.ToolsRegistry]] - The bridge between AI and Backend.
- [[Services.AppointmentService]] - Session management logic.
- [[Services.ContractService]] - Financial lifecycle management.
- [[Services.PaymentService]] - Payment processing.
- [[Services.MCPService]] - AI loop and confirmation gates.

## 🛣️ API Layer ([[Routes]])
- [[Routes.MCPRoutes]] - Endpoints for the AI agent.
- [[Routes.AdminRoutes]] - Management panel API.
- [[Routes.ApiRoutes]] - General public/client API.

## 🚀 Deploy ([[DEPLOY_FLOW]])
- [[DEPLOY_FLOW]] - Auto-deploy pipeline (webhook + GitHub Actions + nginx).
- [[Deployments]] - Registro timestamped de cada deploy.

---
**AI Usage**: To understand a feature, start at `MAP.md` $\rightarrow$ find the relevant `Service` $\rightarrow$ check the `Model` it modifies.
