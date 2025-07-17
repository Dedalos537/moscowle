package com.example.moscowle.models.dto;

import jakarta.validation.constraints.*;

// DTO para recibir datos del formulario de contacto
public class ContactanosDTO {
    
    @NotBlank(message = "El nombre es obligatorio")
    @Size(max = 100, message = "El nombre no puede exceder 100 caracteres")
    private String nombre;
    
    @NotBlank(message = "El correo es obligatorio")
    @Email(message = "Formato de correo inválido")
    @Size(max = 100, message = "El correo no puede exceder 100 caracteres")
    private String correo;
    
    @NotBlank(message = "El sujeto es obligatorio")
    @Size(max = 200, message = "El sujeto no puede exceder 200 caracteres")
    private String sujeto;
    
    @NotBlank(message = "El mensaje es obligatorio")
    @Size(max = 5000, message = "El mensaje no puede exceder 5000 caracteres")
    private String mensaje;

    public ContactanosDTO() {
    }

    public ContactanosDTO(
            @NotBlank(message = "El nombre es obligatorio") @Size(max = 100, message = "El nombre no puede exceder 100 caracteres") String nombre,
            @NotBlank(message = "El correo es obligatorio") @Email(message = "Formato de correo inválido") @Size(max = 100, message = "El correo no puede exceder 100 caracteres") String correo,
            @NotBlank(message = "El sujeto es obligatorio") @Size(max = 200, message = "El sujeto no puede exceder 200 caracteres") String sujeto,
            @NotBlank(message = "El mensaje es obligatorio") @Size(max = 5000, message = "El mensaje no puede exceder 5000 caracteres") String mensaje) {
        this.nombre = nombre;
        this.correo = correo;
        this.sujeto = sujeto;
        this.mensaje = mensaje;
    }

    public String getNombre() {
        return nombre;
    }

    public void setNombre(String nombre) {
        this.nombre = nombre;
    }

    public String getCorreo() {
        return correo;
    }

    public void setCorreo(String correo) {
        this.correo = correo;
    }

    public String getSujeto() {
        return sujeto;
    }

    public void setSujeto(String sujeto) {
        this.sujeto = sujeto;
    }

    public String getMensaje() {
        return mensaje;
    }

    public void setMensaje(String mensaje) {
        this.mensaje = mensaje;
    }

    
}