import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AuthRoutingModule } from './auth-routing-module';
import { SharedModule } from '../../shared/shared-module';
import { Login } from './pages/login/login';
import { ResetPassword } from './pages/reset-password/reset-password';


@NgModule({
  declarations: [
    Login,
    ResetPassword,
  ],
  imports: [
    CommonModule,
    FormsModule,
    AuthRoutingModule,
    SharedModule,
  ],
})
export class AuthModule { }
