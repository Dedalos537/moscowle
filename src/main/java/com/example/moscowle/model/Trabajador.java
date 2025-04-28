package com.example.moscowle.model;

import jakarta.persistence.*;
        import java.util.List;

@Entity
@Table(name = "trabajador")
public class Trabajador {

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

    private String cargo;

    private String especialidad;

    // Relación uno a muchos con Asignacion
    @OneToMany(mappedBy = "trabajador", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Asignacion> asignaciones;

    // Constructor vacío
    public Trabajador() {}

    // Constructor con parámetros
    public Trabajador(Usuario usuario, String nombre, String apellido, String cargo, String especialidad) {
        this.usuario = usuario;
        this.nombre = nombre;
        this.apellido = apellido;
        this.cargo = cargo;
        this.especialidad = especialidad;
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

    public String getCargo() {
        return cargo;
    }

    public void setCargo(String cargo) {
        this.cargo = cargo;
    }

    public String getEspecialidad() {
        return especialidad;
    }

    public void setEspecialidad(String especialidad) {
        this.especialidad = especialidad;
    }

    public List<Asignacion> getAsignaciones() {
        return asignaciones;
    }

    public void setAsignaciones(List<Asignacion> asignaciones) {
        this.asignaciones = asignaciones;
    }
}