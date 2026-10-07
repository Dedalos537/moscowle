import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { KanbanBoardComponent } from '../../../../shared/components/kanban/kanban-board/kanban-board';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-admin-kanban',
  standalone: true,
  imports: [KanbanBoardComponent],
  template: `<app-kanban-board viewMode="admin"></app-kanban-board>`,
})
export class KanbanPage implements OnInit, OnDestroy {
  private headerService = inject(HeaderService);

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Tablero de tareas',
      subtitle: 'Asigna y da seguimiento a las tareas del equipo',
      icon: ['fas', 'table-columns'],
    });
  }

  ngOnDestroy() {
    this.headerService.reset();
  }
}
