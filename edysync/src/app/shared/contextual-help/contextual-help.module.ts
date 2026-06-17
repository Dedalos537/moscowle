import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { HelpButton } from './components/help-button/help-button';
import { HelpPanel } from './components/help-panel/help-panel';

@NgModule({
  imports: [CommonModule, FontAwesomeModule, HelpButton, HelpPanel],
  exports: [HelpButton, HelpPanel],
})
export class ContextualHelpModule {}
