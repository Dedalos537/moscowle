import 'zone.js';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { provideRouter, Routes } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { importProvidersFrom, ErrorHandler } from '@angular/core';
import * as Sentry from '@sentry/angular';

import { App } from './app/app';
import { environment } from './environments/environment';
import { SharedModule } from './app/shared/shared-module';
import { CoreModule } from './app/core/core-module';
import { MainLayout } from './app/core/layout/main-layout/main-layout';

if (environment.sentryDsn) {
  Sentry.init({
    dsn: environment.sentryDsn,
    environment: environment.production ? 'production' : 'development',
    sendDefaultPii: true,
    tracesSampleRate: 0.1,
  });
}

const routes: Routes = [
  {
    path: '',
    redirectTo: 'auth/login',
    pathMatch: 'full'
  },
  {
    path: 'auth',
    loadChildren: () => import('./app/features/auth/auth-module').then(m => m.AuthModule)
  },
  {
    path: 'admin',
    loadChildren: () => import('./app/features/admin/admin-module').then(m => m.AdminModule)
  },
  {
    path: 'therapist',
    loadChildren: () => import('./app/features/therapist/therapist-module').then(m => m.TherapistModule)
  },
  {
    path: 'patient',
    loadChildren: () => import('./app/features/patient/patient-module').then(m => m.PatientModule)
  },
  {
    path: 'ai-assistant',
    loadChildren: () => import('./app/features/ai-assistant/ai-assistant-module').then(m => m.AiAssistantModule)
  },
  {
    path: '',
    component: MainLayout,
    children: [
      {
        path: '',
        loadChildren: () => import('./app/features/public/public-module').then(m => m.PublicModule)
      }
    ]
  }
];

bootstrapApplication(App, {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptorsFromDi()),
    provideAnimations(),
    importProvidersFrom(SharedModule, CoreModule),
    { provide: ErrorHandler, useValue: Sentry.createErrorHandler() },
  ]
}).catch(err => console.error(err));
