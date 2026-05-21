// DCE — Diego Centeno Estuvo Acá
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { MainLayout } from './core/layout/main-layout/main-layout';

const routes: Routes = [
  {
    path: '',
    redirectTo: 'auth/login',
    pathMatch: 'full'
  },
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth-module').then(m => m.AuthModule)
  },
  {
    path: 'admin',
    loadChildren: () => import('./features/admin/admin-module').then(m => m.AdminModule)
  },
  {
    path: 'therapist',
    loadChildren: () => import('./features/therapist/therapist-module').then(m => m.TherapistModule)
  },
  {
    path: 'patient',
    loadChildren: () => import('./features/patient/patient-module').then(m => m.PatientModule)
  },
  {
    path: 'ai-assistant',
    loadChildren: () => import('./features/ai-assistant/ai-assistant-module').then(m => m.AiAssistantModule)
  },
  {
    path: '',
    component: MainLayout,
    children: [
      {
        path: '',
        loadChildren: () => import('./features/public/public-module').then(m => m.PublicModule)
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
