// src/main/java/com/moscowle/service/AuthService.java

package com.example.moscowle.service;

import com.example.moscowle.models.Usuario;
import com.example.moscowle.repository.UsuarioRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class AuthService {

    @Autowired
    private UsuarioRepository usuarioRepository;

    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

    public Map<String, Object> login(String correo, String rawPassword) {
        Usuario usuario = usuarioRepository.findByCorreo(correo).orElse(null);

        if (usuario == null || !encoder.matches(rawPassword, usuario.getContrasena())) {
            return null;
        }

        Map<String, Object> datos = new HashMap<>();
        datos.put("id", usuario.getId());
        datos.put("correo", usuario.getCorreo());
        datos.put("rol", usuario.getRol().getNombre());

        return datos;
    }
}
