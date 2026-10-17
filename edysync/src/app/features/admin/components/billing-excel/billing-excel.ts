import { ChangeDetectionStrategy, Component, OnInit, computed, inject, input, output, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { AdminService } from '../../../../core/services/admin.service';
import { ToastService } from '../../../../core/services/toast.service';
import { BillingImportRecord, BillingImportResult, BillingImportRow } from '../../../../core/models/billing';
import { Drawer } from '../../../../shared/components/drawer/drawer';

/**
 * Excel de cobranza (PRP 008): descarga los pagos fuera de contratos con los contratos propuestos y los importa
 * con vista previa fila por fila. Se aplica todo o nada, y cada importación queda registrada.
 */
@Component({
  selector: 'app-billing-excel',
  standalone: true,
  imports: [DatePipe, FontAwesomeModule, Drawer],
  templateUrl: './billing-excel.html',
  styleUrl: './billing-excel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BillingExcel implements OnInit {
  private admin = inject(AdminService);
  private toast = inject(ToastService);

  withoutContract = input(0);
  imported = output<void>();

  readonly downloading = signal(false);
  readonly busy = signal(false);
  readonly file = signal<File | null>(null);
  readonly result = signal<BillingImportResult | null>(null);
  readonly filter = signal<'all' | 'error'>('all');
  readonly history = signal<BillingImportRecord[]>([]);
  readonly error = signal('');

  readonly rows = computed<BillingImportRow[]>(() => {
    const r = this.result()?.rows ?? [];
    return this.filter() === 'error' ? r.filter((x) => x.status === 'error') : r;
  });
  readonly errors = computed(() => this.result()?.summary['errors'] ?? 0);
  readonly chips = computed(() => {
    const s = this.result()?.summary ?? {};
    const n = (k: string) => s[k] ?? 0;
    return [
      { label: 'Contratos nuevos', value: String(n('contracts_created')) },
      { label: 'Pagos a cuotas', value: String(n('applied') + n('new_applied')) },
      { label: 'Aplicado a cuotas', value: 'S/ ' + n('amount_applied').toFixed(2) },
      { label: 'Pagos sueltos', value: String(n('one_off') + n('new_one_off')) },
      { label: 'Ya aplicados (se saltan)', value: String(n('already_applied')) },
      { label: 'Posibles duplicados', value: String(n('duplicates')) },
      { label: 'Deuda vencida resultante', value: 'S/ ' + n('overdue_after').toFixed(2), warn: n('overdue_after') > 0 },
      { label: 'Saldo a favor', value: 'S/ ' + n('credit_total').toFixed(2) },
    ];
  });

  ngOnInit() {
    this.loadHistory();
  }

  private loadHistory() {
    this.admin.billingImports().subscribe({ next: (r) => this.history.set(r.imports.slice(0, 3)), error: () => {} });
  }

  download() {
    this.downloading.set(true);
    this.admin.exportBillingExcel().subscribe({
      next: (blob) => {
        const a = document.createElement('a');
        const d = new Date();
        a.href = URL.createObjectURL(blob);
        a.download = `cobranza-pagos-fuera-de-contratos-${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}.xlsx`;
        a.click();
        setTimeout(() => URL.revokeObjectURL(a.href), 4000);
        this.downloading.set(false);
      },
      error: () => {
        this.downloading.set(false);
        this.toast.show('No se pudo generar el Excel.', 'error');
      },
    });
  }

  pick(ev: Event) {
    const input = ev.target as HTMLInputElement;
    const f = input.files?.[0] ?? null;
    input.value = '';
    if (!f) return;
    this.file.set(f);
    this.run(false);
  }

  run(apply: boolean) {
    const f = this.file();
    if (!f || this.busy()) return;
    this.busy.set(true);
    this.error.set('');
    this.admin.importBillingExcel(f, apply).subscribe({
      next: (r) => {
        this.busy.set(false);
        this.result.set(r);
        this.filter.set(r.summary['errors'] ? 'error' : 'all');
        if (r.applied) {
          this.toast.show(`Importación aplicada: ${r.summary['contracts_created'] ?? 0} contratos y ${(r.summary['applied'] ?? 0) + (r.summary['new_applied'] ?? 0)} pagos a cuotas.`, 'success', 7000);
          this.loadHistory();
          this.imported.emit();
        }
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(e?.error?.message || 'No se pudo procesar el archivo.');
        if (!this.result()) this.result.set({ success: false, ok: false, applied: false, sha256: '', summary: {}, rows: [] });
      },
    });
  }

  close() {
    this.result.set(null);
    this.file.set(null);
    this.error.set('');
  }

  label(status: BillingImportRow['status']): string {
    return { ok: 'Se aplica', skip: 'Se salta', error: 'Error', warn: 'Revisar', info: 'Resultado' }[status];
  }
}
