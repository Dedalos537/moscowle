    package com.example.moscowle.controllers;

    import com.example.moscowle.models.Usuario;
import com.example.moscowle.models.dto.UsuarioDTO;
import com.example.moscowle.service.UsuarioService;
    import org.springframework.beans.factory.annotation.Autowired;
    import org.springframework.web.bind.annotation.*;

    import java.util.List;

    @RestController
    @RequestMapping("/api/usuarios")
    @CrossOrigin(origins = "*") // Ajusta si deseas restringir
    public class UsuarioController {

        @Autowired
        private UsuarioService usuarioService;

       @GetMapping("/listar")
public List<UsuarioDTO> listarUsuarios() {
    return usuarioService.listarUsuarios()
            .stream()
            .map(usuario -> new UsuarioDTO(
                usuario.getId(),
                usuario.getCorreo(),
                usuario.getRol().getNombre()
            ))
            .toList();
}

        // Crear nuevo usuario
        @PostMapping
        public Usuario crearUsuario(@RequestBody Usuario usuario) {
            return usuarioService.guardarUsuario(usuario);
        }

        // Actualizar usuario
        @PutMapping("/{id}")
        public Usuario actualizarUsuario(@PathVariable Integer id, @RequestBody Usuario usuario) {
            return usuarioService.actualizarUsuario(id, usuario);
        }

        // Eliminar usuario
        @DeleteMapping("/{id}")
        public void eliminarUsuario(@PathVariable Integer id) {
            usuarioService.eliminarUsuario(id);
        }
    }
