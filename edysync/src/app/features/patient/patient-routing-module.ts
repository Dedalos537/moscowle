import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { RoleGuard } from '../../core/guards/role.guard';
import { PatientLayout } from '../../core/layout/patient-layout/patient-layout';
import { PatientDashboard } from './pages/dashboard/dashboard';
import { PatientSessions } from './pages/sessions/sessions';
import { PatientPayments } from './pages/payments/payments';
import { PatientProgressPage } from './pages/progress/progress';
import { PatientCalendar } from './pages/calendar/calendar';
import { ChatComponent } from '../../shared/components/chat/chat.component';
import { PatientProfile } from './pages/profile/profile';
import { PatientMyTherapist } from './pages/my-therapist/my-therapist';

const routes: Routes = [
  {
    path: '',
    component: PatientLayout,
    canActivate: [RoleGuard],
    data: { role: 'jugador' },
    children: [
      { path: 'dashboard', component: PatientDashboard },
      { path: 'sessions', component: PatientSessions },
      { path: 'payments', component: PatientPayments },
      { path: 'progress', component: PatientProgressPage },
      { path: 'calendar', component: PatientCalendar },
      { path: 'messages', component: ChatComponent },
      { path: 'profile', component: PatientProfile },
      { path: 'my-therapist', component: PatientMyTherapist },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
    ],
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class PatientRoutingModule {}
