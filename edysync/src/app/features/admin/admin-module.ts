import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { AdminRoutingModule } from './admin-routing-module';
import { SharedModule } from '../../shared/shared-module';
import { Dashboard } from './pages/dashboard/dashboard';
import { EdysyncDashboard } from './pages/edysync-dashboard/edysync-dashboard';
import { Sedes } from './pages/sedes/sedes';
import { SedeCard } from './pages/sedes/components/sede-card/sede-card';

@NgModule({
  declarations: [
    Dashboard,
    EdysyncDashboard,
    Sedes,
    SedeCard
  ],
  imports: [
    CommonModule,
    AdminRoutingModule,
    SharedModule
  ]
})
export class AdminModule { }
