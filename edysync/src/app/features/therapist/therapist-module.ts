import { TherapistDashboard } from './pages/dashboard/dashboard';
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { BaseChartDirective } from 'ng2-charts';

import { TherapistRoutingModule } from './therapist-routing-module';
import { SharedModule } from '../../shared/shared-module';
import { TherapistSessions } from './pages/sessions/therapist-sessions';
import { TherapistSessionReview } from './pages/session-review/session-review';
import { TherapistMessages } from './pages/messages/therapist-messages';
import { TherapistProfile } from './pages/profile/therapist-profile';
import { TherapistGames } from './pages/games/therapist-games';
import { TherapistPatients } from './pages/patients/patients';
import { TherapistPatientDetail } from './pages/patient-detail/patient-detail';
import { TherapistReports } from './pages/reports/reports';
import { TherapistAnalytics } from './pages/analytics/analytics';
import { TherapistCalendarPage } from './pages/calendar/calendar';

@NgModule({
  declarations: [
    TherapistDashboard,
    TherapistSessions,
    TherapistSessionReview,
    TherapistMessages,
    TherapistProfile,
    TherapistGames,
    TherapistPatients,
    TherapistPatientDetail,
    TherapistReports,
    TherapistAnalytics,
    TherapistCalendarPage,
  ],
  imports: [
    CommonModule,
    FormsModule,
    BaseChartDirective,
    TherapistRoutingModule,
    SharedModule,
  ],
})
export class TherapistModule {}
