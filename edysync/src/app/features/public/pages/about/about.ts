import { Component, OnInit, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-about',
  standalone: false,
  templateUrl: './about.html',
  styleUrl: './about.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class About implements OnInit {
  constructor(
    private headerService: HeaderService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Nosotros',
      subtitle: 'Conoce más sobre EduSync',
      icon: ['fas', 'info-circle'],
    });
  }
}
