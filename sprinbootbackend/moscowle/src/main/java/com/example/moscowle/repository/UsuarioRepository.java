package com.example.moscowle.repository;

import com.example.moscowle.models.Usuario;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface UsuarioRepository extends JpaRepository<Usuario, Integer> {
    boolean existsByCorreo(String correo); // opcional, para validaciones
    Usuario findByCorreo(String correo);   // opcional, para login u otros usos
}
