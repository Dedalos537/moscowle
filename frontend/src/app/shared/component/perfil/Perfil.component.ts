import { Component, OnInit, AfterViewInit, ViewEncapsulation } from '@angular/core';
import { UiEventService } from '../../services/ui-event.service';
import { Router } from '@angular/router';
import flatpickr from 'flatpickr';

@Component({
  selector: 'app-perfil',
  templateUrl: './perfil.component.html',
  styleUrls: ['./perfil.component.css', '../LMS/cursos.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class PerfilComponent implements OnInit, AfterViewInit {
  today: Date = new Date();
  currentMonth: number = this.today.getMonth();
  currentYear: number = this.today.getFullYear();

  events: { date: string; event: string; color: string }[] = [
    { date: '2024-10-27', event: 'Tarea 3', color: 'green' },
    { date: '2024-10-30', event: 'Tarea 2', color: 'blue' }
  ];

  constructor(private router: Router, private uiEventService: UiEventService) {}

  ngOnInit(): void {
    this.uiEventService.setupEventListeners();
  }

  irPerfil() {
    this.router.navigate(['/perfil']);
  }

  logout(): void {
    localStorage.removeItem('authToken'); // si usas tokens
    this.router.navigate(['/home']);
  }

  
  ngAfterViewInit(): void {
    this.generateCalendar(this.currentMonth, this.currentYear);

    const prevButton = document.getElementById('prev');
    const nextButton = document.getElementById('next');

    prevButton?.addEventListener('click', () => {
      this.currentMonth--;
      if (this.currentMonth < 0) {
        this.currentMonth = 11;
        this.currentYear--;
      }
      this.generateCalendar(this.currentMonth, this.currentYear);
    });

    nextButton?.addEventListener('click', () => {
      this.currentMonth++;
      if (this.currentMonth > 11) {
        this.currentMonth = 0;
        this.currentYear++;
      }
      this.generateCalendar(this.currentMonth, this.currentYear);
    });
  }

  generateCalendar(month: number, year: number): void {
    const calendarContainer = document.getElementById('dates');
    const monthYear = document.getElementById('monthYear');

    if (!calendarContainer || !monthYear) return;

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    calendarContainer.innerHTML = '';

    monthYear.textContent = new Date(year, month).toLocaleString('es-ES', {
      month: 'long',
      year: 'numeric'
    });

    for (let i = 0; i < (firstDay + 6) % 7; i++) {
      const blank = document.createElement('div');
      blank.classList.add('date');
      calendarContainer.appendChild(blank);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(year, month, day);
      const dayElement = document.createElement('div');
      dayElement.classList.add('date');
      dayElement.textContent = day.toString();

      if (
        day === this.today.getDate() &&
        month === this.today.getMonth() &&
        year === this.today.getFullYear()
      ) {
        dayElement.classList.add('today');
      }

      const event = this.events.find(
        e => e.date === date.toISOString().slice(0, 10)
      );
      if (event) {
        const eventElement = document.createElement('div');
        eventElement.classList.add('event');
        eventElement.textContent = event.event;
        eventElement.style.backgroundColor = event.color;
        dayElement.appendChild(eventElement);
      }

      calendarContainer.appendChild(dayElement);
    }
  }
}
