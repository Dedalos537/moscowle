import { Component, ChangeDetectionStrategy, ChangeDetectorRef, OnDestroy, OnInit, inject, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { QRCodeComponent } from 'angularx-qrcode';
import { Subject, Subscription, debounceTime, distinctUntilChanged, interval, switchMap } from 'rxjs';
import { Switch } from '../../../../shared/components/switch/switch';
import { AdminService, type AutomationSettings } from '../../../../core/services/admin.service';
import { LiveSyncService } from '../../../../core/services/live-sync.service';
import { ToastService } from '../../../../core/services/toast.service';

type Field = 'destination' | 'sms_template' | 'whatsapp_template';

const SAMPLE = { patient_name: 'Mateo Rojas', amount: 120, due_date_str: '15/10/2026', days_overdue: 3 };
const VARIABLES: { name: string; hint: string }[] = [
  { name: 'patient_name', hint: 'Nombre del paciente' },
  { name: 'amount', hint: 'Monto adeudado' },
  { name: 'due_date_str', hint: 'Fecha de vencimiento' },
  { name: 'days_overdue', hint: 'Días de atraso' },
];

/**
 * Canales de aviso: conexión de WhatsApp, estado de Telegram y mensajes de SMS/WhatsApp.
 * Todo se guarda solo (con aviso de «Guardado») y se recarga si alguien lo cambia desde otro lado.
 */
@Component({
  selector: 'app-channels-panel',
  standalone: true,
  imports: [FormsModule, FontAwesomeModule, QRCodeComponent, Switch],
  templateUrl: './channels-panel.html',
  styleUrl: './channels-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChannelsPanel implements OnInit, OnDestroy {
  /** Pide al contenedor ir a la configuración del bot (Telegram). */
  openBot = output<void>();

  private admin = inject(AdminService);
  private live = inject(LiveSyncService);
  private toast = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);
  private subs = new Subscription();
  private autosave$ = new Subject<void>();

  readonly variables = VARIABLES;
  readonly templates: { id: 'sms_template' | 'whatsapp_template'; label: string; ph: string }[] = [
    { id: 'sms_template', label: 'Plantilla de SMS', ph: 'Hola {patient_name}, tienes un pago pendiente de S/ {amount:.2f}…' },
    { id: 'whatsapp_template', label: 'Plantilla de WhatsApp', ph: '¡Hola {patient_name}! Te recordamos tu pago de S/ {amount:.2f} vencido el {due_date_str}.' },
  ];

  // Mensajes
  form: Record<Field, string> = { destination: '', sms_template: '', whatsapp_template: '' };
  private saved: Record<Field, string> = { destination: '', sms_template: '', whatsapp_template: '' };
  errors: Partial<Record<Field, string>> = {};
  loading = true;
  saveState: 'idle' | 'saving' | 'saved' | 'error' = 'idle';
  private focused: Field | null = null;
  testing = false;

  // WhatsApp
  wa: any = null;
  waQr: string | null = null;
  waQrLoading = false;
  waError: string | null = null;
  private qrPoll: Subscription | null = null;

  // Telegram
  tgLinked = 0;
  tgBotActive: boolean | null = null;

  // Avisos a padres
  readonly modes: { id: AutomationSettings['mode']; title: string; hint: string }[] = [
    { id: 'all', title: 'Todos', hint: 'Cada familia recibe sus avisos' },
    { id: 'pilot', title: 'Solo una familia', hint: 'Para probar sin molestar a nadie más' },
    { id: 'off', title: 'Apagado', hint: 'No sale ningún aviso automático' },
  ];
  readonly kinds: { id: 'sessions' | 'debts' | 'whatsapp' | 'sms' | 'email' | 'whatsapp_bot'; label: string; hint: string }[] = [
    { id: 'sessions', label: 'Recordatorio de sesiones', hint: 'El día anterior a cada sesión' },
    { id: 'debts', label: 'Cobranza de pagos', hint: 'Pagos vencidos y por vencer' },
    { id: 'whatsapp', label: 'Por WhatsApp', hint: 'Desde el número vinculado del centro' },
    { id: 'sms', label: 'Por SMS', hint: 'Como respaldo o si WhatsApp no está' },
    { id: 'email', label: 'Por correo', hint: 'Al correo del apoderado (o del paciente si no hay)' },
    { id: 'whatsapp_bot', label: 'El bot contesta en WhatsApp', hint: 'Responde con las FAQ del centro; tú puedes tomar la conversación cuando quieras' },
  ];
  auto: AutomationSettings | null = null;
  autoBusy = false;
  autoTesting: 'whatsapp' | 'sms' | 'email' | null = null;
  pilotQuery = '';
  pilotResults: { id: number; username: string; phone: string | null }[] = [];
  private pilotSearch$ = new Subject<string>();

  ngOnInit() {
    this.loadAutomation();
    this.subs.add(
      this.pilotSearch$.pipe(debounceTime(250), distinctUntilChanged(), switchMap((q) => this.admin.searchAutomationPatients(q))).subscribe((rows) => {
        this.pilotResults = rows;
        this.cdr.markForCheck();
      }),
    );
    this.subs.add(this.live.watch(['channels']).subscribe(() => this.loadAutomation()));
    this.loadConfig();
    this.loadWhatsapp();
    this.loadTelegram();

    this.subs.add(this.autosave$.pipe(debounceTime(700)).subscribe(() => this.save()));
    this.subs.add(interval(10000).subscribe(() => { if (!this.waQr) this.loadWhatsapp(); this.loadTelegram(); }));
    // Cambio hecho por otra persona o pestaña: se vuelve a leer, salvo que el usuario esté escribiendo ahora mismo.
    this.subs.add(this.live.watch(['channels']).subscribe(() => { if (!this.focused) this.loadConfig(); }));
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    this.qrPoll?.unsubscribe();
  }

  // ── Mensajes ─────────────────────────────────────────────────────────────
  private loadConfig() {
    this.admin.getNotificationConfig().subscribe({
      next: (res) => {
        const next = { destination: res.destination || '', sms_template: res.sms_template || '', whatsapp_template: res.whatsapp_template || '' };
        this.form = { ...next };
        this.saved = { ...next };
        this.errors = {};
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.toast.show('No se pudo cargar la configuración de canales.', 'error');
        this.cdr.markForCheck();
      },
    });
  }

  get dirty(): boolean {
    return (Object.keys(this.form) as Field[]).some((k) => this.form[k] !== this.saved[k]);
  }

  onEdit(field: Field) {
    this.focused = field;
    delete this.errors[field];
    this.saveState = 'idle';
    this.autosave$.next();
  }

  onBlur() {
    this.focused = null;
    if (this.dirty) this.save();
  }

  private save() {
    if (!this.dirty) return;
    const payload: Record<string, string> = {};
    (Object.keys(this.form) as Field[]).forEach((k) => { if (this.form[k] !== this.saved[k]) payload[k] = this.form[k]; });
    this.saveState = 'saving';
    this.cdr.markForCheck();
    this.admin.updateNotificationConfig(payload).subscribe({
      next: () => {
        Object.assign(this.saved, payload);
        this.errors = {};
        this.saveState = 'saved';
        this.cdr.markForCheck();
        setTimeout(() => { if (this.saveState === 'saved') { this.saveState = 'idle'; this.cdr.markForCheck(); } }, 2200);
      },
      error: (err) => {
        this.errors = err?.error?.fields || {};
        this.saveState = 'error';
        if (!Object.keys(this.errors).length) this.toast.show(err?.error?.error || 'No se pudo guardar.', 'error');
        this.cdr.markForCheck();
      },
    });
  }

  setField(field: Field, value: string) {
    this.form[field] = value;
    this.onEdit(field);
  }

  insertVariable(field: 'sms_template' | 'whatsapp_template', name: string) {
    const token = name === 'amount' ? '{amount:.2f}' : `{${name}}`;
    const current = this.form[field];
    this.form[field] = current && !current.endsWith(' ') ? `${current} ${token}` : `${current}${token}`;
    this.onEdit(field);
  }

  /** Vista previa con datos de ejemplo (mismo reemplazo que hace el servidor). */
  preview(template: string): string {
    if (!template) return '';
    return template
      .replace(/\{amount:\.2f\}/g, SAMPLE.amount.toFixed(2))
      .replace(/\{(patient_name|amount|due_date_str|days_overdue)\}/g, (_m, k: keyof typeof SAMPLE) => String(SAMPLE[k]));
  }

  /** Cobranza de prueba al «Número de pruebas»: guarda lo pendiente y envía tus plantillas por WhatsApp y SMS. */
  sendTest() {
    if (this.testing) return;
    if (!this.form.destination.trim()) {
      this.toast.show('Escribe el número de pruebas para enviar la cobranza de ejemplo.', 'warning');
      return;
    }
    this.testing = true;
    this.cdr.markForCheck();
    const send = () =>
      this.admin.testCollectionToNumber().subscribe({
        next: (res) => this.reportTest(res.phone, res.results),
        error: (err) => {
          if (err?.error?.results) this.reportTest(err.error.phone, err.error.results);
          else {
            this.testing = false;
            this.toast.show(err?.error?.error || 'No se pudo enviar la prueba.', 'error');
            this.cdr.markForCheck();
          }
        },
      });
    if (!this.dirty) {
      send();
      return;
    }
    // Primero se guarda lo que escribiste: la prueba usa lo guardado.
    const payload: Record<string, string> = {};
    (Object.keys(this.form) as Field[]).forEach((k) => { if (this.form[k] !== this.saved[k]) payload[k] = this.form[k]; });
    this.admin.updateNotificationConfig(payload).subscribe({
      next: () => { Object.assign(this.saved, payload); this.errors = {}; send(); },
      error: (err) => {
        this.testing = false;
        this.errors = err?.error?.fields || {};
        this.toast.show(Object.keys(this.errors).length ? 'Revisa los campos marcados antes de probar.' : err?.error?.error || 'No se pudo guardar.', 'error');
        this.cdr.markForCheck();
      },
    });
  }

  private reportTest(phone: string, results: Record<string, { ok: boolean; error?: string | null }>) {
    this.testing = false;
    const label = (c: string) => (c === 'sms' ? 'SMS' : 'WhatsApp');
    const parts = Object.entries(results).map(([c, r]) => (r.ok ? `${label(c)} enviado` : `${label(c)}: ${r.error || 'no salió'}`));
    const anyOk = Object.values(results).some((r) => r.ok);
    this.toast.show(`Prueba a ${phone} · ${parts.join(' · ')}`, anyOk ? 'success' : 'error');
    this.cdr.markForCheck();
  }

  // ── WhatsApp ─────────────────────────────────────────────────────────────
  loadWhatsapp() {
    this.admin.getWhatsappStatus().subscribe({
      next: (res) => { this.wa = res; this.waError = null; this.cdr.markForCheck(); },
      error: () => { this.waError = 'No se pudo leer el estado de WhatsApp.'; this.cdr.markForCheck(); },
    });
  }

  requestQr() {
    this.waQrLoading = true;
    this.waError = null;
    this.cdr.markForCheck();
    this.admin.getWhatsappQr().subscribe({
      next: (res) => {
        this.waQrLoading = false;
        this.waQr = res?.qr ?? null;
        if (!this.waQr) this.waError = res?.message ?? 'No se pudo generar el QR.';
        else this.startQrPolling();
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.waQrLoading = false;
        this.waError = err?.error?.error || err?.error?.message || 'No se pudo generar el QR.';
        this.cdr.markForCheck();
      },
    });
  }

  private startQrPolling() {
    this.qrPoll?.unsubscribe();
    this.qrPoll = interval(3000).subscribe(() => {
      this.admin.getWhatsappStatus().subscribe((res) => {
        this.wa = res;
        if (res?.connected) {
          this.waQr = null;
          this.qrPoll?.unsubscribe();
          this.toast.show('WhatsApp conectado', 'success');
        }
        this.cdr.markForCheck();
      });
    });
  }

  // ── Telegram ─────────────────────────────────────────────────────────────
  private loadTelegram() {
    this.admin.getTelegramStatus().subscribe({
      next: (res: any) => {
        this.tgLinked = (res?.linked_accounts || []).filter((a: any) => a.is_linked).length;
        this.tgBotActive = res?.bot_active ?? res?.configured ?? null;
        this.cdr.markForCheck();
      },
      error: () => { this.tgBotActive = null; this.cdr.markForCheck(); },
    });
  }

  // ── Avisos a padres ──────────────────────────────────────────────────────
  private loadAutomation() {
    this.admin.getAutomation().subscribe({
      next: (res) => { this.auto = res; this.cdr.markForCheck(); },
      error: () => this.toast.show('No se pudo leer la configuración de avisos a padres.', 'error'),
    });
  }

  patchAutomation(patch: Parameters<AdminService['updateAutomation']>[0]) {
    if (!this.auto || this.autoBusy) return;
    const before = this.auto;
    this.auto = { ...this.auto, ...patch };
    this.autoBusy = true;
    this.cdr.markForCheck();
    this.admin.updateAutomation(patch).subscribe({
      next: (res) => {
        this.auto = { ...res, last_24h: before.last_24h };
        this.autoBusy = false;
        this.saveState = 'saved';
        this.cdr.markForCheck();
        setTimeout(() => { if (this.saveState === 'saved') { this.saveState = 'idle'; this.cdr.markForCheck(); } }, 2200);
      },
      error: (err) => {
        this.auto = before;
        this.autoBusy = false;
        this.toast.show(err?.error?.fields?.pilot_patient_id || err?.error?.error || 'No se pudo guardar el cambio.', 'error');
        this.cdr.markForCheck();
      },
    });
  }

  setFlag(id: 'sessions' | 'debts' | 'whatsapp' | 'sms' | 'email' | 'whatsapp_bot', value: boolean) {
    this.patchAutomation({ [id]: value });
  }

  setMode(mode: AutomationSettings['mode']) {
    if (mode === 'pilot' && !this.auto?.pilot_patient_id) {
      this.auto = this.auto && { ...this.auto, mode };
      this.searchPilot('');
      this.cdr.markForCheck();
      return;
    }
    this.patchAutomation({ mode });
  }

  flag(id: 'sessions' | 'debts' | 'whatsapp' | 'sms' | 'email' | 'whatsapp_bot'): boolean {
    return !!this.auto?.[id];
  }

  searchPilot(q: string) {
    this.pilotQuery = q;
    this.pilotSearch$.next(q);
  }

  choosePilot(p: { id: number }) {
    this.pilotResults = [];
    this.pilotQuery = '';
    this.patchAutomation({ mode: 'pilot', pilot_patient_id: p.id });
  }

  sent24(channel: string): number {
    return this.auto?.last_24h?.[channel]?.['sent'] ?? 0;
  }

  testPilot(channel: 'whatsapp' | 'sms' | 'email') {
    if (this.autoTesting || !this.auto?.pilot_patient_id) return;
    this.autoTesting = channel;
    this.cdr.markForCheck();
    this.admin.testAutomation(channel, this.auto.pilot_patient_id).subscribe({
      next: (res) => {
        this.autoTesting = null;
        this.toast.show(`Prueba enviada al apoderado de ${res.patient}${res.phone ? ' (' + res.phone + ')' : ''}`, 'success');
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.autoTesting = null;
        this.toast.show(err?.error?.reason || err?.error?.error || 'No se pudo enviar la prueba.', 'error');
        this.cdr.markForCheck();
      },
    });
  }
}
