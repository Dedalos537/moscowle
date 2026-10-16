import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { CenterDashboard } from '../../../../../../core/models/center-dashboard';
import { PersonLabelPipe } from '../../../../../../shared/pipes/person-label.pipe';

/**
 * Equipo: carga y resultados de cada terapeuta en el periodo. La barra compara sus sesiones con el promedio del
 * equipo, así se ve quién está saturado (riesgo para la continuidad) y quién tiene espacio para nuevos pacientes.
 */
@Component({
  selector: 'app-team-panel',
  standalone: true,
  imports: [RouterLink, FontAwesomeModule, PersonLabelPipe],
  templateUrl: './team-panel.html',
  styleUrl: './team-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TeamPanel {
  data = input.required<CenterDashboard>();
  readonly open = signal<number | null>(null);

  readonly rows = computed(() => {
    const team = this.data().team;
    const max = Math.max(...team.map((t) => t.sessions_done), 1);
    const avg = team.length ? team.reduce((s, t) => s + t.sessions_done, 0) / team.length : 0;
    return team.map((t) => ({
      ...t,
      width: (t.sessions_done / max) * 100,
      vsAvg: avg ? Math.round(((t.sessions_done - avg) / avg) * 100) : 0,
    }));
  });
  readonly average = computed(() => {
    const team = this.data().team;
    return team.length ? Math.round(team.reduce((s, t) => s + t.sessions_done, 0) / team.length) : 0;
  });

  toggle(id: number) {
    this.open.set(this.open() === id ? null : id);
  }

  pct(v: number | null): string {
    return v == null ? 'Sin datos' : `${Math.round(v)} %`;
  }
}
