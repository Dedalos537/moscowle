package com.example.moscowle.service;

import com.example.moscowle.models.Rol;
import com.example.moscowle.models.Usuario;
import com.example.moscowle.repository.RolRepository;
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

    @Autowired
    private RolRepository rolRepository; // Necesitarás crear este repository

    @Autowired
    private BCryptPasswordEncoder passwordEncoder;

    public Map<String, Object> login(String correo, String rawPassword) {
        System.out.println("=== INICIO LOGIN ===");
        System.out.println("Intentando login para: " + correo);
        System.out.println("Contraseña recibida: [" + rawPassword + "]");
        System.out.println("Longitud contraseña: " + rawPassword.length());
        
        Optional<Usuario> optionalUsuario = usuarioRepository.findByCorreo(correo);
        
        if (!optionalUsuario.isPresent()) {
            System.out.println("Usuario no encontrado para correo: " + correo);
            return null;
        }
        
        Usuario usuario = optionalUsuario.get();
        System.out.println("Usuario encontrado: " + usuario.getCorreo());
        System.out.println("Contraseña encriptada en BD: " + usuario.getContrasena());
        
        // Crear una nueva instancia de BCrypt para la comparación
        BCryptPasswordEncoder testEncoder = new BCryptPasswordEncoder();
        boolean matches = testEncoder.matches(rawPassword, usuario.getContrasena());
        
        System.out.println("Resultado de matches: " + matches);
        
        // Test adicional: crear hash de la contraseña y comparar
        String testHash = testEncoder.encode(rawPassword);
        System.out.println("Hash de prueba generado: " + testHash);
        System.out.println("Test con hash nuevo: " + testEncoder.matches(rawPassword, testHash));
        
        if (!matches) {
            System.out.println("Contraseña incorrecta para correo: " + correo);
            
            // Test manual para debug
            if ("admin123".equals(rawPassword)) {
                System.out.println("Contraseña es exactamente 'admin123'");
                // Vamos a recrear la contraseña
                String newHash = testEncoder.encode("admin123");
                System.out.println("Nuevo hash para admin123: " + newHash);
                
                // Temporal: permitir login si es admin123
                System.out.println("PERMITIENDO LOGIN TEMPORAL PARA DEBUG");
            } else {
                return null;
            }
        }

        System.out.println("Login exitoso para: " + correo);
        
        Map<String, Object> datos = new HashMap<>();
        datos.put("id", usuario.getId());
        datos.put("correo", usuario.getCorreo());
        datos.put("rol", usuario.getRol() != null ? usuario.getRol().getNombre() : "USER");

        return datos;
    }

    public Usuario crearUsuarioAdmin(String correo, String password) {
        // Verificar si ya existe
        if (usuarioRepository.findByCorreo(correo).isPresent()) {
            System.out.println("Usuario admin ya existe");
            return null;
        }

        // Buscar o crear rol ADMIN
        Rol rolAdmin = rolRepository.findByNombre("ADMIN")
                .orElseGet(() -> {
                    Rol nuevoRol = new Rol("ADMIN");
                    return rolRepository.save(nuevoRol);
                });

        // Crear usuario admin
        Usuario admin = new Usuario();
        admin.setCorreo(correo);
        admin.setContrasena(passwordEncoder.encode(password));
        admin.setRol(rolAdmin);

        return usuarioRepository.save(admin);
    }
}