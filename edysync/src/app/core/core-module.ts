import { NgModule, Optional, SkipSelf } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { RouterModule } from '@angular/router'; // <- IMPORTANTE: Para router-outlet y routerLink
import { AuthInterceptor } from './interceptors/auth.interceptor';
import { ApiBaseInterceptor } from './interceptors/api-base.interceptor';
import { MainLayout } from './layout/main-layout/main-layout';
import { Navbar } from './layout/navbar/navbar';
import { Footer } from './layout/footer/footer';
import { SharedModule } from '../shared/shared-module';
import { Sidebar } from './components/sidebar/sidebar';
import { Header } from './components/header/header';
import { AdminLayout } from './layout/admin-layout/admin-layout';
import { TherapistLayout } from './layout/therapist-layout/therapist-layout';

@NgModule({
  declarations: [
    MainLayout,
    Navbar,
    Footer,
    Sidebar,
    Header,
    AdminLayout,
    TherapistLayout,
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

