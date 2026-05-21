// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit, OnDestroy } from '@angular/core';
import { RecordingService } from './core/services/recording.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.html',
  standalone: false,
  styleUrl: './app.scss'
})
export class App implements OnInit, OnDestroy {
  constructor(private recordingService: RecordingService) {}

  ngOnInit() {
    this.recordingService.iniciarPolleo();
  }

  ngOnDestroy() {
    this.recordingService.detenerPolleo();
  }
}
