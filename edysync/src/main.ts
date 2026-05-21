// DCE — Diego Centeno Estuvo Acá
import 'zone.js';
import { platformBrowser } from '@angular/platform-browser';
import * as Sentry from '@sentry/angular';
import { AppModule } from './app/app-module';
import { environment } from './environments/environment';

if (environment.sentryDsn) {
  Sentry.init({
    dsn: environment.sentryDsn,
    environment: environment.production ? 'production' : 'development',
    sendDefaultPii: true,
    tracesSampleRate: 0.1,
  });
}

platformBrowser().bootstrapModule(AppModule)
  .catch(err => console.error(err));
