import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';


import { PatientRoutingModule } from './patient-routing-module';
import { SharedModule } from '../../shared/shared-module';
import { PatientDashboard } from './pages/dashboard/dashboard';
import { PatientSessions } from './pages/sessions/sessions';
import { PatientPayments } from './pages/payments/payments';
import { PatientProgressPage } from './pages/progress/progress';
import { PatientCalendar } from './pages/calendar/calendar';
import { PatientMessages } from './pages/messages/messages';
import { PatientProfile } from './pages/profile/profile';
import { PatientMyTherapist } from './pages/my-therapist/my-therapist';

@NgModule({
  declarations: [
    PatientDashboard,
    PatientSessions,
    PatientPayments,
    PatientProgressPage,
    PatientCalendar,
    PatientMessages,
    PatientProfile,
    PatientMyTherapist,
  ],
  imports: [
    CommonModule,
    FormsModule,
    PatientRoutingModule,
    SharedModule,
  ],
})
export class PatientModule {}
