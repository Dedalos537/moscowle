package com.example.moscowle.controllers;

import com.example.moscowle.service.AuthService; 
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus; 
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class AuthController {

    @Autowired
    private AuthService authService;

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> loginData) {
        String correo = loginData.get("email");
        String rawPassword = loginData.get("password"); 

    
        Map<String, Object> responseData = authService.login(correo, rawPassword);

        if (responseData == null) {
    
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body("Credenciales inválidas o acceso no autorizado");
        }

        System.out.println("Login exitoso para: " + correo); 

        return ResponseEntity.ok(responseData);
    }
}