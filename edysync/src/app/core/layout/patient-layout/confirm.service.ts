import { Injectable } from '@angular/core';
import { Observable, BehaviorSubject } from 'rxjs';

export interface ConfirmOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'primary';
  icon?: any;
}

export interface ConfirmState {
  visible: boolean;
  options: ConfirmOptions;
  resolve?: (value: boolean) => void;
}

const DEFAULT_STATE: ConfirmState = { visible: false, options: {} as ConfirmOptions };

@Injectable({ providedIn: 'root' })
export class ConfirmService {
  private stateSubject = new BehaviorSubject<ConfirmState>(DEFAULT_STATE);
  state$ = this.stateSubject.asObservable();

  confirm(options: ConfirmOptions): Observable<boolean> {
    return new Observable(subscriber => {
      this.stateSubject.next({
        visible: true,
        options: {
          confirmText: 'Confirmar',
          cancelText: 'Cancelar',
          variant: 'danger',
          icon: ['fas', 'exclamation-triangle'],
          ...options,
        },
        resolve: (result: boolean) => {
          subscriber.next(result);
          subscriber.complete();
        },
      });
    });
  }

  close(result: boolean) {
    const current = this.stateSubject.value;
    if (current?.resolve) {
      current.resolve(result);
    }
    this.stateSubject.next({ visible: false, options: {} as ConfirmOptions });
  }
}
