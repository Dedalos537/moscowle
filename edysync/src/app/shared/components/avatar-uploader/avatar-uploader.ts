import { Component, ChangeDetectionStrategy, ChangeDetectorRef, OnDestroy, OnInit, inject } from '@angular/core';
import { Subscription } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmService } from '../../../core/services/confirm.service';
import { Avatar } from '../avatar/avatar';

const MAX_BYTES = 5 * 1024 * 1024;
const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp'];

@Component({
  selector: 'app-avatar-uploader',
  standalone: true,
  imports: [Avatar],
  templateUrl: './avatar-uploader.html',
  styleUrl: './avatar-uploader.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AvatarUploader implements OnInit, OnDestroy {
  user: { username?: string; avatar?: string | null } | null = null;
  busy = false;
  error = '';

  private auth = inject(AuthService);
  private toast = inject(ToastService);
  private confirm = inject(ConfirmService);
  private cdr = inject(ChangeDetectorRef);
  private sub?: Subscription;

  ngOnInit() {
    this.sub = this.auth.currentUser$.subscribe((u) => {
      this.user = u;
      this.cdr.markForCheck();
    });
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
  }

  onFile(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.error = '';
    if (!ACCEPTED.includes(file.type)) {
      this.error = 'Usa una imagen JPG, PNG o WebP.';
      return;
    }
    if (file.size > MAX_BYTES) {
      this.error = 'La imagen supera los 5 MB. Elige una más liviana.';
      return;
    }
    this.busy = true;
    this.auth.uploadAvatar(file).subscribe({
      next: () => { this.busy = false; this.toast.show('Foto de perfil actualizada', 'success'); this.cdr.markForCheck(); },
      error: (err) => { this.busy = false; this.error = err?.error?.message || 'No se pudo subir la foto. Inténtalo de nuevo.'; this.cdr.markForCheck(); },
    });
  }

  remove() {
    this.confirm
      .confirm({ title: 'Quitar foto de perfil', message: 'Volverás a mostrar tus iniciales.', confirmText: 'Quitar', variant: 'warning' })
      .subscribe((ok) => {
        if (!ok) return;
        this.busy = true;
        this.auth.removeAvatar().subscribe({
          next: () => { this.busy = false; this.toast.show('Foto quitada', 'success'); this.cdr.markForCheck(); },
          error: () => { this.busy = false; this.error = 'No se pudo quitar la foto.'; this.cdr.markForCheck(); },
        });
      });
  }
}
