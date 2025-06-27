// src/main/java/com/moscowle/repository/UsuarioRepository.java

package com.example.moscowle.repository;

import com.example.moscowle.models.Usuario;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface UsuarioRepository extends JpaRepository<Usuario, Integer> {

    Optional<Usuario> findByCorreo(String correo);

    Usuario findByCorreoAndContrasena(String correo, String contrasena);


}
