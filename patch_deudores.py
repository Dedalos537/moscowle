import re

with open('app/templates/admin/deudores.html', 'r') as f:
    content = f.read()

new_fields = """
            <div id="missing_data_warning" class="hidden mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-800">
                <i class="fas fa-exclamation-triangle"></i> Faltan datos para el Recibo Digital. Por favor complete estos campos.
            </div>
            <div class="mb-4 hidden" id="fg_document_number">
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">DNI del Alumno/Apoderado para Recibo</label>
                <input type="text" name="document_number" id="input_document_number" class="w-full px-3 py-2 border rounded-soft">
            </div>
            <div class="mb-4 hidden" id="fg_guardian_name">
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Nombre del Apoderado para Recibo</label>
                <input type="text" name="guardian_name" id="input_guardian_name" class="w-full px-3 py-2 border rounded-soft">
            </div>
            
            <div class="mb-4">
"""

content = content.replace('<div class="mb-4">\n                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Monto (S/)</label>', new_fields + '                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Monto (S/)</label>')

with open('app/templates/admin/deudores.html', 'w') as f:
    f.write(content)

