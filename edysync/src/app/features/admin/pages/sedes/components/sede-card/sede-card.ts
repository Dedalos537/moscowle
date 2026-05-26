import { Component, Input, Output, EventEmitter } from '@angular/core';
import { Sede } from '../../../../../core/models/sede';

@Component({
  selector: 'app-sede-card',
  standalone: false,
  templateUrl: './sede-card.html',
  styleUrl: './sede-card.scss',
})
export class SedeCard {
  @Input({ required: true }) sede!: Sede;
  @Output() edit = new EventEmitter<Sede>();
  @Output() delete = new EventEmitter<Sede>();
  @Output() toggle = new EventEmitter<Sede>();
}
