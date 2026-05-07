import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, map, switchMap, tap } from 'rxjs';

export interface LoginResponse {
  valid?: boolean;
  user?: any;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly LOGIN_URL = '/moscowle/login'; 

  private currentUserSubject = new BehaviorSubject<any>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      this.currentUserSubject.next(JSON.parse(storedUser));
    }
  }

  // HACK MAESTRO v2.0: Dado que no modificamos el backend remoto, scrapeamos tu CSRF de la vista original
  // y lo enviamos simulando al 100% como si fueramos tu formulario Flask de x-www-form-urlencoded
  login(email: string, password: string): Observable<any> {
    // 1. Cargamos el HTML para robar el csrf_token
    return this.http.get(this.LOGIN_URL, { responseType: 'text' }).pipe(
      switchMap((htmlPage: string) => {
        // Expresión regular para ubicar <input type="hidden" name="csrf_token" value="...">
        const match = htmlPage.match(/name="csrf_token"\s+value="([^"]+)"/);
        const csrfToken = match ? match[1] : '';

        // 2. Construimos la petición real que el backend exige
        const body = new URLSearchParams();
        if (csrfToken) body.set('csrf_token', csrfToken);
        body.set('email', email);
        body.set('password', password);

        // 3. ¡Nos Logueamos!
        return this.http.post(this.LOGIN_URL, body.toString(), {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          observe: 'response',
          responseType: 'text'
        });
      }),
      tap(response => {
        // El servidor responderá con un redirect(302) y terminaremos en "/dashboard"
        if (response.url && response.url.includes('dashboard')) {
          localStorage.setItem('user', JSON.stringify({ email, role: 'admin' }));
          this.currentUserSubject.next({ email, role: 'admin' });
        } else {
          throw new Error('Credenciales inválidas');
        }
      })
    );
  }

  logout(): Observable<any> {
    // Notificar al backend para que destruya la sesión en flask-login. 
    // Usamos responseType: 'text' porque Flask responde con un Redirect 302 hacia HTML.
    return this.http.get('/moscowle/logout', { responseType: 'text' }).pipe(
      tap(() => {
        localStorage.removeItem('user');
        this.currentUserSubject.next(null);
      })
    );
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem('user');
  }
}
