import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { KanbanBoardComponent } from '../../../../shared/components/kanban/kanban-board/kanban-board';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-patient-kanban',
  standalone: true,
  imports: [KanbanBoardComponent],
  template: `<app-kanban-board viewMode="patient"></app-kanban-board>`,
})
export class KanbanPage implements OnInit, OnDestroy {
  private headerService = inject(HeaderService);

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mis tareas',
      subtitle: 'Lo que tienes pendiente y lo que ya terminaste',
      icon: ['fas', 'table-columns'],
    });
  }

  ngOnDestroy() {
    this.headerService.reset();
  }
}
