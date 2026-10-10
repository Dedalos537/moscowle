import { Component, input, output, computed, ChangeDetectionStrategy } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Sede, SedeScore } from '../../../../../../core/models/sede';
import { fmtValue, scoreTone } from '../../kpi-format';

/** Tarjeta de una sede: cifras del periodo elegido y acciones. Tocarla la muestra en el scorecard. */
@Component({
  selector: 'app-sede-card',
  standalone: true,
  imports: [FontAwesomeModule],
  templateUrl: './sede-card.html',
  styleUrl: './sede-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SedeCard {
  sede = input.required<Sede>();
  score = input<SedeScore | null>(null);
  selected = input(false);
  loading = input(false);
  select = output<Sede>();
  edit = output<Sede>();
  toggle = output<Sede>();

  readonly tone = computed(() => scoreTone(this.score()?.score));

  /** Pacientes, sesiones e ingresos del periodo, tomados del scorecard (misma fuente que el resto de la página). */
  readonly figures = computed(() => {
    const k = (key: string) => this.score()?.kpis.find((x) => x.key === key);
    return [
      { label: 'Pacientes', value: fmtValue(k('active_patients')?.value ?? null, 'int') },
      { label: 'Sesiones', value: fmtValue(k('sessions_done')?.value ?? null, 'int') },
      { label: 'Ingresos', value: fmtValue(k('revenue')?.value ?? null, 'money') },
    ];
  });
}
