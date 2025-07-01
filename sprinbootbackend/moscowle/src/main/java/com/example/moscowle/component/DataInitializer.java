package com.example.moscowle.component;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import com.example.moscowle.repository.RolRepository;
import com.example.moscowle.service.AuthService;
import com.example.moscowle.models.*;

@Component
public class DataInitializer implements CommandLineRunner {

    @Autowired
    private AuthService authService;

    @Autowired
    private RolRepository rolRepository;

    @Override
    public void run(String... args) throws Exception {
        initializeRoles();
        initializeAdminUser();
    }

    private void initializeRoles() {
        // Crear rol ADMIN si no existe
        if (!rolRepository.findByNombre("ADMIN").isPresent()) {
            Rol adminRole = new Rol("ADMIN");
            rolRepository.save(adminRole);
            System.out.println("Rol ADMIN creado");
        }

        // Crear rol USER si no existe
        if (!rolRepository.findByNombre("USER").isPresent()) {
            Rol userRole = new Rol("USER");
            rolRepository.save(userRole);
            System.out.println("Rol USER creado");
        }
    }

    private void initializeAdminUser() {
        // Crear usuario administrador por defecto
        String adminEmail = "admin@moscowle.com";
        String adminPassword = "admin123";

        Usuario admin = authService.crearUsuarioAdmin(adminEmail, adminPassword);
        if (admin != null) {
            System.out.println("Usuario administrador creado:");
            System.out.println("Email: " + adminEmail);
            System.out.println("Password: " + adminPassword);
        } else {
            System.out.println("Usuario administrador ya existe");
        }
    }
}