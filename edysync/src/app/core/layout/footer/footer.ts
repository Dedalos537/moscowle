// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-footer',
  standalone: false,
  templateUrl: './footer.html',
  styleUrl: './footer.scss',
})
export class Footer implements OnInit {
  currentYear: number = 0;

  ngOnInit() {
    // Calculado dinámicamente desde Angular, reemplaza a {{ currentYear }} de Flask
    this.currentYear = new Date().getFullYear();
  }
}
