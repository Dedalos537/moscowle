# Plan 09: Chasqui Bot Configuration — Centro de Operaciones

## Objective
Add full Chasqui bot configuration to the admin panel's Telegram tab: bot persona, custom system prompt, FAQ knowledge base, webhook management — all editable from the UI without touching `.env` or code.

## Current State
- Bot persona hardcoded: `BOT_NAME = 'Chasqui'`, `BOT_EMOJI = '🦜'`, identity response hardcoded
- System prompts hardcoded in `mcp_service.py` `SYSTEM_PROMPTS` dict
- No FAQ model or endpoints
- No webhook management UI
- Telegram tab only handles device linking

## Architecture Decision
**Extract patterns from Chasqui, implement within existing Flask architecture.**
Chasqui is a standalone stack (FastAPI + pgvector), not a library. We adapt its approach:
- DB-editable `agent_config` singleton (like Chasqui's `admin/config`)
- FAQ table with pgvector embeddings (like Chasqui's `admin/modules/faq`)
- Prompt editor (like Chasqui's `/prompt` page)

---

## Phase 1: Backend — DB Models + Config Endpoints

### 1a. New models
**File:** `app/models/telegram_config.py` (NEW)
- `TelegramConfig` — singleton row: `bot_name`, `bot_emoji`, `persona_message`, `system_prompt`, `webhook_url`, `webhook_secret`
- `TelegramFaq` — FAQ entries: `question`, `answer`, `category`, `embedding` (pgvector), `created_at`, `updated_at`

### 1b. Migration
**File:** `migrations/` or inline SQL
- Create `telegram_config` table (1 row, seeded with defaults)
- Create `telegram_faq` table with vector column

### 1c. API endpoints
**File:** `app/routes/api/telegram_config.py` (NEW blueprint)
| Endpoint | Method | Purpose |
|---|---|---|
| `/api/telegram/config` | GET | Get bot config (token masked) |
| `/api/telegram/config` | PUT | Update bot persona/name/emoji/prompt |
| `/api/telegram/webhook/status` | GET | Call Telegram `getWebhookInfo` |
| `/api/telegram/webhook/setup` | POST | Call Telegram `setWebhook` |
| `/api/telegram/webhook` | DELETE | Remove webhook |
| `/api/telegram/faq` | GET | List FAQ entries |
| `/api/telegram/faq` | POST | Create FAQ |
| `/api/telegram/faq/:id` | PUT | Update FAQ |
| `/api/telegram/faq/:id` | DELETE | Delete FAQ |
| `/api/telegram/faq/re-embed` | POST | Re-embed all FAQs |
| `/api/telegram/test` | POST | Send test message to a chat_id |

### 1d. Register blueprint
**File:** `app/__init__.py` — register new blueprint

**Verification:** Hit each endpoint with curl, confirm JSON responses.

---

## Phase 2: Backend — Bot Service Integration

### 2a. Load config from DB
**File:** `app/services/telegram_bot_service.py`
- Replace hardcoded `BOT_NAME`, `BOT_EMOJI` with DB lookup
- Load `system_prompt` from DB (fallback to hardcoded `SYSTEM_PROMPTS`)
- Load `persona_message` for identity response

### 2b. FAQ RAG injection
**File:** `app/services/telegram_bot_service.py`
- Before calling MCP, query FAQ embeddings for top-3 similar entries
- Inject as context: "Base de conocimiento relevante:\n{faq_results}"
- Use pgvector cosine similarity (`<=>` operator)

### 2c. MCP service modification
**File:** `app/services/mcp_service.py`
- Accept optional `faq_context` parameter in `process_message()`
- Append FAQ context to system prompt if provided

**Verification:** Send Telegram message, verify bot uses DB prompt and FAQ context.

---

## Phase 3: Frontend — Expanded Telegram Tab

### 3a. Admin service additions
**File:** `app/core/services/admin.service.ts`
- Add methods for all new endpoints (config CRUD, FAQ CRUD, webhook management)

### 3b. New component sections in visor-funcionamiento
**File:** `visor-funcionamiento.html` + `.ts`

Add sub-sections to the Telegram tab:
1. **Estado del Bot** — webhook status indicator, bot name/emoji display
2. **Configuración del Bot** — form: bot name, emoji, persona message
3. **Prompt del Sistema** — textarea editor for system prompt with save
4. **FAQ / Base de Conocimiento** — table with add/edit/delete rows, re-embed button
5. **Dispositivos Vinculados** — existing linking UI (unchanged)
6. **Webhook** — setup/delete buttons, URL display, status badge

### 3c. Styling
Follow existing card/setting-item patterns from settings page.

**Verification:** Navigate to Centro de Operaciones → Telegram tab, see all sections, edit config, verify persistence.

---

## Phase 4: Integration Testing

1. Edit bot name in UI → send `/start` on Telegram → verify new name
2. Edit system prompt → send message → verify bot behavior changes
3. Add FAQ entry → re-embed → send related question → verify bot uses FAQ
4. Setup webhook → verify status shows "active"
5. Delete webhook → verify status shows "inactive"

---

## Key Files
| File | Action |
|---|---|
| `app/models/telegram_config.py` | CREATE |
| `app/routes/api/telegram_config.py` | CREATE |
| `app/__init__.py` | MODIFY — register blueprint |
| `app/services/telegram_bot_service.py` | MODIFY — load from DB |
| `app/services/mcp_service.py` | MODIFY — accept FAQ context |
| `app/core/services/admin.service.ts` | MODIFY — add API methods |
| `visor-funcionamiento.ts` | MODIFY — add config state |
| `visor-funcionamiento.html` | MODIFY — add UI sections |

## Anti-Patterns
- Don't create a new Angular component — keep everything in visor-funcionamiento (existing pattern)
- Don't use pgvector if not installed — check first, fallback to LIKE search
- Don't expose bot token in API responses — always mask
- Don't modify the hardcoded SYSTEM_PROMPTS dict — use DB override pattern
