package com.example.moscowle.service;

import java.time.LocalDateTime;
import java.util.Optional;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import com.example.moscowle.models.Apoderado;
import com.example.moscowle.models.Rol;
import com.example.moscowle.models.SolicitudRegistro;
import com.example.moscowle.models.Usuario;
import com.example.moscowle.repository.ApoderadoRepository;
import com.example.moscowle.repository.RolRepository;
import com.example.moscowle.repository.SolicitudRegistroRepository;
import com.example.moscowle.repository.UsuarioRepository;

import jakarta.transaction.Transactional;

@Service
public class RegistroService {

    @Autowired
    private SolicitudRegistroRepository solicitudRepo;

    @Autowired
    private UsuarioRepository usuarioRepository;

    @Autowired
    private RolRepository rolRepository;

    @Autowired
    private ApoderadoRepository apoderadoRepository;

    @Autowired
    private BCryptPasswordEncoder passwordEncoder;

    public SolicitudRegistro crearSolicitud(SolicitudRegistro solicitud) {
        // Validar que el correo no esté ya registrado
        if (usuarioRepository.findByCorreo(solicitud.getCorreo()).isPresent()) {
            throw new RuntimeException("El correo ya está registrado en el sistema");
        }

        // Validar que no haya solicitud pendiente con el mismo correo
        Optional<SolicitudRegistro> solicitudExistente = solicitudRepo.findByCorreoAndEstado(
            solicitud.getCorreo(), "PENDIENTE");
        
        if (solicitudExistente.isPresent()) {
            throw new RuntimeException("Ya existe una solicitud pendiente para este correo");
        }

        solicitud.setEstado("PENDIENTE");
        // No asignar fechaAprobacion aquí
        
        return solicitudRepo.save(solicitud);
    }

    @Transactional
    public String aprobarSolicitud(Long id, String passwordTemporal) {
        SolicitudRegistro solicitud = solicitudRepo.findById(id)
            .orElseThrow(() -> new RuntimeException("Solicitud no encontrada"));

        if ("APROBADO".equals(solicitud.getEstado())) {
            throw new RuntimeException("La solicitud ya fue aprobada");
        }

        // Buscar o crear rol USER
        Rol rolUser = rolRepository.findByNombre("USER")
                .orElseGet(() -> {
                    Rol nuevoRol = new Rol("USER");
                    return rolRepository.save(nuevoRol);
                });

        // Crear usuario
        Usuario usuario = new Usuario();
        usuario.setCorreo(solicitud.getCorreo());
        usuario.setContrasena(passwordEncoder.encode(passwordTemporal));
        usuario.setRol(rolUser);
        usuario = usuarioRepository.save(usuario);

        // Crear apoderado asociado
        Apoderado apoderado = new Apoderado();
        apoderado.setNombre(solicitud.getNombre());
        apoderado.setApellido(""); 
        apoderado.setUsuario(usuario);
        apoderadoRepository.save(apoderado);

        // Actualizar solicitud
        solicitud.setEstado("APROBADO");
        solicitud.setFechaAprobacion(LocalDateTime.now()); 
        solicitudRepo.save(solicitud);

        return "Solicitud aprobada correctamente. Contraseña temporal: " + passwordTemporal;
    }

    public Object obtenerTodasLasSolicitudes() {
        return solicitudRepo.findAll();
    }
}