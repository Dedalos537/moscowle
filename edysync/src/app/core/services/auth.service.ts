import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';

export interface LoginResponse {
  valid?: boolean;
  user?: any;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly API_URL = 'http://localhost:5000/api/auth'; 

  private currentUserSubject = new BehaviorSubject<any>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      this.currentUserSubject.next(JSON.parse(storedUser));
    }
  }

  // Lógica basada en Cookies con flask-login
  login(email: string, password: string): Observable<LoginResponse> {
    // Apunta al endpoint correcto que retorna JSON validando la sesión
    return this.http.post<LoginResponse>(`${this.API_URL}/validate`, { email, password }).pipe(
      tap(response => {
        if (response && response.valid) {
          // La cookie de sesión (session) ya la guardó el navegador automáticamente
          if (response.user) {
            localStorage.setItem('user', JSON.stringify(response.user));
            this.currentUserSubject.next(response.user);
          } else {
            // Guardar un valor mínimo si el backend no manda los datos completos
            localStorage.setItem('user', JSON.stringify({ email }));
            this.currentUserSubject.next({ email });
          }
        }
      })
    );
  }

  logout(): Observable<any> {
    // Notificar al backend para que destruya la sesión en flask-login
    return this.http.get(`${this.API_URL}/logout`).pipe(
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
