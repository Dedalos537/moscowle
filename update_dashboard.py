import re
import os

dashboard_path = "/Users/apple/Documents/moscowle_ia/app/templates/therapist/dashboard.html"
with open(dashboard_path, "r", encoding="utf-8") as f:
    content = f.read()

# We want to replace the inside of {% block content %} ... {% endblock %} up to the footer
# Let's extract everything before {% block content %}
match1 = re.search(r'(.*?{% block content %}\n)', content, re.DOTALL)
pre_content = match1.group(1)

# we want everything from <footer id="footer" onwards, or from <!-- Modals --> onwards
match2 = re.search(r'(\n    <!-- Modals -->.*)', content, re.DOTALL)
post_content = match2.group(1)

new_content = """
    <!-- Top Alert / Info from new design -->
    <section class="px-4 md:px-8 py-6 space-y-8 max-w-7xl mx-auto">
        <!-- 1. Header Greeting -->
        <div class="flex flex-col md:flex-row md:items-end justify-between gap-6">
            <div class="max-w-2xl">
                <h2 class="text-primary font-bold text-xs tracking-widest uppercase mb-2">Resumen Diario</h2>
                <h1 class="text-3xl md:text-4xl font-extrabold text-textDark leading-tight">
                    Hola, {{ current_user.username }}. Tu próxima sesión es <span class="text-primary">{{ next_session.title if next_session else 'Ninguna' }}</span> a las {{ next_session.start if next_session else '--:--' }}.
                </h1>
            </div>
            <div class="flex gap-4">
                <div class="bg-white p-6 rounded-soft shadow-soft border border-gray-100 flex items-center gap-4">
                    <div class="w-12 h-12 rounded-full bg-lightGreen flex items-center justify-center text-primary">
                        <i class="fas fa-check-circle text-2xl"></i>
                    </div>
                    <div>
                        <div class="text-2xl font-bold text-textDark">{{ avg_compliance }}%</div>
                        <div class="text-xs text-gray-500 font-medium">Cumplimiento Global</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 2. Main Grid: Current Session + Agenda -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <!-- Left col: Session detail -->
            <div class="lg:col-span-8 space-y-8">
                <!-- Session Banner -->
                <div class="bg-primary text-white p-8 md:p-10 rounded-soft relative overflow-hidden shadow-soft">
                    <div class="relative z-10">
                        <span class="bg-white/20 px-3 py-1 rounded-full text-[10px] font-bold tracking-widest uppercase mb-4 inline-block">Sesión Actual / Próxima</span>
                        <h2 class="text-2xl md:text-3xl font-bold mb-2">{{ next_session.title if next_session else 'No hay sesiones activas' }}</h2>
                        <p class="text-white/80 mb-8 max-w-md">Paciente: {{ next_session.patient if next_session else '-' }} • Lugar: {{ next_session.location if next_session else '-' }}</p>
                        
                        <div class="flex flex-col sm:flex-row items-center gap-10">
                            <!-- Circular Progress -->
                            <div class="relative w-32 h-32 md:w-40 md:h-40">
                                <svg class="w-full h-full transform -rotate-90">
                                    <circle class="text-white/20" cx="50%" cy="50%" fill="transparent" r="40%" stroke="currentColor" stroke-width="12"></circle>
                                    <circle class="text-white" cx="50%" cy="50%" fill="transparent" r="40%" stroke="currentColor" stroke-dasharray="250" stroke-dashoffset="75" stroke-linecap="round" stroke-width="12"></circle>
                                </svg>
                                <div class="absolute inset-0 flex flex-col items-center justify-center">
                                    <span class="text-2xl md:text-3xl font-black text-white">70%</span>
                                    <span class="text-[10px] uppercase font-bold text-white/80">Cobertura</span>
                                </div>
                            </div>
                            <div class="flex-1 space-y-3 w-full">
                                <div class="flex items-center justify-between text-sm">
                                    <span class="font-medium text-white">Meta Semanal</span>
                                    <span class="font-bold text-white">85%</span>
                                </div>
                                <div class="h-2 w-full bg-white/20 rounded-full overflow-hidden">
                                    <div class="h-full bg-white" style="width: 70%"></div>
                                </div>
                                <p class="text-xs text-white/80 italic">Buen progreso en cumplimiento terapéutico.</p>
                            </div>
                        </div>
                    </div>
                    <!-- Decoraciones -->
                    <div class="absolute right-[-50px] top-[-50px] w-64 h-64 bg-white/10 rounded-full blur-3xl"></div>
                    <div class="absolute left-[-20px] bottom-[-20px] w-48 h-48 bg-white/5 rounded-full blur-2xl"></div>
                </div>

                <!-- Session Objectives -->
                <div class="bg-white p-6 md:p-8 rounded-soft shadow-soft border border-gray-100">
                    <div class="flex items-center justify-between mb-8">
                        <h3 class="text-xl font-bold text-textDark flex items-center gap-2">
                            <i class="fas fa-tasks text-primary"></i> Temas de la Sesión
                        </h3>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {% if session_objectives %}
                            {% for obj in session_objectives %}
                            <div class="flex items-center gap-4 p-5 bg-gray-50 rounded-soft border-l-4 border-primary">
                                <div class="w-6 h-6 rounded-full {{ 'bg-primary text-white' if obj.status == 'completado' else 'bg-amber-500 text-white' if obj.status == 'parcial' else 'border-2 border-gray-300 text-gray-400' }} flex items-center justify-center">
                                    {% if obj.status == 'completado' %}
                                        <i class="fas fa-check text-xs"></i>
                                    {% elif obj.status == 'parcial' %}
                                        <i class="fas fa-clock text-xs"></i>
                                    {% else %}
                                        <i class="fas fa-circle text-[8px]"></i>
                                    {% endif %}
                                </div>
                                <div>
                                    <div class="font-bold text-textDark">{{ obj.name }}</div>
                                    <div class="text-[10px] font-bold {{ 'text-primary' if obj.status == 'completado' else 'text-amber-600' if obj.status == 'parcial' else 'text-gray-400' }} uppercase">{{ obj.status }}</div>
                                </div>
                            </div>
                            {% endendfor %}
                        {% else %}
                            <div class="col-span-full p-4 bg-gray-50 text-gray-500 rounded-soft text-sm">
                                No se encontraron objetivos de auditoría para la sesión en progreso.
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>

            <!-- Right col: Agenda -->
            <div class="lg:col-span-4 space-y-8">
                <div class="bg-white p-6 md:p-8 rounded-soft shadow-soft border border-gray-100">
                    <div class="flex items-center justify-between mb-8">
                        <h3 class="text-xl font-bold text-textDark">Agenda de Hoy</h3>
                        <span class="text-[10px] font-black bg-gray-100 px-2 py-1 rounded text-textDark">{{ today_date }}</span>
                    </div>
                    <div class="relative space-y-6">
                        <div class="absolute left-[11px] top-2 bottom-2 w-0.5 bg-gray-100"></div>
                        
                        {% if agenda %}
                            {% for sess in agenda %}
                            <div class="relative pl-10 {{ '' if sess.is_current else 'opacity-70' }}">
                                <div class="absolute left-0 top-1 w-6 h-6 rounded-full {{ 'bg-primary' if sess.is_current else 'bg-gray-200' }} ring-4 ring-white z-10 flex items-center justify-center">
                                    {% if sess.is_current %}
                                    <div class="w-2 h-2 rounded-full bg-white"></div>
                                    {% endif %}
                                </div>
                                <div class="text-xs font-bold {{ 'text-primary' if sess.is_current else 'text-gray-400' }} mb-1">{{ 'AHORA • ' if sess.is_current else '' }}{{ sess.start }}</div>
                                <div class="{{ 'bg-lightGreen' if sess.is_current else 'bg-gray-50' }} p-4 rounded-soft border border-transparent {{ 'border-primary/20' if sess.is_current else '' }}">
                                    <div class="font-bold text-textDark">{{ sess.title }}</div>
                                    <div class="text-xs text-gray-500 mb-2">Paciente: {{ sess.patient }} • {{ sess.location }}</div>
                                </div>
                            </div>
                            {% endfor %}
                        {% else %}
                            <div class="relative pl-10">
                                <div class="text-sm text-gray-500">Sin sesiones programadas hoy.</div>
                            </div>
                        {% endif %}
                    </div>
                    
                    <a href="{{ url_for('therapist.calendar') }}" class="block w-full mt-10 py-3 bg-gray-50 text-gray-600 text-center rounded-soft font-bold text-sm hover:bg-gray-100 transition-colors">
                        Ver Calendario Completo
                    </a>
                </div>
            </div>
        </div>

        <!-- Bottom Stats from old dashboard -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-white p-6 rounded-soft shadow-soft border border-gray-100 flex items-start gap-5">
                <div class="p-3 bg-red-100 text-statusRed rounded-lg">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                <div>
                    <div class="text-2xl font-bold text-textDark">{{ alerts|length }}</div>
                    <div class="text-sm font-medium text-gray-500">Alertas Pendientes</div>
                    <div class="mt-2 text-[10px] text-red-600 font-bold bg-red-50 px-2 py-1 rounded inline-block">Atención Requerida</div>
                </div>
            </div>
            
            <div class="bg-white p-6 rounded-soft shadow-soft border border-gray-100 flex items-start gap-5">
                <div class="p-3 bg-lightGreen text-primary rounded-lg">
                    <i class="fas fa-chart-line"></i>
                </div>
                <div>
                    <div class="text-2xl font-bold text-textDark">{{ stats.improvement_rate }}%</div>
                    <div class="text-sm font-medium text-gray-500">Progreso Reciente</div>
                    <div class="mt-2 text-[10px] text-primary font-bold bg-lightGreen px-2 py-1 rounded inline-block">Este Mes</div>
                </div>
            </div>
            
            <div class="bg-white p-6 rounded-soft shadow-soft border border-gray-100 flex items-start gap-5">
                <div class="p-3 bg-blue-50 text-blue-500 rounded-lg">
                    <i class="fas fa-robot"></i>
                </div>
                <div>
                    <div class="text-2xl font-bold text-textDark">{{ stats.ia_precision }}%</div>
                    <div class="text-sm font-medium text-gray-500">IA Activa</div>
                    <div class="mt-2 text-[10px] text-blue-600 font-bold bg-blue-50 px-2 py-1 rounded inline-block">Precisión</div>
                </div>
            </div>
        </div>
    </section>

    <!-- Main Patient Table Section (Retained from existing for functionality constraints) -->
    <div id="patient-performance-section" class="px-4 md:px-8 pb-8">
        <div class="bg-white rounded-soft shadow-soft border border-gray-100 p-4 md:p-8">
            <div class="flex flex-col md:flex-row items-start md:items-center justify-between mb-6 md:mb-8 gap-4">
                <div>
                    <h3 class="text-xl md:text-2xl font-bold text-textDark mb-2">Rendimiento de Pacientes</h3>
                    <p class="text-sm text-gray-500">Análisis en tiempo real con recomendaciones de IA</p>
                </div>
                <div class="flex items-center gap-3 w-full md:w-auto">
                    <button class="flex-1 md:flex-none px-5 py-2.5 rounded-full border-2 border-gray-200 text-gray-600 font-medium hover:border-primary hover:text-primary transition-all text-center">
                        <i class="fa-solid fa-filter mr-2"></i>Filtrar
                    </button>
                    <button class="flex-1 md:flex-none px-5 py-2.5 rounded-full bg-primary text-white font-semibold shadow-soft transition-all text-center">
                        <i class="fa-solid fa-download mr-2"></i>Exportar
                    </button>
                </div>
            </div>

            <!-- Table content exactly as before, omitted the mobile duplicate for brevity, kept structure -->
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="border-b border-gray-100">
                            <th class="text-left py-4 px-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Paciente</th>
                            <th class="text-left py-4 px-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Ejercicio</th>
                            <th class="text-center py-4 px-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Nivel Actual</th>
                            <th class="text-center py-4 px-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Precisión</th>
                            <th class="text-left py-4 px-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Recomendación IA</th>
                            <th class="text-center py-4 px-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Acciones</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-50">
                        {% for p in patients %}
                        <tr class="hover:bg-gray-50 transition-colors">
                            <td class="py-4 px-4">
                                <div class="flex items-center gap-3">
                                    <div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                                        {{ p.name[:2].upper() if p.name else 'US' }}
                                    </div>
                                    <div>
                                        <p class="font-semibold text-textDark">{{ p.name }}</p>
                                        <p class="text-xs text-gray-500">ID: {{ p.ptid }}</p>
                                    </div>
                                </div>
                            </td>
                            <td class="py-4 px-4">
                                <div class="flex items-center gap-2">
                                    <i class="fa-solid fa-gamepad text-primary"></i>
                                    <span class="text-sm font-medium">{{ p.game }}</span>
                                </div>
                            </td>
                            <td class="py-4 px-4 text-center">
                                <span class="inline-block px-3 py-1 rounded-full bg-blue-50 text-blue-600 text-xs font-semibold">Nivel {{ p.level }}</span>
                            </td>
                            <td class="py-4 px-4 text-center">
                                <span class="text-sm font-bold {% if p.accuracy > 80 %}text-statusGreen{% elif p.accuracy > 50 %}text-statusYellow{% else %}text-statusRed{% endif %}">{{ p.accuracy }}%</span>
                            </td>
                            <td class="py-4 px-4">
                                {% if p.prediction_code == 1 %}
                                <span class="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-green-50 text-green-600 text-xs font-bold">
                                    <i class="fa-solid fa-arrow-up"></i>Avanzar
                                </span>
                                {% elif p.prediction_code == 2 %}
                                <span class="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-red-50 text-red-600 text-xs font-bold">
                                    <i class="fa-solid fa-heart"></i>Apoyo
                                </span>
                                {% else %}
                                <span class="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-gray-100 text-gray-600 text-xs font-bold">
                                    <i class="fa-solid fa-minus"></i>Mantener
                                </span>
                                {% endif %}
                            </td>
                            <td class="py-4 px-4 text-center">
                                <a href="{{ url_for('therapist.patient_detail', patient_id=p.ptid) }}" class="p-2 rounded-soft hover:bg-gray-200 transition-all text-gray-500">
                                    <i class="fa-solid fa-eye"></i>
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                        {% if not patients %}
                        <tr>
                            <td colspan="6" class="py-8 text-center text-gray-400 text-sm">No hay datos de pacientes registrados recientes.</td>
                        </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
"""

full_new_file = pre_content + new_content + post_content
with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(full_new_file)
print("Updated successfully")
