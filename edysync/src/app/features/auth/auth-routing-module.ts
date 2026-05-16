import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { Login } from './pages/login/login';
import { ResetPassword } from './pages/reset-password/reset-password';

const routes: Routes = [
  { path: 'login', component: Login },
  { path: 'reset-password', component: ResetPassword },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AuthRoutingModule { }
