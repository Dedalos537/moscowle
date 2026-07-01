"""
Moscowle IA - MCP Server
Permite a Claude Desktop acceder a los datos del sistema de terapia digital.
Conecta a la API de producción en Railway.
"""

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

# URL del backend en Railway
API_BASE_URL = os.getenv(
    'MOSCOWLE_API_URL',
    'https://moscowle-backend-production.up.railway.app',
)

# API Key para autenticación
API_KEY = os.getenv(
    'MOSCOWLE_API_KEY',
    'moscowle_mcp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0',
)

mcp = FastMCP(
    'Moscowle IA',
    instructions=(
        'Servidor MCP para el sistema de terapia digital Moscowle IA. '
        'Permite consultar pacientes, sesiones, métricas y predicciones de IA.'
    ),
)


def api_get(endpoint: str, params: dict | None = None) -> dict:
    """Hacer GET request a la API de Moscowle."""
    url = f'{API_BASE_URL}/api/mcp/{endpoint}'
    headers = {'X-API-Key': API_KEY, 'Content-Type': 'application/json'}

    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


# ============================================================
# TOOLS - Pacientes
# ============================================================


@mcp.tool()
def listar_pacientes(terapist_id: int | None = None) -> str:
    """
    Listar todos los pacientes activos del sistema.
    Opcionalmente filtrar por ID de terapeuta.

    Args:
        terapist_id: ID del terapeuta para filtrar sus pacientes asignados
    """
    params = {}
    if terapist_id:
        params['therapist_id'] = terapist_id
    return json.dumps(api_get('pacientes', params), ensure_ascii=False, default=str)


@mcp.tool()
def obtener_paciente(patient_id: int) -> str:
    """
    Obtener detalles completos de un paciente específico incluyendo métricas recientes.

    Args:
        patient_id: ID del paciente
    """
    return json.dumps(api_get(f'paciente/{patient_id}'), ensure_ascii=False, default=str)


@mcp.tool()
def buscar_pacientes(termino: str) -> str:
    """
    Buscar pacientes por nombre o email.

    Args:
        termino: Texto de búsqueda
    """
    # Primero obtener todos y filtrar localmente
    all_patients = api_get('pacientes')
    if isinstance(all_patients, list):
        resultados = [
            p
            for p in all_patients
            if termino.lower() in (p.get('username', '').lower() or '')
            or termino.lower() in (p.get('email', '').lower() or '')
            or termino.lower() in (p.get('guardian_name', '').lower() or '')
        ]
        return json.dumps(resultados[:20], ensure_ascii=False, default=str)
    return json.dumps([], ensure_ascii=False)


# ============================================================
# TOOLS - Sesiones
# ============================================================


@mcp.tool()
def listar_sesiones(
    patient_id: int | None = None,
    therapist_id: int | None = None,
    estado: str | None = None,
    dias: int = 30,
) -> str:
    """
    Listar sesiones/citas del sistema con filtros opcionales.

    Args:
        patient_id: Filtrar por paciente específico
        therapist_id: Filtrar por terapeuta específico
        estado: Filtrar por estado (scheduled, completed, cancelled, in_progress)
        dias: Número de días hacia atrás para buscar (default: 30)
    """
    params = {'dias': dias}
    if patient_id:
        params['patient_id'] = patient_id
    if therapist_id:
        params['therapist_id'] = therapist_id
    if estado:
        params['estado'] = estado
    return json.dumps(api_get('sesiones', params), ensure_ascii=False, default=str)


# ============================================================
# TOOLS - Métricas y IA
# ============================================================


@mcp.tool()
def obtener_metricas_paciente(patient_id: int, juego: str | None = None) -> str:
    """
    Obtener métricas de desempeño de un paciente en juegos terapéuticos.

    Args:
        patient_id: ID del paciente
        juego: Nombre del juego específico (opcional)
    """
    params = {}
    if juego:
        params['juego'] = juego
    return json.dumps(api_get(f'metricas/{patient_id}', params), ensure_ascii=False, default=str)


