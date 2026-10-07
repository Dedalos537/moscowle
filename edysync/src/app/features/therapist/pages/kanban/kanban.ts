import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { KanbanBoardComponent } from '../../../../shared/components/kanban/kanban-board/kanban-board';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-therapist-kanban',
  standalone: true,
  imports: [KanbanBoardComponent],
  template: `<app-kanban-board viewMode="therapist"></app-kanban-board>`,
})
export class KanbanPage implements OnInit, OnDestroy {
  private headerService = inject(HeaderService);

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Tablero de tareas',
      subtitle: 'Tus tareas y las que asignas a tus pacientes',
      icon: ['fas', 'table-columns'],
    });
  }

  ngOnDestroy() {
    this.headerService.reset();
  }
}
