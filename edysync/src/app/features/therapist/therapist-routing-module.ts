import { TherapistDashboard } from './pages/dashboard/dashboard';
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { RoleGuard } from '../../core/guards/role.guard';
import { TherapistLayout } from '../../core/layout/therapist-layout/therapist-layout';
import { TherapistSessions } from './pages/sessions/therapist-sessions';
import { TherapistMessages } from './pages/messages/therapist-messages';
import { TherapistProfile } from './pages/profile/therapist-profile';
import { TherapistGames } from './pages/games/therapist-games';

const routes: Routes = [
  {
    path: '',
    component: TherapistLayout,
    canActivate: [RoleGuard],
    data: { role: 'terapista' },
    children: [
      { path: 'dashboard', component: TherapistDashboard },
      { path: 'sessions', component: TherapistSessions },
      { path: 'messages', component: TherapistMessages },
      { path: 'profile', component: TherapistProfile },
      { path: 'games', component: TherapistGames },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
    ],
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class TherapistRoutingModule {}