@mcp.tool()
def obtener_predicciones_ia(patient_id: int) -> str:
    """
    Obtener el historial de predicciones de IA (SVM) para un paciente.
    Predicciones: 0=mantener nivel, 1=avanzar, 2=retroceder/apoyo.

    Args:
        patient_id: ID del paciente
    """
    data = api_get(f'metricas/{patient_id}')
    if 'metricas' in data:
        metricas = data['metricas']
        if metricas:
            pred_recientes = [m['prediction'] for m in metricas[:5]]
            if pred_recientes:
                tendencia = 'estable'
                if pred_recientes.count(1) > len(pred_recientes) / 2:
                    tendencia = 'mejorando'
                elif pred_recientes.count(2) > len(pred_recientes) / 2:
                    tendencia = 'necesita apoyo'
            else:
                tendencia = 'sin datos suficientes'

            resumen = {
                'total_predicciones': len(metricas),
                'tendencia_reciente': tendencia,
                'distribucion': {
                    'avanzar': sum(1 for m in metricas if m['prediction'] == 1),
                    'mantener': sum(1 for m in metricas if m['prediction'] == 0),
                    'apoyo': sum(1 for m in metricas if m['prediction'] == 2),
                },
            }
            return json.dumps({'resumen': resumen, 'predicciones': metricas}, ensure_ascii=False, default=str)
    return json.dumps({'resumen': {'total_predicciones': 0}, 'predicciones': []}, ensure_ascii=False)


@mcp.tool()
def estadisticas_generales() -> str:
    """
    Obtener estadísticas generales del sistema Moscowle IA.
    """
    return json.dumps(api_get('estadisticas'), ensure_ascii=False, default=str)


@mcp.tool()
def listar_juegos() -> str:
    """
    Listar todos los juegos terapéuticos disponibles en el sistema.
    """
    return json.dumps(api_get('juegos'), ensure_ascii=False, default=str)


@mcp.tool()
def resumen_terapeuta(therapist_id: int) -> str:
    """
    Obtener resumen general del terapeuta: pacientes asignados y sesiones recientes.

    Args:
        therapist_id: ID del terapeuta
    """
    pacientes = api_get('pacientes', {'therapist_id': therapist_id})
    sesiones = api_get('sesiones', {'therapist_id': therapist_id, 'dias': 30})

    # Calcular estadísticas
    total_sesiones = len(sesiones) if isinstance(sesiones, list) else 0
    completadas = sum(1 for s in sesiones if s.get('status') == 'completed') if isinstance(sesiones, list) else 0
    programadas = sum(1 for s in sesiones if s.get('status') == 'scheduled') if isinstance(sesiones, list) else 0

    return json.dumps(
        {
            'pacientes': pacientes,
            'sesiones_recientes': sesiones[:20] if isinstance(sesiones, list) else [],
            'estadisticas_30_dias': {
                'total': total_sesiones,
                'completadas': completadas,
                'programadas': programadas,
            },
        },
        ensure_ascii=False,
        default=str,
    )


# ============================================================
# TOOLS - Incidencias
# ============================================================


@mcp.tool()
def listar_incidencias(
    estado: str | None = None,
    prioridad: int | None = None,
    categoria: str | None = None,
    limite: int = 20,
) -> str:
    """
    Listar incidencias del sistema con filtros opcionales.

    Args:
        estado: Filtrar por estado (NUEVO, EN_CURSO, PENDIENTE_PROVEEDOR, RESUELTO, CERRADO)
        prioridad: Filtrar por prioridad (1=Critica, 2=Alta, 3=Media, 4=Baja)
        categoria: Filtrar por categoría (HARDWARE, SOFTWARE, RED, ACCESOS, OPERACIONES)
        limite: Número máximo de resultados (default: 20)
    """
    params = {'limite': limite}
    if estado:
        params['estado'] = estado
    if prioridad:
        params['prioridad'] = prioridad
    if categoria:
        params['categoria'] = categoria
    return json.dumps(api_get('incidencias', params), ensure_ascii=False, default=str)


