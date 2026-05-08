import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { Dashboard } from './pages/dashboard/dashboard';
import { EdysyncDashboard } from './pages/edysync-dashboard/edysync-dashboard';
import { Sedes } from './pages/sedes/sedes';
import { UsersList } from './pages/users/users-list/users-list';
import { UserDetail } from './pages/users/user-detail/user-detail';
import { Payments } from './pages/payments/payments';
import { Debtors } from './pages/debtors/debtors';
import { PaymentHistory } from './pages/payment-history/payment-history';
import { Sessions } from './pages/sessions/sessions';
import { Expenses } from './pages/expenses/expenses';
import { Messages } from './pages/messages/messages';
import { Reports } from './pages/reports/reports';
import { AdminLayout } from '../../core/layout/admin-layout/admin-layout';

const routes: Routes = [
  { 
    path: '', 
    component: AdminLayout,
    children: [
      { path: 'dashboard', component: Dashboard },
      { path: 'edysync', component: EdysyncDashboard },
      { path: 'sedes', component: Sedes },
      { path: 'users', component: UsersList },
      { path: 'users/:id', component: UserDetail },
      { path: 'payments', component: Payments },
      { path: 'debtors', component: Debtors },
      { path: 'payments/history/:userId', component: PaymentHistory },
      { path: 'sessions', component: Sessions },
      { path: 'expenses', component: Expenses },
      { path: 'messages', component: Messages },
      { path: 'reports', component: Reports },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AdminRoutingModule { }
