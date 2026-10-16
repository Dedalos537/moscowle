import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { CenterDashboard, SedeSummary } from '../../../../../../core/models/center-dashboard';
import { fmtValue, scoreTone } from '../../../sedes/kpi-format';

/** Sedes lado a lado con las cifras que más pesan para crecer; tocar una filtra todo el dashboard. */
@Component({
  selector: 'app-sede-compare',
  standalone: true,
  imports: [RouterLink, FontAwesomeModule],
  templateUrl: './sede-compare.html',
  styleUrl: './sede-compare.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SedeCompare {
  data = input.required<CenterDashboard>();
  pick = output<number>();

  readonly tone = scoreTone;
  readonly fields: { key: keyof SedeSummary['kpis']; label: string; unit: 'money' | 'int' | 'pct' }[] = [
    { key: 'revenue', label: 'Ingresos', unit: 'money' },
    { key: 'active_patients', label: 'Pacientes', unit: 'int' },
    { key: 'attendance', label: 'Asistencia', unit: 'pct' },
    { key: 'retention', label: 'Continuidad', unit: 'pct' },
  ];

  fmt(v: number | null, unit: 'money' | 'int' | 'pct'): string {
    return fmtValue(v, unit);
  }
}
