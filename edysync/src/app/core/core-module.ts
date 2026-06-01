import { NgModule, Optional, SkipSelf } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { AuthInterceptor } from './interceptors/auth.interceptor';
import { ApiBaseInterceptor } from './interceptors/api-base.interceptor';
import { ErrorInterceptor } from './interceptors/error.interceptor';
import { MainLayout } from './layout/main-layout/main-layout';
import { Navbar } from './layout/navbar/navbar';
import { Footer } from './layout/footer/footer';
import { SharedModule } from '../shared/shared-module';
import { Sidebar } from './components/sidebar/sidebar';
import { Header } from './components/header/header';
import { AdminLayout } from './layout/admin-layout/admin-layout';
import { TherapistLayout } from './layout/therapist-layout/therapist-layout';
import { PatientLayout } from './layout/patient-layout/patient-layout';

@NgModule({
  declarations: [
    MainLayout,
    Navbar,
    Footer,
    Sidebar,
    Header,
    AdminLayout,
    TherapistLayout,
    PatientLayout,
  ],
  imports: [
    CommonModule,
    HttpClientModule,
    RouterModule,
    SharedModule
  ],
  exports: [
    MainLayout,
    AdminLayout,
    TherapistLayout,
    PatientLayout,
  ],
  providers: [
    {
      provide: HTTP_INTERCEPTORS,
      useClass: ApiBaseInterceptor,
      multi: true
    },
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    },
    {
      provide: HTTP_INTERCEPTORS,
      useClass: ErrorInterceptor,
      multi: true
    }
  ]
})
export class CoreModule {
  constructor(@Optional() @SkipSelf() parentModule: CoreModule) {
    if (parentModule) {
      throw new Error('CoreModule ya ha sido cargado. Impórtalo únicamente en el AppModule.');
    }
  }
}
