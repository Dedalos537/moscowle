package com.example.moscowle.service;

import com.example.moscowle.models.Usuario;
import com.example.moscowle.repository.UsuarioRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional; 

@Service
public class AuthService {

    @Autowired
    private UsuarioRepository usuarioRepository;

    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

    public Map<String, Object> login(String correo, String rawPassword) {
        Optional<Usuario> optionalUsuario = usuarioRepository.findByCorreo(correo); // Use Optional for safety
        Usuario usuario = optionalUsuario.orElse(null); // Get User or null

        if (usuario == null) {
            System.out.println("Intento de login fallido: usuario no encontrado para correo " + correo);
            return null; // User not found
        }

        if (!encoder.matches(rawPassword, usuario.getContrasena())) {
            System.out.println("Intento de login fallido: contraseña incorrecta para correo " + correo);
            return null; // Password does not match
        }

        Map<String, Object> datos = new HashMap<>();
        datos.put("id", usuario.getId());
        datos.put("correo", usuario.getCorreo());
        // Ensure rol is not null before calling getNombre()
        datos.put("rol", usuario.getRol() != null ? usuario.getRol().getNombre() : "UNDEFINED_ROL");

        return datos;
    }
}