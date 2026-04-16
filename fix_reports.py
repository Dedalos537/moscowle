import re
import os

filepath = 'app/templates/admin/reports.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Refactor the report buttons block
buttons_block_old = """        <div class="flex gap-2">
            <button onclick="generateIAReport(this)" class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-soft hover:bg-indigo-700 transition-colors flex items-center gap-2" title="Generar análisis estratégico con Llama 3.1">
                <i class="fas fa-brain"></i> Análisis Llama AI
            </button>
            <button onclick="sendWeeklyReport(this)" class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-soft hover:bg-blue-700 transition-colors flex items-center gap-2" title="Enviar ahora el resumen de deudores">
                <i class="fas fa-envelope"></i> Reporte Semanal
            </button>
            <a href="{{ url_for('admin.export_payments_csv') }}" class="px-4 py-2 bg-charcoal text-white text-sm font-medium rounded-soft hover:bg-gray-700 transition-colors flex items-center gap-2">
                <i class="fas fa-file-csv"></i> Exportar CSV
            </a>
        </div>"""

buttons_block_new = """        <div class="flex gap-2">
            <button onclick="generateIAReport(this)" class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-soft hover:bg-indigo-700 transition-colors flex items-center gap-2" title="Generar análisis estratégico con Llama 3.1"><i class="fas fa-brain"></i> Análisis Llama AI</button>
            <button onclick="sendWeeklyReport(this)" class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-soft hover:bg-blue-700 transition-colors flex items-center gap-2" title="Enviar ahora el resumen de deudores"><i class="fas fa-envelope"></i> Reporte Semanal</button>
            <a href="{{ url_for('admin.export_payments_csv') }}" class="px-4 py-2 bg-charcoal text-white text-sm font-medium rounded-soft hover:bg-gray-700 transition-colors flex items-center gap-2"><i class="fas fa-file-csv"></i> Exportar CSV</a>
        </div>"""
# Let's write the actual macro replacements
buttons_block_macro = """        <div class="flex gap-2 flex-wrap sm:flex-nowrap">
            <button onclick="generateIAReport(this)" title="Generar análisis estratégico con Llama 3.1" class="px-6 py-2.5 rounded-xl text-white font-bold hover:shadow-lg hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-sm">
                <i class="fas fa-brain"></i> <span>Análisis Llama AI</span>
            </button>
            <button onclick="sendWeeklyReport(this)" title="Enviar ahora el resumen de deudores" class="px-6 py-2.5 rounded-xl text-white font-bold hover:shadow-lg hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-sm">
                <i class="fas fa-envelope"></i> <span>Reporte Semanal</span>
            </button>
            <a href="{{ url_for('admin.export_payments_csv') }}" class="px-6 py-2.5 rounded-xl text-white font-bold hover:shadow-lg hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 bg-gray-800 hover:bg-gray-900 text-sm">
                <i class="fas fa-file-csv"></i> <span>Exportar CSV</span>
            </a>
        </div>"""

if buttons_block_old in content:
    content = content.replace(buttons_block_old, buttons_block_macro)

# Refactor Table headers for Therapists and Patients
thead_therapists_old = """        <thead class="bg-gray-50"><tr>
          <th class="px-3 py-2 text-left">Nombre</th>
          <th class="px-3 py-2 text-left">Email</th>
          <th class="px-3 py-2 text-left">Sesiones</th>
          <th class="px-3 py-2 text-left">Precisión</th>
        </tr></thead>"""

thead_therapists_new = """        {{ tables.table_header([
          {'label': 'Nombre'},
          {'label': 'Email'},
          {'label': 'Sesiones'},
          {'label': 'Precisión'}
        ]) }}"""

content = content.replace(thead_therapists_old, thead_therapists_new)

thead_patients_old = """        <thead class="bg-gray-50"><tr>
          <th class="px-3 py-2 text-left">Nombre</th>
          <th class="px-3 py-2 text-left">Email</th>
          <th class="px-3 py-2 text-left">Juegos</th>
          <th class="px-3 py-2 text-left">Precisión</th>
        </tr></thead>"""

thead_patients_new = """        {{ tables.table_header([
          {'label': 'Nombre'},
          {'label': 'Email'},
          {'label': 'Juegos'},
          {'label': 'Precisión'}
        ]) }}"""

content = content.replace(thead_patients_old, thead_patients_new)

# Replace table bodies classes
content = content.replace('<td class="px-3 py-2">', '<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated reports")
