// src/main/java/com/moscowle/controller/AuthController.java

package com.example.moscowle.controllers;

import com.example.moscowle.models.Usuario;
import com.example.moscowle.repository.UsuarioRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class AuthController {

    @Autowired
    private UsuarioRepository usuarioRepository;

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> loginData) {
        String correo = loginData.get("email");
        String contrasena = loginData.get("password");

        Usuario usuario = usuarioRepository.findByCorreoAndContrasena(correo, contrasena);

        if (usuario == null) {
            return ResponseEntity.status(401).body("Credenciales inválidas o acceso no autorizado");
        }

        Map<String, Object> response = new HashMap<>();
        response.put("id", usuario.getId());
        response.put("correo", usuario.getCorreo());
        response.put("rol", usuario.getRol().getNombre());

        System.out.println("Intentando login con: " + correo);

        

        return ResponseEntity.ok(response);
    }
}
