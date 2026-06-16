import logging

logger = logging.getLogger('app')

ADMIN_FUNCTIONS = {
    'view_unpaid_users': {
        'group': 'Análisis de Deudores',
        'description': 'Ver lista de alumnos que no han pagado',
        'examples': [
            '¿Cuáles alumnos no han pagado?',
            '¿Quiénes son los morosos?',
            'Dame lista de deudores',
            '¿Cuánta deuda hay acumulada?',
        ],
        'parameters': [],
        'returns': 'Lista con nombres, montos adeudados, días de retraso',
    },
    'check_weekly_payments': {
        'group': 'Vencimientos',
        'description': 'Ver qué pagos vencen en los próximos 7 días',
        'examples': [
            '¿Qué pagos vencen pronto?',
            '¿Quién debe pagar próxima semana?',
            'Pagos de los próximos 7 días',
            '¿Ingresos esperados esta semana?',
        ],
        'parameters': [],
        'returns': 'Lista de pacientes y montos que vencen',
    },
    'analyze_finances': {
        'group': 'Análisis Financiero',
        'description': 'Ver estado financiero completo del mes',
        'examples': [
            '¿Cómo andan las finanzas?',
            '¿Cuál es el balance actual?',
            '¿Cuánto he ganado este mes?',
            'Status financiero',
        ],
        'parameters': [],
        'returns': 'Ingresos, egresos, ganancia neta, margen, cobranza %',
    },
    'calculate_breakeven': {
        'group': 'Rentabilidad',
        'description': 'Calcular cuántos alumnos necesita para una ganancia objetivo',
        'examples': [
            'Necesito ganar S/. 20000, ¿cuántos alumnos?',
            'Punto de equilibrio para S/. 15000',
            '¿Cuántos estudiantes para $X de ganancia?',
        ],
        'parameters': ['target_profit'],
        'returns': 'Alumnos necesarios, adicionales, factibilidad',
    },
    'optimize_schedule': {
        'group': 'Optimización',
        'description': 'Recibir recomendaciones de IA para mejorar horarios',
        'examples': [
            '¿Cómo mejoro los horarios?',
            'Sugerencias para optimizar agenda',
            'Recomendaciones de scheduling',
        ],
        'parameters': [],
        'returns': 'Recomendaciones basadas en datos',
    },
    'generate_report': {
        'group': 'Reportes',
        'description': 'Generar reporte completo del negocio',
        'examples': ['Dame un informe completo', 'Crea un reporte de hoy', 'Análisis completo de datos'],
        'parameters': [],
        'returns': 'Reporte formateado con todos los datos',
    },
    'register_payment': {
        'group': 'Pagos',
        'description': 'Registrar un pago de un paciente',
        'examples': ['Registra S/.500 para Juan', 'Cobré S/.300 a María', 'Nuevo ingreso de S/.450 por terapia'],
        'parameters': ['patient_name', 'amount'],
        'returns': 'Confirmación de pago registrado',
    },
    'create_appointment': {
        'group': 'Sesiones',
        'description': 'Agendar una nueva sesión/cita',
        'examples': [
            'Agendar sesión con Juan el lunes',
            'Nueva cita para María mañana a las 3pm',
            'Programar terapia con Pedro el miércoles',
        ],
        'parameters': ['patient_name', 'day', 'time'],
        'returns': 'Confirmación de sesión creada',
    },
    'view_sessions': {
        'group': 'Sesiones',
        'description': 'Ver todas las sesiones/citas programadas',
        'examples': ['Ver todas las sesiones', 'Mis citas programadas', 'Próximas sesiones de la semana'],
        'parameters': [],
        'returns': 'Calendario completo de citas',
    },
    'list_patients': {
        'group': 'Usuarios',
        'description': 'Ver lista de todos los pacientes activos',
        'examples': ['¿Cuántos pacientes activos hay?', 'Lista de todos los alumnos', 'Quiénes son mis pacientes'],
        'parameters': [],
        'returns': 'Lista de pacientes con info de contacto',
    },
    'create_expense': {
        'group': 'Gastos',
        'description': 'Registrar un nuevo gasto',
        'examples': ['Gasto de S/.250 en útiles', 'Registra costo de S/.500 para servicios', 'Nuevo egreso de S/.150'],
        'parameters': ['amount', 'category'],
        'returns': 'Confirmación de gasto registrado',
    },
    'assign_therapist': {
        'group': 'Usuarios',
        'description': 'Asignar terapeuta a un paciente',
        'examples': ['Asigna a Juan con el Dr. García', 'Terapeuta para María', 'Vincula a Pedro con especialista'],
        'parameters': ['patient_name', 'therapist_name'],
        'returns': 'Confirmación de asignación',
    },
    'navigate_to': {
        'group': 'Navegación',
        'description': 'Navegar a una sección específica del sistema',
        'examples': ['Llévame a deudores', 'Ir a gestión de pagos', 'Abre dashboard de reportes'],
        'parameters': ['target_section'],
        'returns': 'Redirección a la sección',
    },
}


