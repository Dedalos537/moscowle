import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class SidebarService {
  private openSubject = new BehaviorSubject<boolean>(false);
  open$ = this.openSubject.asObservable();

  /** Mobile: overlay open/close */
  toggle() {
    this.openSubject.next(!this.openSubject.value);
  }

  open() {
    this.openSubject.next(true);
  }

  close() {
    this.openSubject.next(false);
  }
}
