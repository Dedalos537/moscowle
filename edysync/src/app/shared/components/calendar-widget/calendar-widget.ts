import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges, NgZone } from '@angular/core';

export interface CalendarWidgetEvent {
  id: number;
  title: string;
  date: Date;
  time?: string;
  endTime?: string;
  status: 'scheduled' | 'completed' | 'cancelled';
  therapist?: string;
  patient?: string;
  therapistId?: number;
  patientId?: number;
}

interface DayCell {
  date: Date;
  day: number;
  isToday: boolean;
  isCurrentMonth: boolean;
  isSelected: boolean;
  isInRange: boolean;
  isRangeStart: boolean;
  isRangeEnd: boolean;
  events: CalendarWidgetEvent[];
}

@Component({
  selector: 'app-calendar-widget',
  standalone: false,
  templateUrl: './calendar-widget.html',
  styleUrl: './calendar-widget.scss',
})
export class CalendarWidget implements OnInit, OnChanges {
  @Input() events: CalendarWidgetEvent[] = [];
  @Input() role: 'admin' | 'therapist' | 'patient' = 'admin';
  @Input() readonly = false;

  @Output() dayDblClick = new EventEmitter<Date>();
  @Output() rangeDblClick = new EventEmitter<{ start: Date; end: Date }>();
  @Output() eventClick = new EventEmitter<CalendarWidgetEvent>();

  currentMonth: Date = new Date();
  selectedDate: Date = new Date();
  rangeStart: Date | null = null;
  rangeEnd: Date | null = null;
  weeks: DayCell[][] = [];
  weekdays = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre'];

  private clickCount = 0;
  private clickTimer: any = null;
  private lastClickedKey = '';

