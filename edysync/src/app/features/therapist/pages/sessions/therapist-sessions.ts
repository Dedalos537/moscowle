import { DatePipe } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, computed, inject, signal, TemplateRef, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Router } from '@angular/router';
import { firstValueFrom, Subscription } from 'rxjs';
import { TherapistService } from '../../../../core/services/therapist.service';
import { RecordingService } from '../../../../core/services/recording.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { ToastService } from '../../../../core/services/toast.service';
import { Modal } from '../../../../shared/components/modal/modal';
import { Select, SelectOption } from '../../../../shared/components/select/select';
import { Button } from '../../../../shared/components/button/button';
import { CalendarWidget, CalendarWidgetEvent } from '../../../../shared/components/calendar-widget/calendar-widget';
import { toLocalDateString, timeFromISO, dateFromISO } from '../../../../core/utils/date.util';

type Status = 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

/** Sesión tal como la usa la pantalla: un solo lugar decide de dónde sale cada dato del backend. */
interface AgendaItem {
  id: number;
  title: string;
  patient: string;
  patientId: number | null;
  date: string; // YYYY-MM-DD local
  start: string; // HH:MM
  end: string;
  minutes: number | null;
  status: Status;
  attendance: string | null;
  location: string;
  notes: string;
  auditScore: number | null;
  hasTranscript: boolean;
  hasProgram: boolean;
  groupSession: boolean;
}

const STATUS_LABEL: Record<string, string> = {
  scheduled: 'Programada',
  in_progress: 'En curso',
  completed: 'Realizada',
  cancelled: 'Cancelada',
};

const DAY_SHORT = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
const DAY_LONG = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toItem(e: any): AgendaItem {
  const ext = e.extendedProps ?? {};
  const start = timeFromISO(e.start);
  const end = timeFromISO(e.end);
  let minutes: number | null = null;
  if (e.start && e.end) minutes = Math.round((Date.parse(e.end) - Date.parse(e.start)) / 60000);
  return {
    id: e.id,
    title: e.title || 'Sesión',
    patient: e.patient?.name || ext.patient || '',
    patientId: e.patient?.id ?? ext.patient_id ?? null,
    date: dateFromISO(e.start),
    start,
    end,
    minutes: minutes && minutes > 0 ? minutes : null,
    status: (e.status || ext.status || 'scheduled') as Status,
    attendance: e.attendance ?? null,
    location: e.location || '',
    notes: (e.notes || ext.feedback_notes || ext.notes || '').trim(),
    auditScore: e.audit_score ?? ext.audit_score ?? null,
    hasTranscript: !!(e.has_transcript ?? ext.has_transcript),
    hasProgram: !!(e.has_program ?? ext.has_program),
    groupSession: (ext.session_type || 'individual') === 'group',
  };
}

