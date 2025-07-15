import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink, RouterModule } from '@angular/router';

@Component({
  selector: 'app-about',
  imports: [CommonModule, RouterModule, RouterLink],
  templateUrl: './about.html',
  styleUrl: './about.css'
})
export class About {

}