  ngOnInit() {
    this.buildGrid();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['events'] && !changes['events'].firstChange) {
      this.buildGrid();
    }
  }

  get rangeLabel(): string {
    if (!this.rangeStart) return '';
    const fmt = (d: Date) => `${d.getDate()} ${this.months[d.getMonth()]}`;
    if (this.rangeEnd) {
      return `${fmt(this.rangeStart)} — ${fmt(this.rangeEnd)}`;
    }
    return `${fmt(this.rangeStart)} — ?`;
  }

  get isRangeSelected(): boolean {
    return this.rangeStart !== null && this.rangeEnd !== null;
  }



  private dateKey(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  private sameDay(a: Date, b: Date): boolean {
    return this.dateKey(a) === this.dateKey(b);
  }

  private isInDateRange(d: Date, start: Date, end: Date): boolean {
    const t = new Date(d).setHours(0, 0, 0, 0);
    const s = new Date(start).setHours(0, 0, 0, 0);
    const e = new Date(end).setHours(0, 0, 0, 0);
    return t >= Math.min(s, e) && t <= Math.max(s, e);
  }

  private buildGrid() {
    const year = this.currentMonth.getFullYear();
    const month = this.currentMonth.getMonth();

    const firstDay = new Date(year, month, 1);
    const startOfWeek = new Date(firstDay);
    startOfWeek.setDate(startOfWeek.getDate() - ((startOfWeek.getDay() + 6) % 7));

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const sel = new Date(this.selectedDate);
    sel.setHours(0, 0, 0, 0);

    const weeks: DayCell[][] = [];
    let cursor = new Date(startOfWeek);

    for (let w = 0; w < 6; w++) {
      const week: DayCell[] = [];
      for (let d = 0; d < 7; d++) {
        const dayStart = new Date(cursor);
        dayStart.setHours(0, 0, 0, 0);

        const dayEvents = this.events.filter((e) => {
          const ed = new Date(e.date);
          ed.setHours(0, 0, 0, 0);
          return ed.getTime() === dayStart.getTime();
        });

        const inRange = this.rangeStart && this.rangeEnd && this.isInDateRange(dayStart, this.rangeStart, this.rangeEnd);
        const isRs = this.rangeStart && this.sameDay(dayStart, this.rangeStart);
        const isRe = this.rangeEnd && this.sameDay(dayStart, this.rangeEnd);

        week.push({
          date: new Date(cursor),
          day: cursor.getDate(),
          isToday: dayStart.getTime() === today.getTime(),
          isCurrentMonth: cursor.getMonth() === month,
          isSelected: !this.isRangeSelected && dayStart.getTime() === sel.getTime(),
          isInRange: !!inRange,
          isRangeStart: !!isRs,
          isRangeEnd: !!isRe,
          events: dayEvents,
        });
        cursor.setDate(cursor.getDate() + 1);
      }
      weeks.push(week);
      if (cursor.getMonth() !== month && weeks.length >= 4) break;
    }

    this.weeks = weeks;
  }



  get monthLabel(): string {
    return `${this.months[this.currentMonth.getMonth()]} ${this.currentMonth.getFullYear()}`;
  }

  prevMonth() {
    this.currentMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() - 1, 1);
    this.buildGrid();
  }

  nextMonth() {
    this.currentMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + 1, 1);
    this.buildGrid();
  }

  today() {
    this.currentMonth = new Date();
    this.selectedDate = new Date();
    this.clearRange();
    this.buildGrid();
  }

  get todayButtonVisible(): boolean {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const cur = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth(), 1);
    cur.setHours(0, 0, 0, 0);
    return cur.getTime() !== today.getTime();
  }



  onDayClick(cell: DayCell, event: MouseEvent) {
    if (this.clickTimer) {
      clearTimeout(this.clickTimer);
      this.clickTimer = null;
    }

    const key = this.dateKey(cell.date);

    if (key === this.lastClickedKey) {
      this.clickCount++;
    } else {
      this.clickCount = 1;
      this.lastClickedKey = key;
    }

    if (this.clickCount >= 3) {
      this.clickCount = 0;
      this.lastClickedKey = '';
      this.clearAll();
      return;
    }

    if (this.clickCount === 2) {
      this.clickCount = 0;
      this.lastClickedKey = '';
      this.handleDblClick(cell);
      return;
    }

    const isModifier = event.metaKey || event.ctrlKey;
    this.clickTimer = setTimeout(() => {
      this.clickCount = 0;
      this.lastClickedKey = '';
      this.clickTimer = null;
      this.handleSingleClick(cell, isModifier);
    }, 300);
  }

  private handleSingleClick(cell: DayCell, isModifier: boolean) {
    if (isModifier) {
      if (!this.rangeStart) {
        this.rangeStart = new Date(cell.date);
        this.rangeEnd = null;
      } else {
        this.rangeEnd = new Date(cell.date);
        if (this.rangeStart && this.rangeEnd) {
          this.selectedDate = new Date(this.rangeStart);
        }
      }
      this.buildGrid();
      return;
    }

    this.clearRange();
    this.selectedDate = new Date(cell.date);
    if (!cell.isCurrentMonth) {
      this.currentMonth = new Date(cell.date.getFullYear(), cell.date.getMonth(), 1);
    }
    this.buildGrid();
  }

  private handleDblClick(cell: DayCell) {
    if (this.isRangeSelected) {
      this.rangeDblClick.emit({ start: this.rangeStart!, end: this.rangeEnd! });
    } else {
      this.selectedDate = new Date(cell.date);
      this.buildGrid();
      this.dayDblClick.emit(cell.date);
    }
  }

  private clearAll() {
    this.clearRange();
    this.selectedDate = new Date();
    this.currentMonth = new Date();
    this.buildGrid();
  }

  private clearRange() {
    this.rangeStart = null;
    this.rangeEnd = null;
  }



  get selectedDayEvents(): CalendarWidgetEvent[] {
    if (this.rangeStart && this.rangeEnd) {
      const s = new Date(this.rangeStart).setHours(0, 0, 0, 0);
      const e = new Date(this.rangeEnd).setHours(0, 0, 0, 0);
      return this.events.filter((ev) => {
        const ed = new Date(ev.date).setHours(0, 0, 0, 0);
        return ed >= Math.min(s, e) && ed <= Math.max(s, e);
      });
    }

    const sel = this.dateKey(this.selectedDate);
    return this.events.filter((ev) => this.dateKey(ev.date) === sel);
  }

  get selectedDateLabel(): string {
    if (this.isRangeSelected) {
      const fmt = (d: Date) => `${d.getDate()} de ${this.months[d.getMonth()]}`;
      return `${fmt(this.rangeStart!)} — ${fmt(this.rangeEnd!)}`;
    }
    const d = this.selectedDate;
    return `${d.getDate()} de ${this.months[d.getMonth()]}, ${d.getFullYear()}`;
  }

  get eventCount(): number {
    return this.selectedDayEvents.length;
  }



  get statusColor() {
    return (status: string) => {
      switch (status) {
        case 'completed': return 'bg-emerald-500';
        case 'cancelled': return 'bg-red-400';
        default: return 'bg-indigo-400';
      }
    };
  }

  get statusBgClass() {
    return (status: string) => {
      switch (status) {
        case 'completed': return 'bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300';
        case 'cancelled': return 'bg-red-100 dark:bg-red-500/15 text-red-700 dark:text-red-300';
        default: return 'bg-indigo-100 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300';
      }
    };
  }

  get statusLabel() {
    return (status: string) => {
      switch (status) {
        case 'completed': return 'Completada';
        case 'cancelled': return 'Cancelada';
        default: return 'Programada';
      }
    };
  }

  onEventClick(event: CalendarWidgetEvent) {
    if (this.readonly) return;
    this.eventClick.emit(event);
  }

  formatMonthRange(start: Date, end: Date): string {
    const s = `${start.getDate()} ${this.months[start.getMonth()]}`;
    const e = `${end.getDate()} ${this.months[end.getMonth()]}`;
    return `${s} — ${e}`;
  }
}
