import {
  Component,
  inject,
  input,
  output,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { DragDropModule, CdkDragDrop, moveItemInArray } from '@angular/cdk/drag-drop';
import { KanbanTaskCardComponent } from '../kanban-task-card/kanban-task-card';
import { KanbanService, KanbanTask } from '../../../../core/services/kanban.service';
import { KanbanColumn } from '../kanban-board/kanban-board';

@Component({
  selector: 'app-kanban-column',
  standalone: true,
  imports: [CommonModule, DragDropModule, KanbanTaskCardComponent],
  templateUrl: './kanban-column.html',
  styleUrl: './kanban-column.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KanbanColumnComponent {
  column = input.required<KanbanColumn>();
  viewMode = input<'admin' | 'therapist' | 'patient'>('admin');
  connectedLists = input<string[]>([]);

  taskMoved = output<void>();
  taskExtended = output<void>();
  taskDeleted = output<void>();
  taskEdited = output<void>();
  taskClicked = output<KanbanTask>();

  private kanbanService = inject(KanbanService);

  onDrop(event: CdkDragDrop<KanbanTask[]>) {
    if (event.previousContainer === event.container) {
      const tasks = event.container.data;
      moveItemInArray(tasks, event.previousIndex, event.currentIndex);
      tasks.forEach((t, i) => (t.position = i));
      tasks.forEach((t) =>
        this.kanbanService.updateTask(t.id, { position: t.position }).subscribe()
      );
    } else {
      const task = event.previousContainer.data[event.previousIndex];
      event.previousContainer.data.splice(event.previousIndex, 1);
      event.container.data.splice(event.currentIndex, 0, task);
      task.column = event.container.id as KanbanTask['column'];
      event.container.data.forEach((t, i) => (t.position = i));
      this.kanbanService
        .updateTask(task.id, { column: task.column, position: task.position })
        .subscribe();
    }
    this.taskMoved.emit();
  }
}
