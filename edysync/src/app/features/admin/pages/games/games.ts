import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Modal } from '../../../../shared/components/modal/modal';
import { Input } from '../../../../shared/components/input/input';
import { Alert } from '../../../../shared/components/alert/alert';

@Component({
  selector: 'app-games',
  standalone: true,
  templateUrl: './games.html',
  styleUrl: './games.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  imports: [CommonModule, FontAwesomeModule, Button, Spinner, Modal, Input, Alert],
})
export class Games implements OnInit, OnDestroy {
  games: string[] = [];
  loading = false;
  uploading = false;
  showUploadModal = false;
  uploadName = '';
  selectedFile: File | null = null;
  deleteName: string | null = null;
  statusText = '';
  private subscriptions: Subscription = new Subscription();

  constructor(private admin: AdminService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadGames();
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
  }

  loadGames() {
    this.loading = true;
    this.subscriptions.add(
      this.admin.getGames().subscribe({
        next: (res) => { this.games = res.games; this.loading = false; this.cdr.markForCheck(); },
        error: () => { this.loading = false; this.cdr.markForCheck(); }
      })
    );
  }

  openUploadModal() { this.showUploadModal = true; this.uploadName = ''; this.selectedFile = null; }

  closeUploadModal() { this.showUploadModal = false; }

  onFileSelected(event: any) {
    this.selectedFile = event.target.files[0] || null;
    if (this.selectedFile && !this.uploadName) {
      this.uploadName = this.selectedFile.name.replace('.html', '');
    }
  }

  uploadGame() {
    if (!this.uploadName || !this.selectedFile) return;
    this.uploading = true;
    this.statusText = '';
    this.subscriptions.add(
      this.admin.uploadGame(this.uploadName, this.selectedFile).subscribe({
        next: () => { this.uploading = false; this.statusText = 'Juego subido correctamente'; this.closeUploadModal(); this.loadGames(); this.cdr.markForCheck(); },
        error: () => { this.uploading = false; this.statusText = 'Error al subir el juego'; this.cdr.markForCheck(); }
      })
    );
  }

  confirmDelete(name: string) { this.deleteName = name; }

  cancelDelete() { this.deleteName = null; }

  deleteGame() {
    if (!this.deleteName) return;
    this.subscriptions.add(
      this.admin.deleteGame(this.deleteName).subscribe({
        next: () => { this.deleteName = null; this.loadGames(); this.cdr.markForCheck(); },
        error: () => { this.deleteName = null; this.cdr.markForCheck(); }
      })
    );
  }

  getGameUrl(filename: string): string {
    return `/static/games/${filename}`;
  }
}
