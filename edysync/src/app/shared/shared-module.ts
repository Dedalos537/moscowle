import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

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

@NgModule({
  declarations: [
    Button,
    Card,
    Input,
    Spinner,
    Alert,
    Modal,
    Chip,
    ProgressBar,
    PillStatus
  ],
  imports: [
    CommonModule,
    FontAwesomeModule
  ],
  exports: [
    CommonModule,
    FontAwesomeModule,
    Button,
    Card,
    Input,
    Spinner,
    Alert,
    Modal,
    Chip,
    ProgressBar,
    PillStatus
  ]
})
export class SharedModule {
  constructor(library: FaIconLibrary) {
    library.addIconPacks(fas, far, fab);
  }
}
