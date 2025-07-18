package com.example.moscowle.controllers;

import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import com.example.moscowle.models.Usuario;
import com.example.moscowle.models.dto.UsuarioNombreApellidoDTO;
import com.example.moscowle.service.UsuarioService;

import jakarta.servlet.http.HttpServletRequest;

@RestController
@RequestMapping("/api/usuarios")
@CrossOrigin(origins = "*") // o especifica tu origen frontend
public class UsuarioController {

    @Autowired
    private UsuarioService usuarioService;

    @GetMapping("/nombres-apellidos")
    public List<UsuarioNombreApellidoDTO> listarNombresYApellidos() {
        return usuarioService.obtenerNombresYApellidos();
    }

    
}
