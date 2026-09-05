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
import { CollapsiblePanel } from './components/collapsible-panel/collapsible-panel';
import { Select } from './components/select/select';

@NgModule({
  imports: [
    CommonModule, FormsModule, FontAwesomeModule,
    Button, Card, Input, Spinner, Alert, Modal, Chip,
    ProgressBar, PillStatus, CollapsiblePanel, Select,
  ],
  exports: [
    CommonModule, FormsModule, FontAwesomeModule,
    Button, Card, Input, Spinner, Alert, Modal, Chip,
    ProgressBar, PillStatus, CollapsiblePanel, Select,
  ]
})
export class SharedModule {
  constructor(library: FaIconLibrary) {
    // Add entire icon packs to prevent tree-shaking
    library.addIconPacks(fas, far, fab);
  }
}
