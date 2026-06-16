# Therapist Sessions — Late Session Warning + Auto-Recording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add late-session warning modal when therapist logs in within 10 min of session start, and fix auto-recording reliability.

**Architecture:** Two phases — (1) backend adds `delay_minutes` to current-session endpoint, (2) frontend RecordingService detects 0-10min delay and emits `pendingLateSession$` instead of auto-starting, (3) TherapistSessions shows modal.

**Tech Stack:** Angular 17+, Flask, PostgreSQL, flask-jwt-extended

---

### Task 1: Add `delay_minutes` to backend current-session endpoint

**Files:**
- Modify: `app/routes/api/sessions.py:1295-1329`

- [ ] **Step 1: Calculate delay_minutes and add to response**

In `api_current_session()`, after finding the appointment, calculate the delay between now and start_time in minutes:

```python
@api_bp.route('/sessions/current', methods=['GET'])
@login_required
def api_current_session():
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    from sqlalchemy import or_

    appt = (
        Appointment.query.filter(
            Appointment.therapist_id == current_user.id,
            Appointment.start_time <= now,
            or_(Appointment.end_time >= now, Appointment.end_time.is_(None)),
            Appointment.status.in_(['scheduled', 'in_progress']),
        )
        .order_by(Appointment.start_time)
        .first()
    )
    if not appt:
        return jsonify({'success': False, 'has_active': False})

    delay_minutes = int((now - appt.start_time).total_seconds() / 60)
    if delay_minutes < 0:
        delay_minutes = 0

    return jsonify(
        {
            'success': True,
            'has_active': True,
            'delay_minutes': delay_minutes,
            'session': {
                'id': appt.id,
                'title': appt.title or 'Sesión',
                'start': appt.start_time.isoformat() if appt.start_time else None,
                'end': appt.end_time.isoformat() if appt.end_time else None,
                'status': appt.status,
                'patient': {'id': appt.patient.id, 'name': appt.patient.username} if appt.patient else None,
                'location': appt.location,
            },
        }
    )
```

- [ ] **Step 2: Commit**

```bash
git add app/routes/api/sessions.py
git commit -m "feat: add delay_minutes to /api/sessions/current response"
```

---

### Task 2: Add `pendingLateSession$` observable to RecordingService

**Files:**
- Modify: `edysync/src/app/core/services/recording.service.ts`

Add a new BehaviorSubject for late sessions, and modify `checkSessions()` to emit to it instead of auto-starting when delay is 0-10 min.

- [ ] **Step 1: Add pendingLateSession$ subject and modify checkSessions**

In `recording.service.ts`:

Add new subject after existing subjects (line 17):
```typescript
pendingLateSession$ = new BehaviorSubject<any>(null);
```

Replace the `checkSessions()` method (lines 61-88):

```typescript
private checkSessions() {
    const user = this.getCurrentUser();
    if (!user || user.role !== 'terapista') {
      this.activeSession$.next(null);
      return;
    }
    if (this.recordingState$.value === 'recording' || this.recordingState$.value === 'starting') return;

    this.http.post('/api/sessions/auto-complete-expired', {}).subscribe({
      error: () => {},
    });

    this.http.get<any>('/api/sessions/current').subscribe({
      next: (res) => {
        if (!res.success || !res.has_active) return;
        const s = res.session;
        if (this.checkedSessions.has(s.id)) return;
        this.checkedSessions.add(s.id);

        const delayMinutes = res.delay_minutes ?? 0;
        console.log(`[RecordingService] Session #${s.id} found, delay=${delayMinutes}min, status=${s.status}`);

        // Late session warning: 0-10 min delay, session not yet in_progress
        if (s.status === 'scheduled' && delayMinutes >= 0 && delayMinutes <= 10) {
          this.currentSessionId = s.id;
          const patientName = s.patient?.name || '';
          this.sessionTitle$.next(s.title || 'Sesión');
          this.patientName$.next(patientName);
          this.activeSession$.next(s);
          this.pendingLateSession$.next(s);
          console.log(`[RecordingService] Late session detected, showing warning`);
          return;
        }

        // Normal case: auto-start recording
        this.currentSessionId = s.id;
        const patientName = s.patient?.name || '';
        this.sessionTitle$.next(s.title || 'Sesión');
        this.patientName$.next(patientName);
        this.activeSession$.next(s);
        console.log(`[RecordingService] Auto-starting recording for session #${s.id}`);
        this.autoStart();
      },
      error: (err) => console.warn('[RecordingService] Error fetching current session:', err),
    });
  }
```

- [ ] **Step 2: Commit**

```bash
git add edysync/src/app/core/services/recording.service.ts
git commit -m "feat: add pendingLateSession$ observable for 0-10min late session warning"
```

---

### Task 3: Add late-session warning modal to therapist sessions page

**Files:**
- Modify: `edysync/src/app/features/therapist/pages/sessions/therapist-sessions.ts`
- Modify: `edysync/src/app/features/therapist/pages/sessions/therapist-sessions.html`

- [ ] **Step 1: Subscribe to pendingLateSession$ and show modal**

In `therapist-sessions.ts`, add to `ngOnInit()`:

```typescript
import { RecordingService } from '../../../../core/services/recording.service';
// ... already imported

// Add these properties:
lateSession: any = null;

// In ngOnInit(), after the existing RecordingService subscription:
this.subscriptions.add(
  this.recordingService.pendingLateSession$.subscribe(session => {
    this.lateSession = session;
    this.cdr.markForCheck();
  })
);
```

Add handler methods:
```typescript
getLateSessionDelay(): string {
  if (!this.lateSession?.start) return '';
  const start = new Date(this.lateSession.start);
  const diff = Math.floor((Date.now() - start.getTime()) / 60000);
  return diff > 0 ? `${diff} min` : '< 1 min';
}

