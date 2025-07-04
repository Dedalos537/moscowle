package com.example.moscowle.controllers;

import com.example.moscowle.security.JwtUtil;
import com.example.moscowle.service.AuthService; 
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus; 
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = {"http://localhost:3000", "http://localhost:3001"})
public class AuthController {

    @Autowired
    private AuthService authService;

    @Autowired
    private JwtUtil jwtUtil;

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> loginData) {
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

            System.out.println("Login exitoso para: " + correo);
            return ResponseEntity.ok(responseData);

        } catch (Exception e) {
            System.err.println("Error en login: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("Error interno del servidor");
        }
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout() {
        // Aquí podrías invalidar la sesión si usas sesiones de Spring, pero como es stateless, solo responde OK
        return ResponseEntity.ok(Map.of("success", true, "message", "Sesión cerrada correctamente"));
    }
}