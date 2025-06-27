// src/main/java/com/moscowle/controller/SolicitudRegistroController.java

package com.example.moscowle.controllers;

import com.example.moscowle.models.SolicitudRegistro;
import com.example.moscowle.repository.SolicitudRegistroRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/registro")
public class SolicitudRegistroController {

    @Autowired
    private SolicitudRegistroRepository solicitudRepo;

    @PostMapping
    public ResponseEntity<SolicitudRegistro> registrarSolicitud(@RequestBody SolicitudRegistro solicitud) {
        solicitud.setEstado("PENDIENTE");
        return ResponseEntity.ok(solicitudRepo.save(solicitud));
    }

    @GetMapping
    public ResponseEntity<List<SolicitudRegistro>> obtenerSolicitudes() {
        return ResponseEntity.ok(solicitudRepo.findAll());
    }

    @PutMapping("/{id}/aprobar")
    public ResponseEntity<?> aprobarSolicitud(@PathVariable Long id) {
        SolicitudRegistro solicitud = solicitudRepo.findById(id).orElse(null);
        if (solicitud == null) return ResponseEntity.notFound().build();

        solicitud.setEstado("APROBADO");
        solicitudRepo.save(solicitud);
        return ResponseEntity.ok("Solicitud aprobada");
    }
}
