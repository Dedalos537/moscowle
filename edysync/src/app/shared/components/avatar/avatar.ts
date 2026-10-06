import { Component, ChangeDetectionStrategy, computed, effect, inject, input, signal } from '@angular/core';
import { AvatarService } from '../../../core/services/avatar.service';

@Component({
  selector: 'app-avatar',
  standalone: true,
  imports: [],
  templateUrl: './avatar.html',
  styleUrl: './avatar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Avatar {
  /** URL de la foto devuelta por el backend (`/api/profile/avatar/<id>?v=…`); sin ella se muestran las iniciales. */
  src = input<string | null | undefined>(null);
  name = input('');
  size = input<'sm' | 'md' | 'lg' | 'xl'>('md');

  url = signal<string | null>(null);
  initials = computed(() => {
    const parts = this.name().trim().split(/\s+/).filter(Boolean);
    return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase() || '?';
  });

  private svc = inject(AvatarService);

  constructor() {
    effect((onCleanup) => {
      const sub = this.svc.blobUrl(this.src()).subscribe((u) => this.url.set(u));
      onCleanup(() => sub.unsubscribe());
    });
  }
}
