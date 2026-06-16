# Therapist Sessions — Late Session Warning + Auto-Recording Fix + Calendar Merge

## Overview

Three-block improvement to the therapist session experience in EduSync AI:

1. **Late Session Warning** — When a therapist logs in and a session's start time has already passed (within a 10-minute grace window), show a modal asking whether to start recording or mark as late.
2. **Fix Auto-Recording** — Debug and fix the RecordingService auto-polling so it reliably detects and starts recording active sessions.
3. **Unify Calendar + My Sessions** — Merge the two separate therapist pages into one view with a List/Calendar tab toggle.

---

## Block 1: Late Session Warning

### Trigger
- Therapist logs in (or page refreshes) while authenticated as `terapista`
- `RecordingService.checkSessions()` runs (every 30s or immediately)
- Finds a session where `now - start_time` is between 0 and 10 minutes
- Session status is `scheduled` (not yet `in_progress`, not already being recorded)

### Flow
```
RecordingService.checkSessions()
  → GET /api/sessions/current (returns session if within time window)
  → Calculate delay = now - session.start_time
  → If 0 <= delay <= 10min AND status == 'scheduled':
      → Emit on new BehaviorSubject: pendingLateSession$
  → Else if delay > 10min AND status == 'scheduled':
      → Auto-start recording (existing behavior)
```

### UI Component: `LateSessionModal`
- **Not a new component** — reuse existing `app-alert-modal` or build a simple standalone modal inside `TherapistSessions`
- Shows:
  - Icon: `⏰`
  - Title: "¡La sesión ya comenzó!"
  - Patient name
  - Scheduled time (start — end)
  - Delay in minutes
  - Two buttons:
    - `🎤 Iniciar grabación` → calls `RecordingService.autoStart()`
    - `⚠ Marcar como tarde` → closes modal, no recording, optionally logs `late_start = true` to session

### Backend
- `GET /api/sessions/current` returns `delay_minutes` field (calculated from `now - start_time`)
- No new backend endpoints needed

### Data Flow
```
app.ts
  → RecordingService.iniciarPolleo()
    → checkSessions() every 30s
      → GET /api/sessions/current
        → if delay 0-10min + scheduled:
            → pendingLateSession$.next(session)
                → TherapistSessions subscribes
                  → shows LateSessionModal
                    → user clicks:
                      "Iniciar grabación" → autoStart()
                      "Marcar como tarde" → pendingLateSession$.next(null), no recording
```

---

## Block 2: Fix Auto-Recording

### Root Cause Analysis

**Timezone bug in `api_current_session()`** (sessions.py:1300):
```python
now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC
```
But `Appointment.start_time` is stored in the database as a naive datetime in local time (America/Lima, UTC-5). The comparison:
```python
Appointment.start_time <= now  # naive local 10:00 <= naive UTC 15:00 → Always True!
```
This means the query is too broad — it can match sessions hours before their actual start time in local time. However, the `end_time >= now` check may compensate partially.

**Fix**: Use timezone-aware comparisons consistently.

```python
from datetime import datetime, timezone
from sqlalchemy import func

now = datetime.now(timezone.utc)
# Convert stored naive local times to UTC for comparison
appt = Appointment.query.filter(
    Appointment.therapist_id == current_user.id,
    func.timezone('UTC', Appointment.start_time) <= now,
    # ...
)
```

Or simpler: store all `start_time`/`end_time` values as UTC in the database and convert on display.

### Additional Debugging

1. **Add console logging** to `RecordingService.checkSessions()` to show what `/api/sessions/current` returns
2. **Add a "🧪 Test Recording" button** in the therapist sessions toolbar that manually calls `checkSessions()` for easy debugging
3. **Log timezone info** in the health check endpoint

### Failsafe: Session Start Warning at Login

Even if auto-recording has edge cases, the `LateSessionModal` (Block 1) ensures the therapist always knows about a session that should be active. This compensates for any polling/recording failures.

---

## Block 3: Unify Calendar + My Sessions (deferred)

### Design
- Single page at `/therapist/sessions`
- Two view modes toggled by tabs:
  - `📋 Lista` — the existing week-picker + timeline + stats (current TherapistSessions)
  - `📅 Calendario` — month grid using CalendarWidget (currently at `/therapist/calendar`)
- Tab state persisted in URL query param: `/therapist/sessions?view=lista|calendario`
- Remove the separate `/therapist/calendar` route

### Implementation approach (when ready)
1. Move CalendarWidget usage from `TherapistCalendarPage` into `TherapistSessions`
2. Add `viewMode` property: `'lista' | 'calendario'`
3. Wrap timeline section and calendar section in `*ngIf` blocks
4. Style tab buttons as pill-shaped toggle
5. Update therapist-routing-module to remove the calendar route

---

## Phasing

| Phase | Block | Effort | Priority |
|-------|-------|--------|----------|
| 1 | Late Session Warning (Block 1) | Small | High |
| 2 | Fix Auto-Recording (Block 2) | Medium | High |
| 3 | Unify Calendar + Sessions (Block 3) | Medium | Low |

Phase 1 and 2 can be done in parallel since they touch different parts of the code.

---

## Files to Modify

### Phase 1 — Late Session Warning
- `edysync/src/app/core/services/recording.service.ts` — add `pendingLateSession$` BehaviorSubject, modify `checkSessions()` to emit on 0-10min delay
- `edysync/src/app/features/therapist/pages/sessions/therapist-sessions.ts` — subscribe to `pendingLateSession$`, show modal
- `edysync/src/app/features/therapist/pages/sessions/therapist-sessions.html` — add modal HTML

### Phase 2 — Fix Auto-Recording
- `app/routes/api/sessions.py` (line 1300) — fix timezone comparison in `api_current_session()`
- `edysync/src/app/core/services/recording.service.ts` — add logging, add test button trigger
- `edysync/src/app/features/therapist/pages/sessions/therapist-sessions.ts` — add "🧪 Test Recording" button handler
- `edysync/src/app/features/therapist/pages/sessions/therapist-sessions.html` — add button

### Phase 3 — Unify Calendar (future)
- `edysync/src/app/features/therapist/therapist-routing-module.ts` — remove calendar route
- `edysync/src/app/features/therapist/pages/sessions/therapist-sessions.ts` — add viewMode, calendar tab
- `edysync/src/app/features/therapist/pages/sessions/therapist-sessions.html` — add tab toggle, calendar section
