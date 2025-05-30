// src/main/java/com/example/moscowle/models/dto/UsuarioDTO.java
package com.example.moscowle.models.dto;

public class UsuarioDTO {
    private Integer id;
    private String correo;
    private String rol;

    public UsuarioDTO(Integer id, String correo, String rol) {
        this.id = id;
        this.correo = correo;
        this.rol = rol;
    }

    public Integer getId() {
        return id;
    }

    public String getCorreo() {
        return correo;
    }

    public String getRol() {
        return rol;
    }
}
