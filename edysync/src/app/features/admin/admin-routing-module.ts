import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { RoleGuard } from '../../core/guards/role.guard';
import { Dashboard } from './pages/dashboard/dashboard';
import { Sedes } from './pages/sedes/sedes';
import { UsersList } from './pages/users/users-list/users-list';
import { UserDetail } from './pages/users/user-detail/user-detail';
import { PaymentHistory } from './pages/payment-history/payment-history';
import { Sessions } from './pages/sessions/sessions';
import { Expenses } from './pages/expenses/expenses';
import { ChatComponent } from '../../shared/components/chat/chat.component';
import { Games } from './pages/games/games';
import { CspReports } from './pages/csp-reports/csp-reports';
import { ApiTokens } from './pages/api-tokens/api-tokens';
import { Profile } from './pages/profile/profile';
import { YapeImport } from './pages/yape-import/yape-import';
import { AiTraining } from './pages/ai-training/ai-training';
import { Incidents } from './pages/incidents/incidents';
import { IncidentDetailPage } from './pages/incidents/incident-detail';
import { PasswordResets } from './pages/password-resets/password-resets';
import { AdminLayout } from '../../core/layout/admin-layout/admin-layout';

const routes: Routes = [
  {
    path: '',
    component: AdminLayout,
    canActivate: [RoleGuard],
    data: { role: ['admin', 'supervisor'] },
    children: [
      { path: 'dashboard', component: Dashboard },
      { path: 'sedes', component: Sedes },
      { path: 'users', component: UsersList },
      { path: 'users/:id', component: UserDetail },
      { path: 'finanzas', loadComponent: () => import('./pages/finanzas/finanzas').then(m => m.Finanzas) },
      { path: 'payments', loadComponent: () => import('./pages/payments/payments').then(m => m.Payments) },
      { path: 'payments/history/:userId', component: PaymentHistory },
      { path: 'sessions', component: Sessions },
      { path: 'expenses', component: Expenses },
      { path: 'messages', component: ChatComponent },
      { path: 'reports', loadComponent: () => import('./pages/reports/reports').then(m => m.Reports) },
      { path: 'games', component: Games },
      { path: 'csp-reports', component: CspReports },
      { path: 'api-tokens', component: ApiTokens },
      { path: 'profile', component: Profile },
      { path: 'yape-import', component: YapeImport },
      { path: 'ai', component: AiTraining },
      { path: 'visor-funcionamiento', loadComponent: () => import('./pages/visor-funcionamiento/visor-funcionamiento').then(m => m.VisorFuncionamiento) },
      { path: 'operations', redirectTo: 'visor-funcionamiento', pathMatch: 'full' },
      { path: 'incidents', component: Incidents },
      { path: 'incidents/:id', component: IncidentDetailPage },
      { path: 'password-resets', component: PasswordResets },
      { path: 'settings', loadComponent: () => import('./pages/settings/settings').then(m => m.Settings) },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AdminRoutingModule { }
