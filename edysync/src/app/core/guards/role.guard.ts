import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { map } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class RoleGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    const requiredRole = route.data['role'] as string;
    return this.auth.currentUser$.pipe(
      map(user => {
        if (user && user.role === requiredRole) {
          return true;
        }
        this.router.navigate(['/admin/dashboard']);
        return false;
      })
    );
  }
}
