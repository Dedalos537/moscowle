import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class WakeLockService implements OnDestroy {
  private wakeLock: WakeLockSentinel | null = null;
  private isSupported = 'wakeLock' in navigator;
  private isActiveSubject = new BehaviorSubject<boolean>(false);
  isActive$ = this.isActiveSubject.asObservable();

  async request(): Promise<boolean> {
    if (!this.isSupported) {
      console.warn('Screen Wake Lock API not supported');
      return false;
    }

    try {
      this.wakeLock = await navigator.wakeLock.request('screen');
      this.isActiveSubject.next(true);

      this.wakeLock.addEventListener('release', () => {
        this.isActiveSubject.next(false);
      });

      document.addEventListener('visibilitychange', this.onVisibilityChange);
      return true;
    } catch (err) {
      console.warn('Wake Lock request failed:', err);
      return false;
    }
  }

  async release(): Promise<void> {
    if (this.wakeLock) {
      try {
        await this.wakeLock.release();
      } catch {}
      this.wakeLock = null;
      this.isActiveSubject.next(false);
      document.removeEventListener('visibilitychange', this.onVisibilityChange);
    }
  }

  private onVisibilityChange = async (): Promise<void> => {
    if (document.visibilityState === 'visible' && this.isActiveSubject.value === false) {
      await this.request();
    }
  };

  ngOnDestroy(): void {
    this.release();
  }
}