class FunctionsTrainer:
    """Proporciona información sobre funciones disponibles a la IA"""

    @staticmethod
    def get_functions_prompt() -> str:
        """
        Retorna un prompt que entrena a la IA sobre funciones disponibles
        """
        prompt = """
=== FUNCIONES DISPONIBLES PARA EL ADMINISTRADOR ===

El administrador del Centro de Terapias puede usar este asistente para:

"""

        groups = {}
        for func_key, func_info in ADMIN_FUNCTIONS.items():
            group = func_info['group']
            if group not in groups:
                groups[group] = []
            groups[group].append(func_info)

        for group_name in sorted(groups.keys()):
            prompt += f'\n## {group_name.upper()}\n'
            for func in groups[group_name]:
                prompt += f'\n**{func["description"]}**\n'
                prompt += 'Ejemplos:\n'
                for example in func['examples']:
                    prompt += f'  • {example}\n'
                if func['parameters']:
                    prompt += f'Parámetros necesarios: {", ".join(func["parameters"])}\n'
                prompt += f'Resultado: {func["returns"]}\n'

        prompt += """
=== INSTRUCCIONES ===

1. Reconoce funciones por palabras clave similares
2. Si algo se parece a una función, intenta realizarla
3. Si falta información crítica, pide clarificación
4. Siempre usa los datos reales cargados en el contexto
5. Responde de forma concisa y práctica
6. Si el usuario pide algo que no está en la lista, ayuda como puedas

=== FIN DE FUNCIONES ===
"""

        return prompt

    @staticmethod
    def get_function_details(function_name: str) -> dict:
        """Retorna detalles de una función específica"""
        return ADMIN_FUNCTIONS.get(function_name, {})

    @staticmethod
    def list_functions_by_group() -> dict:
        """Retorna funciones agrupadas por categoría"""
        groups = {}
        for func_key, func_info in ADMIN_FUNCTIONS.items():
            group = func_info['group']
            if group not in groups:
                groups[group] = []
            groups[group].append(
                {'key': func_key, 'description': func_info['description'], 'examples': func_info['examples']}
            )
        return groups

    @staticmethod
    def can_do_function(user_query: str) -> list:
        """
        Detecta si el usuario está pidiendo una función específica
        Retorna lista de funciones posibles por relevancia
        """
        query_lower = user_query.lower()
        matches = []

        for func_key, func_info in ADMIN_FUNCTIONS.items():
            score = 0

            if any(word in query_lower for word in func_info['description'].lower().split()):
                score += 3

            for example in func_info['examples']:
                if any(word in query_lower for word in example.lower().split()):
                    score += 2

            if score > 0:
                matches.append((func_key, func_info, score))

        matches.sort(key=lambda x: x[2], reverse=True)
        return [{'function': m[0], 'info': m[1], 'score': m[2]} for m in matches]


functions_trainer = FunctionsTrainer()
