// DCE — Diego Centeno Estuvo Acá
import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { map } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class RoleGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    const requiredRole = route.data['role'] as string | string[];
    return this.auth.currentUser$.pipe(
      map(user => {
        if (!user) {
          this.router.navigate(['/auth/login']);
          return false;
        }
        if (Array.isArray(requiredRole)) {
          if (requiredRole.includes(user.role)) {
            return true;
          }
        } else if (user.role === requiredRole) {
          return true;
        }
        // Admin can access therapist routes
        if (user.role === 'admin' && (requiredRole === 'terapista' || (Array.isArray(requiredRole) && requiredRole.includes('terapista')))) {
          return true;
        }
        this.router.navigate(['/auth/login']);
        return false;
      })
    );
  }
}
