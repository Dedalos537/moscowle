import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { Dashboard } from './pages/dashboard/dashboard';
import { EdysyncDashboard } from './pages/edysync-dashboard/edysync-dashboard';
import { Sedes } from './pages/sedes/sedes';
import { AdminLayout } from '../../core/layout/admin-layout/admin-layout';

const routes: Routes = [
  { 
    path: '', 
    component: AdminLayout,
    children: [
      { path: 'dashboard', component: Dashboard },
      { path: 'edysync', component: EdysyncDashboard },
      { path: 'sedes', component: Sedes },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AdminRoutingModule { }
