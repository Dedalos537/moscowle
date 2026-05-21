// DCE — Diego Centeno Estuvo Acá
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-sede-card',
  standalone: false,
  templateUrl: './sede-card.html',
  styleUrl: './sede-card.scss',
})
export class SedeCard {
  @Input() sede: any;
}
