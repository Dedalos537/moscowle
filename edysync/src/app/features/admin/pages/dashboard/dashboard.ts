import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-dashboard',
  standalone: false,
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  summary: any = null;
  porSede: Record<string, any> = {};

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.http.get<any>('/api/admin/list-users').subscribe({
      next: (res) => {
        if (res && res.success && res.users) {
          const arr = res.users;
          // Construimos el summary según tu requerimiento de conteo local
          this.summary = {
            therapists: arr.filter((u:any) => u.role === 'terapista').length,
            patients: arr.filter((u:any) => u.role === 'jugador').length,
            sessions_total: '-', // Pendiente si hay otra fuente
            avg_accuracy: '-'   // Pendiente si hay otra fuente
          };
        }
      },
      error: (err) => console.error('Error al obtener lista completa de usuarios:', err)
    });
  }
}
