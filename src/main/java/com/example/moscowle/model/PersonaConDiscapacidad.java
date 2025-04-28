package com.example.moscowle.model;

import jakarta.persistence.*;
        import java.time.LocalDate;

@Entity
@Table(name = "persona_con_discapacidad")
public class PersonaConDiscapacidad {

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

    private String diagnostico;

    @Column(name = "fecha_nacimiento")
    private LocalDate fechaNacimiento;

    // Relación muchos a uno con Apoderado
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "apoderado_id", nullable = false)
    private Apoderado apoderado;

    // Constructor vacío
    public PersonaConDiscapacidad() {}

    // Constructor con parámetros
    public PersonaConDiscapacidad(Usuario usuario, String nombre, String apellido, String diagnostico, LocalDate fechaNacimiento, Apoderado apoderado) {
        this.usuario = usuario;
        this.nombre = nombre;
        this.apellido = apellido;
        this.diagnostico = diagnostico;
        this.fechaNacimiento = fechaNacimiento;
        this.apoderado = apoderado;
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

    public String getDiagnostico() {
        return diagnostico;
    }

    public void setDiagnostico(String diagnostico) {
        this.diagnostico = diagnostico;
    }

    public LocalDate getFechaNacimiento() {
        return fechaNacimiento;
    }

    public void setFechaNacimiento(LocalDate fechaNacimiento) {
        this.fechaNacimiento = fechaNacimiento;
    }

    public Apoderado getApoderado() {
        return apoderado;
    }

    public void setApoderado(Apoderado apoderado) {
        this.apoderado = apoderado;
    }
}