import { Injectable, signal, computed, DestroyRef, inject } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter, map } from 'rxjs/operators';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AuthService } from '../../../core/services/auth.service';
import { UserRole } from '../../../core/models/user';

export interface DetectedContext {
  role: UserRole | null;
  route: string;
  tab: string | null;
}

@Injectable({ providedIn: 'root' })
export class ContextDetectorService {
  private router = inject(Router);
  private authService = inject(AuthService);
  private destroyRef = inject(DestroyRef);

  private role = signal<UserRole | null>(null);
  private route = signal<string>('');
  private tab = signal<string | null>(null);

  context = computed<DetectedContext>(() => ({
    role: this.role(),
    route: this.route(),
    tab: this.tab(),
  }));

  constructor() {
    this.authService.currentUser$.pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe(user => {
      this.role.set(user?.role ?? null);
    });

    this.router.events.pipe(
      filter(e => e instanceof NavigationEnd),
      map(e => e as NavigationEnd),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe(e => {
      const url = new URL(e.urlAfterRedirects, window.location.origin);
      this.route.set(url.pathname);
      this.tab.set(url.searchParams.get('tab'));
    });
  }
}
