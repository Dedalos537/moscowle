package com.example.moscowle.controllers;

import com.example.moscowle.models.Contactanos;
import com.example.moscowle.service.ContactanosService;
import com.example.moscowle.models.dto.ContactanosDTO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindingResult;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/contactanos")
@CrossOrigin(origins = "http://localhost:3000") // Permitir todas las origins para desarrollo
public class ContactanosController {
    
    @Autowired
    private ContactanosService contactanosService;
    
    // Endpoint principal para recibir mensajes de contacto
    @PostMapping
    public ResponseEntity<Map<String, Object>> crearContacto(@Valid @RequestBody ContactanosDTO contactoDTO, 
                                                           BindingResult bindingResult) {
        Map<String, Object> response = new HashMap<>();
        
        try {
            // Validar errores de binding
            if (bindingResult.hasErrors()) {
                Map<String, String> errors = new HashMap<>();
                bindingResult.getFieldErrors().forEach(error -> 
                    errors.put(error.getField(), error.getDefaultMessage()));
                
                response.put("success", false);
                response.put("message", "Errores de validación");
                response.put("errors", errors);
                return ResponseEntity.badRequest().body(response);
            }
            
            // Validar datos adicionales
            if (!contactanosService.validarContacto(contactoDTO)) {
                response.put("success", false);
                response.put("message", "Todos los campos son obligatorios");
                return ResponseEntity.badRequest().body(response);
            }
            
            // Guardar contacto
            Contactanos contactoGuardado = contactanosService.guardarContacto(contactoDTO);
            
            response.put("success", true);
            response.put("message", "¡Mensaje enviado con éxito! Nos comunicaremos contigo pronto.");
            response.put("id", contactoGuardado.getId());
            response.put("fecha", contactoGuardado.getFecha().toString());
            
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            response.put("success", false);
            response.put("message", "Error interno del servidor: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }

    @GetMapping
    public ResponseEntity<?> listarContactos() {
        try {
            return ResponseEntity.ok(contactanosService.listarContactos());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("Error al obtener mensajes");
        }
    }

}
