// DCE — Diego Centeno Estuvo Acá
import { NgModule, ErrorHandler } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import * as Sentry from '@sentry/angular';

import { AppRoutingModule } from './app-routing-module';
import { CoreModule } from './core/core-module';
import { SharedModule } from './shared/shared-module';
import { App } from './app';

@NgModule({
  declarations: [
    App
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    AppRoutingModule,
    CoreModule,
    SharedModule
  ],
  providers: [
    { provide: ErrorHandler, useValue: Sentry.createErrorHandler() },
  ],
  bootstrap: [App]
})
export class AppModule { }
