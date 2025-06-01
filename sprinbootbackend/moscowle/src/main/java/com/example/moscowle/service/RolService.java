package com.example.moscowle.service;
import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.example.moscowle.models.Rol;
import com.example.moscowle.repository.RolRepository;

@Service 
public class RolService {
    @Autowired
    private RolRepository rolRepository;

    public List<Rol> listarRoles() {
        return rolRepository.findAll();
    }

    public Rol guardarRol(Rol rol) {
        return rolRepository.save(rol);
    }

    public void eliminarRol(Integer id) {
        rolRepository.deleteById(id);
    }

    public Rol obtenerPorId(Integer id) {
        return rolRepository.findById(id).orElse(null);
    }
}
