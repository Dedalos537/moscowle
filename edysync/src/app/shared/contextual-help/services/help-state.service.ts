import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class HelpStateService {
  panelOpen = signal(false);

  toggle(): void {
    this.panelOpen.update(v => !v);
  }

  open(): void {
    this.panelOpen.set(true);
  }

  close(): void {
    this.panelOpen.set(false);
  }
}
