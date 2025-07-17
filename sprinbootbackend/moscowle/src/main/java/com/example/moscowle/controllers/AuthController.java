package com.example.moscowle.controllers;

import com.example.moscowle.security.JwtUtil;
import com.example.moscowle.service.AuthService;

import jakarta.servlet.http.HttpServletResponse;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "http://localhost:4200", allowCredentials = "true")
public class AuthController {

    @Autowired
    private AuthService authService;

    @Autowired
    private JwtUtil jwtUtil;

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> loginData, HttpServletResponse response) {
        try {
            String correo = loginData.get("email");
            String rawPassword = loginData.get("password");

            System.out.println("Intento de login - Correo: " + correo);

            if (correo == null || rawPassword == null) {
                return ResponseEntity.badRequest().body("Email y contraseña son requeridos");
            }

            Map<String, Object> responseData = authService.login(correo, rawPassword);

            if (responseData == null) {
                return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                        .body("Credenciales inválidas o acceso no autorizado");
            }

            // Generar JWT y agregarlo a la respuesta
            String token = jwtUtil.generateToken(correo, (String) responseData.get("rol"));
            responseData.put("token", token);

            // Set cookie (HTTP Only, SameSite=None, Secure si usas HTTPS)
            jakarta.servlet.http.Cookie cookie = new jakarta.servlet.http.Cookie("authToken", token);
            cookie.setHttpOnly(true);
            cookie.setPath("/");
            cookie.setMaxAge(60 * 60 * 10); // 10 horas
            cookie.setSecure(false); // true si usas HTTPS
            cookie.setDomain("localhost"); // ajusta si usas otro dominio
            response.addCookie(cookie);

            System.out.println("Login exitoso para: " + correo);
            return ResponseEntity.ok(responseData);

        } catch (Exception e) {
            System.err.println("Error en login: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body("Error interno del servidor");
        }
    }

    @GetMapping("/auth/validate")
    public ResponseEntity<?> validateToken(@CookieValue(value = "authToken", required = false) String token) {
        if (token == null || !jwtUtil.validateToken(token)) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body("Token inválido");
        }
        return ResponseEntity.ok(Map.of("valid", true));
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout() {
        // Aquí podrías invalidar la sesión si usas sesiones de Spring, pero como es
        // stateless, solo responde OK
        return ResponseEntity.ok(Map.of("success", true, "message", "Sesión cerrada correctamente"));
    }
}