import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Sede } from '../../../../../../core/models/sede';

@Component({
  selector: 'app-sede-card',
  standalone: false,
  templateUrl: './sede-card.html',
  styleUrl: './sede-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SedeCard {
  @Input({ required: true }) sede!: Sede;
  @Output() edit = new EventEmitter<Sede>();
  @Output() delete = new EventEmitter<Sede>();
  @Output() toggle = new EventEmitter<Sede>();

  constructor(private cdr: ChangeDetectorRef) {}
}
