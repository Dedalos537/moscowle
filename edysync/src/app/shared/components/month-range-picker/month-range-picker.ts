import { Component, input, output, ChangeDetectionStrategy, ChangeDetectorRef, HostListener, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';

export interface MonthRange {
  start: string;
  end: string;
  mode: 'single' | 'range';
}

const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

@Component({
  selector: 'app-month-range-picker',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule],
  templateUrl: './month-range-picker.html',
  styleUrl: './month-range-picker.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MonthRangePicker {
  value = input<MonthRange | null>(null);
  minYear = input<number>(new Date().getFullYear());
  label = input<string>('Período');

  valueChange = output<MonthRange | null>();

  isOpen = false;
  year = new Date().getFullYear();
  allowRange = false;
  pendingStart: string | null = null;

  readonly months = MONTHS;
  readonly monthKeys = MONTHS.map((_, i) => String(i + 1).padStart(2, '0'));

  constructor(private cdr: ChangeDetectorRef, private elementRef: ElementRef) {}

  get currentYear(): number {
    return new Date().getFullYear();
  }

  get currentMonthKey(): string {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  }

  get selectedLabel(): string {
    const v = this.value();
    if (!v) return 'Seleccionar período';
    return v.mode === 'range' && v.start && v.end && v.start !== v.end
      ? `${this.fmt(v.start)} – ${this.fmt(v.end)}`
      : this.fmt(v.start);
  }

  private fmt(key: string): string {
    if (!key) return '—';
    const [y, m] = key.split('-').map(Number);
    return `${MONTHS[(m || 1) - 1]} ${y}`;
  }

  toggle() {
    this.isOpen = !this.isOpen;
    if (this.isOpen) this.year = this.currentYear;
    this.cdr.markForCheck();
  }

  prevYear() {
    if (this.year <= this.minYear()) return;
    this.year--;
    this.cdr.markForCheck();
  }

  nextYear() {
    this.year++;
    this.cdr.markForCheck();
  }

  canPrev(): boolean {
    return this.year > this.minYear();
  }

  isSelected(displayYear: number, monthIndex: number): boolean {
    const key = this.keyOf(displayYear, monthIndex);
    const v = this.value();
    if (!v) return false;
    if (v.start === key || v.end === key) return true;
    if (v.mode === 'range' && v.start && v.end && key >= v.start && key <= v.end) return true;
    return false;
  }

  isStart(displayYear: number, monthIndex: number): boolean {
    return this.value()?.start === this.keyOf(displayYear, monthIndex);
  }

  isEnd(displayYear: number, monthIndex: number): boolean {
    return this.value()?.end === this.keyOf(displayYear, monthIndex);
  }

  isPreview(displayYear: number, monthIndex: number): boolean {
    if (!this.allowRange || !this.pendingStart) return false;
    const key = this.keyOf(displayYear, monthIndex);
    const pStart = this.pendingStart;
    if (key < pStart) return false;
    const [py] = pStart.split('-').map(Number);
    if (displayYear > py && displayYear <= this.year) return true;
    if (displayYear === py && key >= pStart) return true;
    return false;
  }

  select(monthIndex: number) {
    const key = this.keyOf(this.year, monthIndex);

    if (!this.allowRange) {
      this.pendingStart = null;
      this.emit({ start: key, end: key, mode: 'single' });
      this.isOpen = false;
      this.cdr.markForCheck();
      return;
    }

    if (!this.pendingStart || this.pendingStart === key) {
      this.pendingStart = key;
      this.emit({ start: key, end: key, mode: 'range' });
      this.cdr.markForCheck();
      return;
    }

    const start = key < this.pendingStart ? key : this.pendingStart;
    const end = key < this.pendingStart ? this.pendingStart : key;
    this.pendingStart = null;
    this.emit({ start, end, mode: 'range' });
    this.isOpen = false;
    this.cdr.markForCheck();
  }

  toggleRangeMode() {
    this.allowRange = !this.allowRange;
    this.pendingStart = null;
    if (!this.allowRange) {
      const v = this.value();
      if (v && v.mode === 'range' && v.start) {
        this.emit({ start: v.start, end: v.start, mode: 'single' });
      }
    }
    this.cdr.markForCheck();
  }

  clear(event?: Event) {
    event?.stopPropagation();
    this.pendingStart = null;
    if (this.allowRange) this.allowRange = false;
    this.emit(null);
    this.cdr.markForCheck();
  }

  private keyOf(displayYear: number, monthIndex: number): string {
    return `${displayYear}-${this.monthKeys[monthIndex]}`;
  }

  private emit(value: MonthRange | null) {
    this.valueChange.emit(value);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event) {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isOpen = false;
      this.cdr.markForCheck();
    }
  }
}
