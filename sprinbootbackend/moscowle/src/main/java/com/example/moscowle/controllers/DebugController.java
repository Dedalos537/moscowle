package com.example.moscowle.controllers;

import java.util.Map;
import java.util.Optional;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.example.moscowle.models.Usuario;
import com.example.moscowle.repository.UsuarioRepository;

@RestController
@RequestMapping("/api/debug")
@CrossOrigin(origins = {"http://localhost:3000", "http://localhost:3001"})
public class DebugController {

    @Autowired
    private UsuarioRepository usuarioRepository;

    @Autowired
    private BCryptPasswordEncoder passwordEncoder;

    @PostMapping("/reset-admin")
    public ResponseEntity<?> resetAdminPassword() {
        try {
            Optional<Usuario> adminOpt = usuarioRepository.findByCorreo("admin@moscowle.com");
            
            if (!adminOpt.isPresent()) {
                return ResponseEntity.notFound().build();
            }
            
            Usuario admin = adminOpt.get();
            String newPassword = "admin123";
            String hashedPassword = passwordEncoder.encode(newPassword);
            
            System.out.println("=== RESET ADMIN PASSWORD ===");
            System.out.println("Nueva contraseña: " + newPassword);
            System.out.println("Hash generado: " + hashedPassword);
            
            admin.setContrasena(hashedPassword);
            usuarioRepository.save(admin);
            
            // Verificar que funciona
            boolean testMatch = passwordEncoder.matches(newPassword, hashedPassword);
            System.out.println("Test de verificación: " + testMatch);
            
            return ResponseEntity.ok(Map.of(
                "message", "Contraseña del admin reseteada",
                "email", "admin@moscowle.com",
                "newPassword", newPassword,
                "hash", hashedPassword,
                "testMatch", testMatch
            ));
            
        } catch (Exception e) {
            System.err.println("Error al resetear contraseña: " + e.getMessage());
            return ResponseEntity.status(500).body("Error: " + e.getMessage());
        }
    }

    @GetMapping("/test-password")
    public ResponseEntity<?> testPassword() {
        String testPassword = "admin123";
        String hash1 = passwordEncoder.encode(testPassword);
        String hash2 = passwordEncoder.encode(testPassword);
        
        boolean match1 = passwordEncoder.matches(testPassword, hash1);
        boolean match2 = passwordEncoder.matches(testPassword, hash2);
        
        return ResponseEntity.ok(Map.of(
            "testPassword", testPassword,
            "hash1", hash1,
            "hash2", hash2,
            "match1", match1,
            "match2", match2,
            "hashesEqual", hash1.equals(hash2)
        ));
    }
}