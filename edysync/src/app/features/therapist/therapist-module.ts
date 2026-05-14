import { TherapistDashboard } from './pages/dashboard/dashboard';
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FullCalendarModule } from '@fullcalendar/angular';

import { TherapistRoutingModule } from './therapist-routing-module';
import { SharedModule } from '../../shared/shared-module';
import { TherapistSessions } from './pages/sessions/therapist-sessions';
import { TherapistMessages } from './pages/messages/therapist-messages';
import { TherapistProfile } from './pages/profile/therapist-profile';
import { TherapistGames } from './pages/games/therapist-games';

@NgModule({
  declarations: [
    TherapistDashboard,
    TherapistSessions,
    TherapistMessages,
    TherapistProfile,
    TherapistGames,
  ],
  imports: [
    CommonModule,
    FormsModule,
    FullCalendarModule,
    TherapistRoutingModule,
    SharedModule,
  ],
})
export class TherapistModule {}
