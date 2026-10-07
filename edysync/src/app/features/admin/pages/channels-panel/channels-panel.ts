import { Component, ChangeDetectionStrategy, ChangeDetectorRef, OnDestroy, OnInit, inject, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { QRCodeComponent } from 'angularx-qrcode';
import { Subject, Subscription, debounceTime, interval } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
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
  imports: [FormsModule, FontAwesomeModule, QRCodeComponent],
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

  ngOnInit() {
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

  sendTest() {
    this.testing = true;
    this.cdr.markForCheck();
    this.admin.testNotifications().subscribe({
      next: (res: any) => {
        this.testing = false;
        this.toast.show(res?.status === 'ok' ? 'Prueba enviada correctamente' : 'Prueba enviada: revisa el SMS y WhatsApp del número de destino', 'success');
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.testing = false;
        this.toast.show(err?.error?.error || 'No se pudo enviar la prueba.', 'error');
        this.cdr.markForCheck();
      },
    });
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
}
