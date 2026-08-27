import { Component } from '@angular/core';
import { KanbanBoardComponent } from '../../../../shared/components/kanban/kanban-board/kanban-board';

@Component({
  selector: 'app-admin-kanban',
  standalone: true,
  imports: [KanbanBoardComponent],
  template: `<app-kanban-board viewMode="admin"></app-kanban-board>`,
})
export class KanbanPage {}
