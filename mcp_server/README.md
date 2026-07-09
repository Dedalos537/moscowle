# Moscowle IA - Servidor MCP

Servidor Model Context Protocol (MCP) que permite a **Claude Desktop** acceder directamente a los datos del sistema de terapia digital Moscowle IA.

## Instalación

### 1. Instalar dependencias

```bash
cd /Users/apple/Documents/moscowle_ia/mcp_server
uv sync
```

### 2. Configurar Claude Desktop

Copia el contenido de `claude_desktop_config.json` a la configuración de Claude Desktop:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

O ejecuta el script de instalación:

```bash
./install.sh
```

### 3. Reiniciar Claude Desktop

Cierra y vuelve a abrir Claude Desktop para que detecte el nuevo servidor MCP.

## Tools Disponibles

### Pacientes
| Tool | Descripción |
|------|-------------|
| `listar_pacientes` | Lista todos los pacientes activos |
| `obtener_paciente` | Detalle completo de un paciente |
| `buscar_pacientes` | Buscar por nombre, email o tutor |

### Sesiones
| Tool | Descripción |
|------|-------------|
| `listar_sesiones` | Citas con filtros (paciente, terapeuta, estado) |
| `obtener_sesion` | Detalle de sesión con métricas e imágenes |

### Métricas y IA
| Tool | Descripción |
|------|-------------|
| `obtener_metricas_paciente` | Métricas de juego de un paciente |
| `obtener_predicciones_ia` | Historial de predicciones SVM |
| `resumen_terapeuta` | Resumen del terapeuta con estadísticas |
| `estadisticas_generales` | Estadísticas globales del sistema |

### Juegos y Pagos
| Tool | Descripción |
|------|-------------|
| `listar_juegos` | Juegos terapéuticos disponibles |
| `pagos_paciente` | Historial de pagos de un paciente |

## Prompts Predefinidos

- **analizar_paciente**: Análisis completo del progreso de un paciente
- **reporte_semanal**: Reporte semanal para terapeutas

## Ejemplo de Uso en Claude Desktop

```
Analiza al paciente ID 5: su progreso, métricas y predicciones de IA.
¿Necesita algún ajuste en su tratamiento?
```

```
Dame un resumen de las sesiones de esta semana del terapeuta ID 3.
¿Qué pacientes necesitan seguimiento?
```

```
Compara las métricas de los pacientes del terapeuta 2.
¿Quién está mejorando más rápido?
```

## Seguridad

- Solo accede a datos de la base de datos SQLite local
- No expone endpoints HTTP externos
- No modifica datos (solo lectura)
- Requiere acceso local a la máquina
