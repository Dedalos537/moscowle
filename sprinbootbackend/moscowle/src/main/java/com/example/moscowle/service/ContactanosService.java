package com.example.moscowle.service;

import java.time.LocalDate;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;

import com.example.moscowle.models.Contactanos;
import com.example.moscowle.models.dto.ContactanosDTO;
import com.example.moscowle.repository.ContactanosRepository;
import java.util.List;

@Service
@Transactional
public class ContactanosService {
    
    
    @Autowired
    private ContactanosRepository contactanosRepository;
    
    // Guardar nuevo mensaje de contacto
    public Contactanos guardarContacto(ContactanosDTO contactoDTO) {
        try {
            Contactanos contacto = new Contactanos();
            contacto.setNombre(contactoDTO.getNombre());
            contacto.setCorreo(contactoDTO.getCorreo());
            contacto.setSujeto(contactoDTO.getSujeto());
            contacto.setMensaje(contactoDTO.getMensaje());
            contacto.setFecha(LocalDate.now());
            
            return contactanosRepository.save(contacto);
        } catch (Exception e) {
            throw new RuntimeException("Error al guardar el mensaje de contacto: " + e.getMessage());
        }
    }

    // Validar datos del contacto
    public boolean validarContacto(ContactanosDTO contactoDTO) {
        return contactoDTO.getNombre() != null && !contactoDTO.getNombre().trim().isEmpty() &&
               contactoDTO.getCorreo() != null && !contactoDTO.getCorreo().trim().isEmpty() &&
               contactoDTO.getSujeto() != null && !contactoDTO.getSujeto().trim().isEmpty() &&
               contactoDTO.getMensaje() != null && !contactoDTO.getMensaje().trim().isEmpty();
    }
    // Listar todos los contactos
public List<Contactanos> listarTodos() {
    return contactanosRepository.findAll();
}

}
