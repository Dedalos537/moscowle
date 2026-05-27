import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { FontAwesomeModule, FaIconLibrary } from '@fortawesome/angular-fontawesome';
import { fas } from '@fortawesome/free-solid-svg-icons';
import { far } from '@fortawesome/free-regular-svg-icons';
import { fab } from '@fortawesome/free-brands-svg-icons';

import { Button } from './components/button/button';
import { Card } from './components/card/card';
import { Input } from './components/input/input';
import { Spinner } from './components/spinner/spinner';
import { Alert } from './components/alert/alert';
import { Modal } from './components/modal/modal';
import { Chip } from './components/chip/chip';
import { ProgressBar } from './components/progress-bar/progress-bar';
import { PillStatus } from './components/pill-status/pill-status';
import { AiChat } from './components/ai-chat/ai-chat';
import { CalendarWidget } from './components/calendar-widget/calendar-widget';
import { AlertModal } from './components/alert-modal/alert-modal.component';
import { RecordingOverlay } from './components/recording-overlay/recording-overlay';
import { ConfirmDialog } from './components/confirm-dialog/confirm-dialog';
import { ChatComponent } from './components/chat/chat.component';

@NgModule({
  declarations: [
    Button, Card, Input, Spinner, Alert, Modal, Chip,
    ProgressBar, PillStatus, AiChat, CalendarWidget, AlertModal, RecordingOverlay, ConfirmDialog,
    ChatComponent,
  ],
  imports: [
    CommonModule, FormsModule, FontAwesomeModule
  ],
  exports: [
    CommonModule, FormsModule, FontAwesomeModule,
    Button, Card, Input, Spinner, Alert, Modal, Chip,
    ProgressBar, PillStatus, AiChat, CalendarWidget, AlertModal, RecordingOverlay, ConfirmDialog,
    ChatComponent,
  ]
})
export class SharedModule {
  constructor(library: FaIconLibrary) {
    library.addIconPacks(fas, far, fab);
  }
}
