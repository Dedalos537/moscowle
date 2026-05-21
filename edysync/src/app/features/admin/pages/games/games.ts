// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-games',
  standalone: false,
  templateUrl: './games.html',
  styleUrl: './games.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class Games implements OnInit {
  games: string[] = [];
  loading = false;
  uploading = false;
  showUploadModal = false;
  uploadName = '';
  selectedFile: File | null = null;
  deleteName: string | null = null;
  statusText = '';

  constructor(private admin: AdminService) {}

  ngOnInit() {
    this.loadGames();
  }

  loadGames() {
    this.loading = true;
    this.admin.getGames().subscribe({
      next: (res) => { this.games = res.games; this.loading = false; },
      error: () => { this.loading = false; }
    });
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
    this.admin.uploadGame(this.uploadName, this.selectedFile).subscribe({
      next: () => { this.uploading = false; this.statusText = 'Juego subido correctamente'; this.closeUploadModal(); this.loadGames(); },
      error: () => { this.uploading = false; this.statusText = 'Error al subir el juego'; }
    });
  }

  confirmDelete(name: string) { this.deleteName = name; }

  cancelDelete() { this.deleteName = null; }

  deleteGame() {
    if (!this.deleteName) return;
    this.admin.deleteGame(this.deleteName).subscribe({
      next: () => { this.deleteName = null; this.loadGames(); },
      error: () => { this.deleteName = null; }
    });
  }

  getGameUrl(filename: string): string {
    return `/static/games/${filename}`;
  }
}
