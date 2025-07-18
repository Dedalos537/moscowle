package com.example.moscowle.service;

import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.example.moscowle.models.Usuario;
import com.example.moscowle.models.dto.UsuarioNombreApellidoDTO;
import com.example.moscowle.repository.UsuarioRepository;

@Service
public class UsuarioService {
    @Autowired
    private UsuarioRepository usuarioRepository;

    public List<UsuarioNombreApellidoDTO> obtenerNombresYApellidos() {
        List<Usuario> lista = usuarioRepository.findByNombreIsNotNullAndApellidoIsNotNull();
        return lista.stream()
                .map(usuario -> new UsuarioNombreApellidoDTO(usuario.getNombre(), usuario.getApellido()))
                .toList();
    }
}
