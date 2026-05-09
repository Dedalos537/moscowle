import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FullCalendarModule } from '@fullcalendar/angular';

import { AdminRoutingModule } from './admin-routing-module';
import { SharedModule } from '../../shared/shared-module';
import { Dashboard } from './pages/dashboard/dashboard';
import { EdysyncDashboard } from './pages/edysync-dashboard/edysync-dashboard';
import { Sedes } from './pages/sedes/sedes';
import { SedeCard } from './pages/sedes/components/sede-card/sede-card';
import { UsersList } from './pages/users/users-list/users-list';
import { UserDetail } from './pages/users/user-detail/user-detail';
import { Payments } from './pages/payments/payments';
import { Debtors } from './pages/debtors/debtors';
import { PaymentHistory } from './pages/payment-history/payment-history';
import { Sessions } from './pages/sessions/sessions';
import { Expenses } from './pages/expenses/expenses';
import { Messages } from './pages/messages/messages';
import { Reports } from './pages/reports/reports';
import { Games } from './pages/games/games';
import { CspReports } from './pages/csp-reports/csp-reports';
import { ApiTokens } from './pages/api-tokens/api-tokens';
import { Profile } from './pages/profile/profile';
import { YapeImport } from './pages/yape-import/yape-import';
import { AiTraining } from './pages/ai-training/ai-training';

@NgModule({
  declarations: [
    Dashboard,
    EdysyncDashboard,
    Sedes,
    SedeCard,
    UsersList,
    UserDetail,
    Payments,
    Debtors,
    PaymentHistory,
    Sessions,
    Expenses,
    Messages,
    Reports,
    Games,
    CspReports,
    ApiTokens,
    Profile,
    YapeImport,
    AiTraining
  ],
  imports: [
    CommonModule,
    FormsModule,
    FullCalendarModule,
    AdminRoutingModule,
    SharedModule
  ]
})
export class AdminModule { }
