package com.example.moscowle.controllers;

import com.example.moscowle.models.Usuario;
import com.example.moscowle.models.dto.UsuarioNombreApellidoDTO;
import com.example.moscowle.repository.UsuarioRepository;
import com.example.moscowle.security.JwtUtil;
import com.example.moscowle.service.AuthService;

import jakarta.servlet.http.HttpServletRequest;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "http://localhost:4200")
public class AuthController {
    @Autowired
    private AuthService authService;

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private UsuarioRepository usuarioRepository;

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

    @GetMapping("/auth/validate")
    public ResponseEntity<?> validateToken(
            @RequestHeader(value = "Authorization", required = false) String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body("Token faltante o inválido");
        }
        String token = authHeader.substring(7);
        if (jwtUtil.validateToken(token)) {
            return ResponseEntity.ok(Map.of("valid", true));
        } else {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body("Token inválido");
        }
    }

    @GetMapping("/auth/me")
    public ResponseEntity<UsuarioNombreApellidoDTO> getUsuarioAutenticado(HttpServletRequest request) {
        String token = obtenerTokenDesdeHeader(request);
        String correo = jwtUtil.extractUsername(token); // <- Aquí corregido
        Usuario usuario = usuarioRepository.findByCorreo(correo).orElseThrow();

        return ResponseEntity.ok(new UsuarioNombreApellidoDTO(usuario.getNombre(), usuario.getApellido()));
    }

    private String obtenerTokenDesdeHeader(HttpServletRequest request) {
        String authHeader = request.getHeader("Authorization");
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            return authHeader.substring(7);
        } else {
            throw new RuntimeException("Token no encontrado en el header");
        }
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout() {
        // Aquí podrías invalidar la sesión si usas sesiones de Spring, pero como es
        // stateless, solo responde OK
        return ResponseEntity.ok(Map.of("success", true, "message", "Sesión cerrada correctamente"));
    }
}