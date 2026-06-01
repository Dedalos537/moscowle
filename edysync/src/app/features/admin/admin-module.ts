import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { BaseChartDirective } from 'ng2-charts';

import { AdminRoutingModule } from './admin-routing-module';
import { SharedModule } from '../../shared/shared-module';
import { Dashboard } from './pages/dashboard/dashboard';
import { Sedes } from './pages/sedes/sedes';
import { SedeCard } from './pages/sedes/components/sede-card/sede-card';
import { UsersList } from './pages/users/users-list/users-list';
import { UserDetail } from './pages/users/user-detail/user-detail';
import { Finanzas } from './pages/finanzas/finanzas';
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
import { QuickPayment } from './components/quick-payment/quick-payment';
import { Logs } from './pages/logs/logs';

@NgModule({
  declarations: [
    Dashboard,
    Sedes,
    SedeCard,
    UsersList,
    UserDetail,
    Finanzas,
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
    AiTraining,
    QuickPayment,
    Logs,
  ],
  imports: [
    CommonModule,
    FormsModule,
    AdminRoutingModule,
    SharedModule,
    BaseChartDirective
  ]
})
export class AdminModule { }
