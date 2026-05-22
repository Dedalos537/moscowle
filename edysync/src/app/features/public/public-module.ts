import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { PublicRoutingModule } from './public-routing-module';
import { SharedModule } from '../../shared/shared-module';

import { Home } from './pages/home/home';
import { About } from './pages/about/about';
import { Contact } from './pages/contact/contact';

@NgModule({
  declarations: [
    Home,
    About,
    Contact
  ],
  imports: [
    CommonModule,
    FormsModule,
    PublicRoutingModule,
    SharedModule
  ]
})
export class PublicModule { }
