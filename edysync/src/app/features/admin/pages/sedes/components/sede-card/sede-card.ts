import { Component, input, output, ChangeDetectionStrategy } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Sede } from '../../../../../../core/models/sede';

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
  edit = output<Sede>();
  delete = output<Sede>();
  toggle = output<Sede>();
}
