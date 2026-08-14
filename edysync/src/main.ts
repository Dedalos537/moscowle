import 'zone.js';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { provideRouter, Routes } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { importProvidersFrom, ErrorHandler, APP_INITIALIZER } from '@angular/core';
import { FaIconLibrary } from '@fortawesome/angular-fontawesome';
import { provideBeacon } from 'ng-beacon';
import * as Sentry from '@sentry/angular';

import { App } from './app/app';
import { environment } from './environments/environment';
import { CoreModule } from './app/core/core-module';
import { registerAppIcons } from './app/shared/fontawesome-icons';

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
    loadComponent: () => import('./app/core/layout/main-layout/main-layout').then(m => m.MainLayout),
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
    provideBeacon({ backdropColor: 'rgba(0, 0, 0, 0.55)' }),
    importProvidersFrom(CoreModule),
    {
      provide: APP_INITIALIZER,
      useFactory: (library: FaIconLibrary) => () => registerAppIcons(library),
      deps: [FaIconLibrary],
      multi: true,
    },
    {
      provide: ErrorHandler,
      useClass: class extends ErrorHandler {
        override handleError(error: any) {
          console.error('[ANGULAR-ERROR]', error);
          try { Sentry.createErrorHandler().handleError(error); } catch (e) { /* noop */ }
        }
      }
    },
  ]
}).catch(err => console.error(err));
