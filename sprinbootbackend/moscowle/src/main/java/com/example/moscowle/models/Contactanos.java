package com.example.moscowle.models;

import java.time.LocalDate;

import jakarta.persistence.*;

@Entity
public class Contactanos {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String nombre;


    private String correo;

    private String sujeto;

    @Column(columnDefinition = "TEXT")
    private String mensaje;

    private LocalDate fecha;

    @ManyToOne
    @JoinColumn(name = "id_usuario")
    private Usuario usuario;

    // Constructor vacío
    public Contactanos() {
        this.fecha = LocalDate.now();
    }
    
    // Constructor con parámetros
    public Contactanos(String nombre, String correo, String sujeto, String mensaje) {
        this.nombre = nombre;
        this.correo = correo;
        this.sujeto = sujeto;
        this.mensaje = mensaje;
        this.fecha = LocalDate.now();
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
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

    public LocalDate getFecha() {
        return fecha;
    }

    public void setFecha(LocalDate fecha) {
        this.fecha = fecha;
    }

    public Usuario getUsuario() {
        return usuario;
    }

    public void setUsuario(Usuario usuario) {
        this.usuario = usuario;
    }

    
}
