package com.example.moscowle.model;

import jakarta.persistence.*;
        import java.util.List;

@Entity
@Table(name = "apoderado")
public class Apoderado {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    // Relación uno a uno con Usuario
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "usuario_id", nullable = false)
    private Usuario usuario;

    @Column(nullable = false)
    private String nombre;

    @Column(nullable = false)
    private String apellido;

    private String telefono;

    private String direccion;

    // Relación uno a muchos con Asignacion
    @OneToMany(mappedBy = "apoderado", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Asignacion> asignaciones;

    // Relación uno a muchos con PersonaConDiscapacidad (representado por)
    @OneToMany(mappedBy = "apoderado", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<PersonaConDiscapacidad> personasConDiscapacidad;

    // Constructor vacío
    public Apoderado() {}

    // Constructor con parámetros
    public Apoderado(Usuario usuario, String nombre, String apellido, String telefono, String direccion) {
        this.usuario = usuario;
        this.nombre = nombre;
        this.apellido = apellido;
        this.telefono = telefono;
        this.direccion = direccion;
    }

    // Getters y Setters
    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public Usuario getUsuario() {
        return usuario;
    }

    public void setUsuario(Usuario usuario) {
        this.usuario = usuario;
    }

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

    public String getTelefono() {
        return telefono;
    }

    public void setTelefono(String telefono) {
        this.telefono = telefono;
    }

    public String getDireccion() {
        return direccion;
    }

    public void setDireccion(String direccion) {
        this.direccion = direccion;
    }

    public List<Asignacion> getAsignaciones() {
        return asignaciones;
    }

    public void setAsignaciones(List<Asignacion> asignaciones) {
        this.asignaciones = asignaciones;
    }

    public List<PersonaConDiscapacidad> getPersonasConDiscapacidad() {
        return personasConDiscapacidad;
    }

    public void setPersonasConDiscapacidad(List<PersonaConDiscapacidad> personasConDiscapacidad) {
        this.personasConDiscapacidad = personasConDiscapacidad;
    }
}