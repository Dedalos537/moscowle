import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { HelpButton } from './components/help-button/help-button';
import { HelpPanel } from './components/help-panel/help-panel';
import { WizardOverlay } from './components/wizard-overlay/wizard-overlay';

@NgModule({
  imports: [CommonModule, FontAwesomeModule, HelpButton, HelpPanel, WizardOverlay],
  exports: [HelpButton, HelpPanel, WizardOverlay],
})
export class ContextualHelpModule {}