@Component({
  selector: 'app-therapist-sessions',
  standalone: true,
  imports: [DatePipe, FormsModule, FontAwesomeModule, Modal, Select, Button, CalendarWidget],
  templateUrl: './therapist-sessions.html',
  styleUrl: './therapist-sessions.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TherapistSessions implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<unknown>;

  private therapistService = inject(TherapistService);
  private recordingService = inject(RecordingService);
  private headerService = inject(HeaderService);
  private router = inject(Router);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);
  private subs = new Subscription();
  private daySub?: Subscription;

  readonly view = signal<'week' | 'month'>('week');
  readonly selected = signal<Date>(this.startOfDay(new Date()));
  readonly items = signal<AgendaItem[]>([]);
  readonly loading = signal(true);
  readonly loadError = signal<string | null>(null);
  /** Dirección de la animación al cambiar de día (−1 = hacia atrás). */
  readonly slide = signal<-1 | 0 | 1>(0);
  readonly weekCounts = signal<Record<string, { total: number; done: number }>>({});
  readonly activePatients = signal<number | null>(null);

  readonly monthEvents = signal<CalendarWidgetEvent[]>([]);
  readonly monthCursor = signal<Date>(new Date());
  readonly monthLoading = signal(false);

  // Edición
  readonly editing = signal<AgendaItem | null>(null);
  readonly saving = signal(false);
  readonly deleting = signal(false);
  readonly formError = signal<string | null>(null);
  form = { title: '', date: '', start: '', end: '', status: 'scheduled' as string, attendance: 'pending' as string };
  readonly attendanceOptions: SelectOption[] = [
    { value: 'pending', label: 'Sin registrar' },
    { value: 'present', label: 'Asistió' },
    { value: 'absent', label: 'Faltó' },
  ];
  readonly statusOptions: SelectOption[] = [
    { value: 'scheduled', label: 'Programada' },
    { value: 'completed', label: 'Realizada' },
    { value: 'cancelled', label: 'Cancelada' },
  ];

  readonly notesOf = signal<AgendaItem | null>(null);

  // Sesión que se está grabando ahora (aviso flotante).
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  readonly live = signal<any>(null);
  readonly liveDismissed = signal(false);

  readonly week = computed(() => {
    const d = this.selected();
    const monday = new Date(d);
    monday.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    const today = toLocalDateString(new Date());
    const sel = toLocalDateString(d);
    const counts = this.weekCounts();
    return Array.from({ length: 7 }, (_, i) => {
      const day = new Date(monday);
      day.setDate(monday.getDate() + i);
      const key = toLocalDateString(day);
      return {
        date: day,
        key,
        short: DAY_SHORT[day.getDay()],
        num: day.getDate(),
        today: key === today,
        selected: key === sel,
        total: counts[key]?.total ?? 0,
        done: counts[key]?.done ?? 0,
      };
    });
  });

  readonly weekLabel = computed(() => {
    const w = this.week();
    const a = w[0].date;
    const b = w[6].date;
    if (a.getMonth() === b.getMonth()) return `${a.getDate()}–${b.getDate()} de ${MONTHS[b.getMonth()]} ${b.getFullYear()}`;
    return `${a.getDate()} ${MONTHS[a.getMonth()].slice(0, 3)} – ${b.getDate()} ${MONTHS[b.getMonth()].slice(0, 3)} ${b.getFullYear()}`;
  });

  readonly dayTitle = computed(() => {
    const d = this.selected();
    const key = toLocalDateString(d);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    const prefix =
      key === toLocalDateString(today) ? 'Hoy' : key === toLocalDateString(tomorrow) ? 'Mañana' : key === toLocalDateString(yesterday) ? 'Ayer' : '';
    const long = `${DAY_LONG[d.getDay()]} ${d.getDate()} de ${MONTHS[d.getMonth()]}`;
    return prefix ? `${prefix}, ${long}` : long.charAt(0).toUpperCase() + long.slice(1);
  });

  readonly isToday = computed(() => toLocalDateString(this.selected()) === toLocalDateString(new Date()));

  readonly daySummary = computed(() => {
    const list = this.items();
    const minutes = list.filter((i) => i.status !== 'cancelled').reduce((s, i) => s + (i.minutes ?? 0), 0);
    return {
      total: list.filter((i) => i.status !== 'cancelled').length,
      done: list.filter((i) => i.status === 'completed').length,
      pending: list.filter((i) => i.status === 'scheduled' || i.status === 'in_progress').length,
      cancelled: list.filter((i) => i.status === 'cancelled').length,
      hours: minutes ? (minutes >= 60 ? `${Math.floor(minutes / 60)} h${minutes % 60 ? ' ' + (minutes % 60) + ' min' : ''}` : `${minutes} min`) : '—',
    };
  });

  /** Próxima sesión del día seleccionado si es hoy (para resaltarla). */
  readonly nextId = computed(() => {
    if (!this.isToday()) return null;
    const now = new Date();
    const hhmm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    return this.items().find((i) => i.status === 'in_progress')?.id ?? this.items().find((i) => i.status === 'scheduled' && (i.end || i.start) >= hhmm)?.id ?? null;
  });

  readonly monthSummary = computed(() => {
    const m = this.monthCursor();
    const list = this.monthEvents().filter((e) => e.date.getMonth() === m.getMonth() && e.date.getFullYear() === m.getFullYear());
    const done = list.filter((e) => e.status === 'completed').length;
    const cancelled = list.filter((e) => e.status === 'cancelled').length;
    const held = list.length - cancelled;
    const counts: Record<number, number> = {};
    list.filter((e) => e.status !== 'cancelled').forEach((e) => (counts[e.date.getDay()] = (counts[e.date.getDay()] ?? 0) + 1));
    const busiest = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
    return {
      label: `${MONTHS[m.getMonth()]} ${m.getFullYear()}`,
      total: held,
      done,
      pending: list.filter((e) => e.status === 'scheduled').length,
      cancelled,
      rate: held ? Math.round((done / held) * 100) : null,
      busiest: busiest ? DAY_LONG[+busiest[0]] : '—',
    };
  });

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mis sesiones',
      subtitle: 'Agenda, registro y revisión',
      icon: ['fas', 'calendar-days'],
      actionTemplate: this.headerActions,
    });
    this.loadDay();
    this.loadWeekCounts();
    this.subs.add(
      this.therapistService.getDashboardStats().subscribe({
        next: (s) => this.activePatients.set(s.active_patients),
        error: () => this.activePatients.set(null),
      }),
    );
    this.subs.add(
      this.recordingService.activeSession$.subscribe((session) => {
        if (!session?.id) {
          this.live.set(null);
          return;
        }
        this.liveDismissed.set(false);
        this.subs.add(
          this.therapistService.getSessionBriefing(session.id).subscribe({
            next: (b) => this.live.set(b),
            error: () => this.live.set({ session: { id: session.id, title: 'Sesión en curso' } }),
          }),
        );
      }),
    );
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subs.unsubscribe();
    this.daySub?.unsubscribe();
  }

  // ── navegación ──────────────────────────────────────────────────────────
  selectDay(d: Date) {
    const prev = toLocalDateString(this.selected());
    const next = toLocalDateString(d);
    if (prev === next) return;
    const weekChanged = this.mondayKey(d) !== this.mondayKey(this.selected());
    this.slide.set(next > prev ? 1 : -1);
    this.selected.set(this.startOfDay(d));
    this.loadDay();
    if (weekChanged) this.loadWeekCounts();
  }

  shiftWeek(dir: -1 | 1) {
    const d = new Date(this.selected());
    d.setDate(d.getDate() + 7 * dir);
    this.selectDay(d);
  }

  shiftDay(dir: -1 | 1) {
    const d = new Date(this.selected());
    d.setDate(d.getDate() + dir);
    this.selectDay(d);
  }

  goToday() {
    this.view.set('week');
    this.selectDay(new Date());
  }

  setView(v: 'week' | 'month') {
    this.view.set(v);
    if (v === 'month') this.loadMonth(this.selected());
  }

  onMonthChange(month: Date) {
    this.loadMonth(month);
  }

  /** En el mes, tocar un día abre su agenda. */
  onMonthDay(d: Date) {
    this.view.set('week');
    this.selectDay(d);
  }

  onWeekKey(ev: KeyboardEvent) {
    const map: Record<string, -1 | 1> = { ArrowLeft: -1, ArrowRight: 1 };
    if (!map[ev.key]) return;
    ev.preventDefault();
    this.shiftDay(map[ev.key]);
    queueMicrotask(() => (ev.currentTarget as HTMLElement)?.querySelector<HTMLElement>('[aria-current="date"], .is-selected')?.focus());
  }

  // ── datos ───────────────────────────────────────────────────────────────
  loadDay() {
    const f = toLocalDateString(this.selected());
    this.loading.set(true);
    this.loadError.set(null);
    this.daySub?.unsubscribe();
    this.daySub = this.therapistService.getSessions(f, f).subscribe({
      next: (events) => {
        this.items.set(events.map(toItem).sort((a, b) => a.start.localeCompare(b.start)));
        this.loading.set(false);
      },
      error: (e) => {
        this.items.set([]);
        this.loading.set(false);
        this.loadError.set(e?.error?.message || e?.error?.error || 'No se pudo cargar la agenda.');
      },
    });
  }

  private loadWeekCounts() {
    const w = this.week();
    this.subs.add(
      this.therapistService.getSessions(w[0].key, w[6].key).subscribe({
        next: (events) => {
          const counts: Record<string, { total: number; done: number }> = {};
          events.map(toItem).forEach((i) => {
            if (!i.date || i.status === 'cancelled') return;
            counts[i.date] ??= { total: 0, done: 0 };
            counts[i.date].total++;
            if (i.status === 'completed') counts[i.date].done++;
          });
          this.weekCounts.set(counts);
        },
        error: () => this.weekCounts.set({}),
      }),
    );
  }

  private loadMonth(month: Date) {
    this.monthCursor.set(month);
    const start = toLocalDateString(new Date(month.getFullYear(), month.getMonth(), 1));
    const end = toLocalDateString(new Date(month.getFullYear(), month.getMonth() + 1, 0));
    this.monthLoading.set(true);
    this.subs.add(
      this.therapistService.getSessions(start, end).subscribe({
        next: (events) => {
          this.monthEvents.set(
            events.map(toItem).map((i) => ({
              id: i.id,
              title: i.patient || i.title,
              date: new Date(`${i.date}T12:00:00`),
              time: i.start,
              endTime: i.end,
              status: (i.status === 'in_progress' ? 'scheduled' : i.status) as CalendarWidgetEvent['status'],
              patient: i.patient,
            })),
          );
          this.monthLoading.set(false);
        },
        error: () => {
          this.monthEvents.set([]);
          this.monthLoading.set(false);
        },
      }),
    );
  }

  private refresh() {
    this.loadDay();
    this.loadWeekCounts();
    if (this.view() === 'month') this.loadMonth(this.monthCursor());
  }

  // ── acciones ────────────────────────────────────────────────────────────
  review(id: number) {
    this.router.navigate(['/therapist/sessions', id, 'review']);
  }

  openPatient(i: AgendaItem) {
    if (i.patientId) this.router.navigate(['/therapist/patients', i.patientId]);
  }

  openEdit(i: AgendaItem) {
    this.form = {
      title: i.title,
      date: i.date,
      start: i.start,
      end: i.end,
      status: i.status === 'in_progress' ? 'scheduled' : i.status,
      attendance: i.attendance === 'present' || i.attendance === 'absent' ? i.attendance : 'pending',
    };
    this.formError.set(null);
    this.editing.set(i);
  }

  closeEdit() {
    this.editing.set(null);
  }

  submitEdit() {
    const item = this.editing();
    if (!item) return;
    const f = this.form;
    if (!f.date || !f.start) {
      this.formError.set('Indica la fecha y la hora de inicio.');
      return;
    }
    if (f.end && f.end <= f.start) {
      this.formError.set('La hora de fin debe ser posterior a la de inicio.');
      return;
    }
    this.saving.set(true);
    this.formError.set(null);
    const payload: { title: string; start_time: string; status: string; attendance: string; end_time?: string } = {
      title: f.title.trim() || item.title,
      start_time: `${f.date}T${f.start}`,
      status: f.status,
      attendance: f.attendance,
    };
    if (f.end) payload.end_time = `${f.date}T${f.end}`;
    this.subs.add(
      this.therapistService.updateSession(item.id, payload).subscribe({
        next: () => {
          this.saving.set(false);
          this.closeEdit();
          this.toastService.show('Sesión actualizada', 'success');
          if (f.date !== toLocalDateString(this.selected())) this.selectDay(new Date(`${f.date}T12:00:00`));
          this.refresh();
        },
        error: (e) => {
          this.saving.set(false);
          const errs = e?.error?.errors;
          this.formError.set(Array.isArray(errs) && errs.length ? errs.join(' ') : e?.error?.message || 'No se pudo guardar la sesión.');
        },
      }),
    );
  }

  async quickStatus(i: AgendaItem, status: 'completed' | 'cancelled') {
    if (status === 'cancelled') {
      const ok = await firstValueFrom(
        this.confirmService.confirm({
          title: 'Cancelar sesión',
          message: `La sesión de ${i.patient || i.title} a las ${i.start} quedará cancelada. El paciente verá el cambio en su calendario.`,
          confirmText: 'Cancelar sesión',
          cancelText: 'Volver',
          variant: 'danger',
        }),
      );
      if (!ok) return;
    }
    this.subs.add(
      // «Realizada» desde la agenda implica que el paciente asistió; si faltó, se registra desde Editar.
      this.therapistService.updateSession(i.id, status === 'completed' ? { status, attendance: 'present' } : { status }).subscribe({
        next: () => {
          this.items.update((list) =>
            list.map((x) => (x.id === i.id ? { ...x, status, attendance: status === 'completed' ? 'present' : x.attendance } : x)),
          );
          this.toastService.show(status === 'completed' ? 'Sesión marcada como realizada' : 'Sesión cancelada', 'success');
          this.loadWeekCounts();
        },
        error: (e) => this.toastService.show(e?.error?.message || 'No se pudo actualizar la sesión', 'error'),
      }),
    );
  }

  async deleteSession() {
    const item = this.editing();
    if (!item) return;
    const ok = await firstValueFrom(
      this.confirmService.confirm({
        title: 'Eliminar sesión',
        message: 'Se borrará la sesión y su registro. Si solo no se realizará, mejor márcala como cancelada.',
        confirmText: 'Eliminar',
        cancelText: 'Volver',
        variant: 'danger',
      }),
    );
    if (!ok) return;
    this.deleting.set(true);
    this.subs.add(
      this.therapistService.deleteSession(item.id).subscribe({
        next: () => {
          this.deleting.set(false);
          this.closeEdit();
          this.toastService.show('Sesión eliminada', 'success');
          this.refresh();
        },
        error: (e) => {
          this.deleting.set(false);
          this.formError.set(e?.error?.message || 'No se pudo eliminar la sesión.');
        },
      }),
    );
  }

  // ── presentación ────────────────────────────────────────────────────────
  statusLabel(s: string) {
    return STATUS_LABEL[s] ?? s;
  }

  attendanceLabel(a: string | null) {
    return a === 'present' ? 'Asistió' : a === 'absent' ? 'Faltó' : null;
  }

  duration(m: number | null) {
    if (!m) return '';
    return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h${m % 60 ? ' ' + (m % 60) : ''}`;
  }

  initials(name: string) {
    return (name || '?')
      .split(/\s+/)
      .filter(Boolean)
      .map((w) => w[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();
  }

  auditTone(score: number | null) {
    return score == null ? 'none' : score >= 70 ? 'good' : score >= 40 ? 'warn' : 'bad';
  }

  private startOfDay(d: Date) {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }

  private mondayKey(d: Date) {
    const m = new Date(d);
    m.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    return toLocalDateString(m);
  }
}
