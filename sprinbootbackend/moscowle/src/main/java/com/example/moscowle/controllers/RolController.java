package com.example.moscowle.controllers;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.example.moscowle.models.Rol;
import com.example.moscowle.service.RolService;

import java.util.List;

@RestController
@RequestMapping("/api/roles")
@CrossOrigin(origins = "*") // Ajusta según tu configuración de CORS

public class RolController {
    @Autowired
    private RolService rolService;

    @GetMapping("/listar")
    public List<Rol> listarRoles() {
        return rolService.listarRoles();
    }

    @PostMapping
    public Rol guardarRol(@RequestBody Rol rol) {
        return rolService.guardarRol(rol);
    }

    @DeleteMapping("/{id}")
    public void eliminarRol(@PathVariable Integer id) {
        rolService.eliminarRol(id);
    }

    @GetMapping("/{id}")
    public Rol obtenerRol(@PathVariable Integer id) {
        return rolService.obtenerPorId(id);
    }
}