@mcp.tool()
def obtener_incidencia(incident_id: int) -> str:
    """
    Obtener detalle completo de una incidencia incluyendo historial y comentarios.

    Args:
        incident_id: ID de la incidencia
    """
    return json.dumps(api_get(f'incidente/{incident_id}'), ensure_ascii=False, default=str)


@mcp.tool()
def estadisticas_incidencias() -> str:
    """
    Obtener KPIs del sistema de incidencias: abiertas, vencidas, por categoría, SLA compliance %.
    """
    return json.dumps(api_get('incidencias/estadisticas'), ensure_ascii=False, default=str)


@mcp.tool()
def analizar_tendencia_incidencias(dias: int = 30) -> str:
    """
    Analizar tendencia de incidencias: patrones recurrentes, categorías críticas.

    Args:
        dias: Número de días hacia atrás para el análisis (default: 30)
    """
    return json.dumps(api_get('incidencias/tendencia', {'dias': dias}), ensure_ascii=False, default=str)


# ============================================================
# RECURSOS
# ============================================================


@mcp.resource('moscowle://database-info')
def database_info() -> str:
    """Información sobre la conexión a Moscowle IA."""
    return f"""
Servidor: Moscowle IA - Sistema de Terapia Digital
API: {API_BASE_URL}
Estado: Conectado

Endpoints disponibles:
- /api/mcp/pacientes - Listar pacientes
- /api/mcp/paciente/<id> - Detalle de paciente
- /api/mcp/sesiones - Listar sesiones
- /api/mcp/metricas/<id> - Métricas de paciente
- /api/mcp/estadisticas - Estadísticas generales
- /api/mcp/juegos - Juegos terapéuticos
- /api/mcp/incidencias - Listar incidencias
- /api/mcp/incidente/<id> - Detalle de incidencia
- /api/mcp/incidencias/estadisticas - KPIs de incidencias
- /api/mcp/incidencias/tendencia - Análisis de tendencia
"""


# ============================================================
# PROMPTS
# ============================================================


@mcp.prompt()
def analizar_paciente(patient_id: int) -> str:
    """
    Prompt para analizar el progreso de un paciente específico.
    """
    return f"""
Eres un asistente de terapia digital especializado en neuroeducación.

Analiza los datos del paciente ID {patient_id} de Moscowle IA y proporciona:

1. **Resumen del paciente**: Datos generales y contexto
2. **Análisis de métricas**: Precisión, tiempo de respuesta, tendencias
3. **Predicciones de IA**: Qué significan las predicciones SVM (0=mantener, 1=avanzar, 2=apoyo)
4. **Recomendaciones**: Sugerencias para el terapeuta basadas en los datos
5. **Alertas**: Si hay señales de que el paciente necesita atención especial

Usa las tools disponibles para obtener los datos necesarios.
"""


@mcp.prompt()
def reporte_semanal(therapist_id: int) -> str:
    """
    Prompt para generar un reporte semanal del terapeuta.
    """
    return f"""
Eres un analista de datos clínicos para terapia digital.

Genera un reporte semanal para el terapeuta ID {therapist_id} de Moscowle IA:

1. **Resumen ejecutivo**: Actividad de la semana
2. **Pacientes atendidos**: Quiénes, cuántas sesiones, asistencia
3. **Métricas destacadas**: Mejores y peores desempeños
4. **Tendencias**: Mejoras o declives en el progreso
5. **Recomendaciones**: Acciones sugeridas para la próxima semana
6. **Alertas**: Pacientes que requieren seguimiento especial

Usa las tools disponibles para obtener la información necesaria.
"""


if __name__ == '__main__':
    mcp.run()