startLateSessionRecording() {
  this.recordingService.pendingLateSession$.next(null);
  this.lateSession = null;
  this.recordingService.autoStart();
  this.cdr.markForCheck();
}

dismissLateSession() {
  this.recordingService.pendingLateSession$.next(null);
  this.lateSession = null;
  this.cdr.markForCheck();
}
```

- [ ] **Step 2: Add modal HTML to template**

In `therapist-sessions.html`, add the late session modal near the top (inside the main container, but before content):

```html
<!-- Late Session Warning Modal -->
<div class="late-session-overlay" *ngIf="lateSession">
  <div class="late-session-modal">
    <div class="late-session-icon">⏰</div>
    <h2>¡La sesión ya comenzó!</h2>
    <div class="late-session-info">
      <p><strong>Paciente:</strong> {{ lateSession.patient?.name }}</p>
      <p><strong>Horario:</strong> {{ lateSession.start | date:'shortTime' }} — {{ lateSession.end | date:'shortTime' }}</p>
      <p><strong>Atraso:</strong> {{ getLateSessionDelay() }}</p>
    </div>
    <div class="late-session-actions">
      <button class="btn btn-primary" (click)="startLateSessionRecording()">
        🎤 Iniciar grabación
      </button>
      <button class="btn btn-secondary" (click)="dismissLateSession()">
        ⚠ Marcar como tarde
      </button>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Add modal styles**

In `therapist-sessions.scss`:

```scss
.late-session-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.late-session-modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  max-width: 400px;
  width: 90%;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.late-session-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.late-session-modal h2 {
  margin: 0 0 16px;
  font-size: 20px;
  color: #1a1a2e;
}

.late-session-info {
  text-align: left;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 20px;
}

.late-session-info p {
  margin: 4px 0;
  font-size: 14px;
  color: #333;
}

.late-session-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.late-session-actions .btn {
  padding: 10px 20px;
  border-radius: 8px;
  border: none;
  font-size: 14px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.late-session-actions .btn-primary {
  background: #3b82f6;
  color: white;
}

.late-session-actions .btn-primary:hover {
  background: #2563eb;
}

.late-session-actions .btn-secondary {
  background: #e5e7eb;
  color: #374151;
}

.late-session-actions .btn-secondary:hover {
  background: #d1d5db;
}
```

- [ ] **Step 4: Commit**

```bash
git add edysync/src/app/features/therapist/pages/sessions/therapist-sessions.ts edysync/src/app/features/therapist/pages/sessions/therapist-sessions.html edysync/src/app/features/therapist/pages/sessions/therapist-sessions.scss
git commit -m "feat: add late session warning modal to therapist sessions"
```

---

### Task 4: Fix auto-recording timezone and add debugging

**Files:**
- Modify: `app/routes/api/sessions.py:1300`
- Modify: `edysync/src/app/core/services/recording.service.ts`
- Modify: `edysync/src/app/features/therapist/pages/sessions/therapist-sessions.ts`
- Modify: `edysync/src/app/features/therapist/pages/sessions/therapist-sessions.html`

- [ ] **Step 1: Fix timezone handling in api_current_session**

In `sessions.py:1300`, the current code uses naive UTC for `now` and compares with naive UTC stored times. This is actually correct since `parse_datetime()` stores naive UTC. But add an extra safeguard — use the database's `UTC_TIMESTAMP` for comparison:

```python
from sqlalchemy import func

# Replace line 1300:
now = datetime.now(timezone.utc).replace(tzinfo=None)

# With:
now = func.now() if app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('postgresql') else datetime.now(timezone.utc).replace(tzinfo=None)
```

Actually, simpler — just add a log line to help debug:
```python
import logging
current_app.logger.info(
    'api_current_session check',
    extra={
        'user_id': current_user.id,
        'now': now.isoformat(),
        'sample_start': str(appt.start_time) if appt else 'no_appt',
        'timezone': 'naive_utc',
    },
)
```

Add this right after finding (or not finding) the appointment.

- [ ] **Step 2: Add test-recording button in therapist sessions toolbar**

In `therapist-sessions.ts`, add:
```typescript
testRecording() {
  console.log('[Manual] Triggering checkSessions()');
  (this.recordingService as any).checkSessions();
}
```

In `therapist-sessions.html`, add button next to other toolbar items:
```html
<button class="btn btn-sm btn-outline-secondary" (click)="testRecording()" title="Probar detección de sesión activa">
  🧪 Probar Recording
</button>
```

- [ ] **Step 3: Add console log for checkSessions response**

Already added in Task 2 step 1 (the `console.log` lines in `checkSessions()`).

- [ ] **Step 4: Commit**

```bash
git add app/routes/api/sessions.py edysync/src/app/features/therapist/pages/sessions/therapist-sessions.ts edysync/src/app/features/therapist/pages/sessions/therapist-sessions.html
git commit -m "fix: add recording debugging logs and test button"
```

---

### Task 5: Deploy and verify

- [ ] **Step 1: Push to Railway**

```bash
git push railway main
```

- [ ] **Step 2: Verify deployment**

```bash
railway service list
```

Wait for backend deployment to complete.

- [ ] **Step 3: Force redeploy frontend service**

```bash
railway redeploy --service moscowle-frontend-production --yes
```

- [ ] **Step 4: Verify frontend build completes**

```bash
railway service list
```

Check that frontend shows "Online" status.

- [ ] **Step 5: Test manually**
   - Log in as a therapist
   - Open browser console (F12)
   - Check for `[RecordingService] Session #X found` log messages
   - Click "🧪 Probar Recording" to manually trigger detection
   - Verify late-session modal appears when session is 0-10 min late
