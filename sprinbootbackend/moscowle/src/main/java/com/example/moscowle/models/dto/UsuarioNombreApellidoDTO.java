package com.example.moscowle.models.dto;

public class UsuarioNombreApellidoDTO {
    private String nombre;
    private String apellido;

    public UsuarioNombreApellidoDTO(String nombre, String apellido) {
        this.nombre = nombre;
        this.apellido = apellido;
    }

    // Getters y setters
    public String getNombre() {
        return nombre;
    }

    public void setNombre(String nombre) {
        this.nombre = nombre;
    }

    public String getApellido() {
        return apellido;
    }

    public void setApellido(String apellido) {
        this.apellido = apellido;
    }
}