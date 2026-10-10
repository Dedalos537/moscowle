import { TherapistDashboard } from './pages/dashboard/dashboard';
import { NgModule, inject } from '@angular/core';
import { Router, RouterModule, Routes } from '@angular/router';
import { RoleGuard } from '../../core/guards/role.guard';
import { TherapistLayout } from '../../core/layout/therapist-layout/therapist-layout';
import { TherapistSessions } from './pages/sessions/therapist-sessions';
import { TherapistSessionReview } from './pages/session-review/session-review';
import { ChatComponent } from '../../shared/components/chat/chat.component';
import { TherapistProfile } from './pages/profile/therapist-profile';
import { TherapistGames } from './pages/games/therapist-games';
import { TherapistPatients } from './pages/patients/patients';
import { TherapistPatientDetail } from './pages/patient-detail/patient-detail';
import { TherapistReports } from './pages/reports/reports';
import { IncidentsList } from '../../shared/components/incidents-list/incidents-list';

const routes: Routes = [
  {
    path: '',
    component: TherapistLayout,
    canActivate: [RoleGuard],
    data: { role: 'terapista' },
    children: [
      { path: 'dashboard', component: TherapistDashboard },
      { path: 'sessions', component: TherapistSessions },
      { path: 'sessions/:id/review', component: TherapistSessionReview },
      { path: 'messages', component: ChatComponent },
      { path: 'profile', component: TherapistProfile },
      { path: 'games', component: TherapistGames },
      { path: 'patients', component: TherapistPatients },
      { path: 'patients/:id', component: TherapistPatientDetail },
      { path: 'session-review/:id', component: TherapistSessionReview },
      { path: 'reports', component: TherapistReports },
      // «Analíticas IA» ahora es la pestaña «IA y juegos» de Reportes; los enlaces viejos llegan ahí.
      { path: 'analytics', redirectTo: () => inject(Router).parseUrl('/therapist/reports?tab=ai') },
      { path: 'incidents', component: IncidentsList, data: { viewMode: 'therapist' } },
      { path: 'kanban', loadComponent: () => import('./pages/kanban/kanban').then(m => m.KanbanPage) },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
    ],
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class TherapistRoutingModule {}
