// src/main/java/com/moscowle/controller/SolicitudRegistroController.java

package com.example.moscowle.controllers;

import com.example.moscowle.models.SolicitudRegistro;
import com.example.moscowle.service.RegistroService;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "http://localhost:4200")
public class SolicitudRegistroController {

    @Autowired
    private RegistroService registroService;

    @PostMapping("/registro")
    public ResponseEntity<?> registrarSolicitud(@RequestBody SolicitudRegistro solicitud) {
        try {
            System.out.println("Recibiendo solicitud de registro para: " + solicitud.getCorreo());
            
            SolicitudRegistro solicitudGuardada = registroService.crearSolicitud(solicitud);
            
            return ResponseEntity.ok(Map.of(
                "message", "Solicitud enviada correctamente. Pronto será revisada.",
                "solicitud", solicitudGuardada
            ));
            
        } catch (RuntimeException e) {
            System.err.println("Error en registro: " + e.getMessage());
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
            
        } catch (Exception e) {
            System.err.println("Error interno en registro: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", "Error interno del servidor"));
        }
    }

    @GetMapping("/registro")
    public ResponseEntity<Object> obtenerSolicitudes() {
        try {
            return ResponseEntity.ok(registroService.obtenerTodasLasSolicitudes());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    @PutMapping("/registro/{id}/aprobar")
    public ResponseEntity<?> aprobarSolicitud(@PathVariable Long id) {
        try {
            String passwordTemporal = generarPasswordTemporal();
            String mensaje = registroService.aprobarSolicitud(id, passwordTemporal);
            
            return ResponseEntity.ok(Map.of("message", mensaje));
            
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", "Error interno del servidor"));
        }
    }

    private String generarPasswordTemporal() {
        return "temp" + System.currentTimeMillis();
    }
}