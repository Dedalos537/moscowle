// src/main/java/com/moscowle/repository/SolicitudRegistroRepository.java

package com.example.moscowle.repository;

import com.example.moscowle.models.SolicitudRegistro;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SolicitudRegistroRepository extends JpaRepository<SolicitudRegistro, Long> {
    Optional<SolicitudRegistro> findByCorreoAndEstado(String correo, String estado);
    List<SolicitudRegistro> findByEstado(String estado);
}