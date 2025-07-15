import { Routes } from '@angular/router';
import { Login } from './pages/auth/login/login';
import { Home } from './pages/home/home';
import { About } from './pages/about/about';
import { Services } from './pages/services/services';
import { Contact } from './pages/contact/contact';
import { Solicitudes } from './pages/admin/solicitudes/solicitudes';

import { CursosComponent } from './shared/component/LMS/cursos.component';
import { PerfilComponent } from './shared/component/perfil/Perfil.component';


export const routes: Routes = [
  { path: '', component: Home },
  { path: 'home', component: Home },
  { path: 'about', component: About },
  { path: 'services', component: Services },
  { path: 'contact', component: Contact },
  { path: 'login', component: Login },
  { path: 'dashboard', component: Solicitudes },
  { path: 'cursos', component: CursosComponent },
  { path: 'perfil', component: PerfilComponent }, 
  { path: '**',pathMatch: 'full', redirectTo: 'home'},
  

];
