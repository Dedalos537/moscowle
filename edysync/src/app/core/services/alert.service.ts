// DCE — Diego Centeno Estuvo Acá
import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

export interface AlertConfig {
  type: 'info' | 'success' | 'error' | 'warning';
  title?: string;
  message: string;
  isHelp?: boolean;
  helpTitle?: string;
  helpContent?: string;
}

@Injectable({ providedIn: 'root' })
export class AlertService {
  private stateSubject = new Subject<{ visible: boolean; config: AlertConfig | null }>();
  state$ = this.stateSubject.asObservable();

  show(message: string, type: AlertConfig['type'] = 'info') {
    this.stateSubject.next({ visible: true, config: { type, message } });
  }

  showHelp(title: string, content: string) {
    this.stateSubject.next({
      visible: true,
      config: { type: 'info', title, message: '', isHelp: true, helpTitle: title, helpContent: content },
    });
  }

  close() {
    this.stateSubject.next({ visible: false, config: null });
  }
}
