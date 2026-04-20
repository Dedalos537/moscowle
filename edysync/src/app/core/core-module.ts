import { NgModule, Optional, SkipSelf } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { RouterModule } from '@angular/router'; // <- IMPORTANTE: Para router-outlet y routerLink
import { AuthInterceptor } from './interceptors/auth.interceptor';
import { MainLayout } from './layout/main-layout/main-layout';
import { Navbar } from './layout/navbar/navbar';
import { Footer } from './layout/footer/footer';
import { SharedModule } from '../shared/shared-module';

@NgModule({
  declarations: [
    MainLayout,
    Navbar,
    Footer
  ],
  imports: [
    CommonModule,
    HttpClientModule,
    RouterModule,
    SharedModule // Importamos para tener FontAwesome y <app-button> entre otros
  ],
  exports: [
    MainLayout
  ],
  providers: [
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

