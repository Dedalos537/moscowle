import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-sedes',
  standalone: false,
  templateUrl: './sedes.html',
  styleUrl: './sedes.scss',
})
export class Sedes implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  sedes = [
    {
      id: 1,
      name: 'Talara',
      address: 'Sin dirección',
      active: true,
      stats: {
        patients: { total: 45 },
        sessions: { total_completed: 120 },
        payments: { total_revenue: 3500.00 }
      }
    },
    {
      id: 2,
      name: 'Piura',
      address: 'Jr. Vicús 311',
      active: true,
      stats: {
        patients: { total: 80 },
        sessions: { total_completed: 250 },
        payments: { total_revenue: 7200.00 }
      }
    }
  ];

  constructor(private headerService: HeaderService) {}

  get activeCount(): number {
    return this.sedes.filter(s => s.active).length;
  }

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Sedes',
      subtitle: 'Administra y analiza tus puntos de atención',
      icon: ['fas', 'map-marker-alt'],
      actionTemplate: this.headerActions
    });
  }

  ngOnDestroy() {
    this.headerService.reset();
  }
}
