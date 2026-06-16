import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { Toast, ToastType } from '../models/toast';

const MAX_VISIBLE = 5;

@Injectable({ providedIn: 'root' })
export class ToastService {
  private toasts: Toast[] = [];
  private toastsSubject = new Subject<Toast[]>();
  toasts$ = this.toastsSubject.asObservable();
  private nextId = 1;

  show(message: string, type: ToastType = 'info', duration = 4000): number {
    const id = this.nextId++;
    const toast: Toast = { id, message, type, duration };
    this.toasts = [...this.toasts, toast];
    if (this.toasts.length > MAX_VISIBLE) {
      this.toasts = this.toasts.slice(this.toasts.length - MAX_VISIBLE);
    }
    this.toastsSubject.next(this.toasts);
    if (duration > 0) {
      setTimeout(() => this.remove(id), duration);
    }
    return id;
  }

  remove(id: number): void {
    this.toasts = this.toasts.filter(t => t.id !== id);
    this.toastsSubject.next(this.toasts);
  }

  clear(): void {
    this.toasts = [];
    this.toastsSubject.next(this.toasts);
  }
}
