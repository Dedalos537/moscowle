import { Component, OnInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-about',
  standalone: false,
  templateUrl: './about.html',
  styleUrl: './about.scss',
})
export class About implements OnInit {
  constructor(private headerService: HeaderService) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Nosotros',
      subtitle: 'Conoce más sobre EduSync',
      icon: ['fas', 'info-circle'],
    });
  }
}
