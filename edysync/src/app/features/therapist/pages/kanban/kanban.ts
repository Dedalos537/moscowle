import { Component } from '@angular/core';
import { KanbanBoardComponent } from '../../../../shared/components/kanban/kanban-board/kanban-board';

@Component({
  selector: 'app-therapist-kanban',
  standalone: true,
  imports: [KanbanBoardComponent],
  template: `<app-kanban-board viewMode="therapist"></app-kanban-board>`,
})
export class KanbanPage {}
