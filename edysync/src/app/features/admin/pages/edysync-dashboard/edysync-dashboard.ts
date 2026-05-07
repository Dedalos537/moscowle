import { Component } from '@angular/core';

@Component({
  selector: 'app-edysync-dashboard',
  standalone: false,
  templateUrl: './edysync-dashboard.html',
  styleUrl: './edysync-dashboard.scss',
})
export class EdysyncDashboard {
  summary: any = null;

  ngOnInit() {
    this.summary = {
      therapists: 15,
      patients: 120,
      sessions_total: 142,
      avg_accuracy: 94
    };
  }
}
