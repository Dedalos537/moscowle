import sys

filepath = 'app/templates/admin/users.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_sedes = '''            <!-- Sede Selection -->
            <div class="mb-4">
                 <div id="patient-sede-div">
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Sede (Sucursal)</label>
                    <select id="new-sede" class="px-3 py-2 border rounded-soft w-full focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700">
                        <option value="">-- Sin asignar --</option>
                        {% for s in sedes %}
                        <option value="{{ s.id }}">{{ s.name }}</option>
                        {% endfor %}
                    </select>
                 </div>
                 <div id="therapist-sede-div" class="hidden">
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Sedes Asignadas (Ctrl+Click para múltiples)</label>
                    <select id="new-sedes-multi" multiple class="px-3 py-2 border rounded-soft w-full focus:ring-primary focus:border-primary h-24 bg-gray-50 dark:bg-gray-800 dark:border-gray-700">
                        {% for s in sedes %}
                        <option value="{{ s.id }}">{{ s.name }}</option>
                        {% endfor %}
                    </select>
                 </div>
            </div>'''
            
new_sedes = '''            <!-- Sede Selection -->
            <div class="mb-4">
                 {% set sede_opts = [] %}
                 {% for s in sedes %}
                     {% set _ = sede_opts.append({'value': s.id, 'label': s.name}) %}
                 {% endfor %}
                 
                 <div id="patient-sede-div">
                    {{ inputs.select_input('new-sede', 'Sede (Sucursal)', sede_opts, default_option='-- Sin asignar --') }}
                 </div>
                 <div id="therapist-sede-div" class="hidden">
                    {{ inputs.select_input('new-sedes-multi', 'Sedes Asignadas (Ctrl+Click para múltiples)', sede_opts, default_option='', multiple=true, select_classes='h-24 custom-scrollbar') }}
                 </div>
            </div>'''

content = content.replace(old_sedes, new_sedes)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Success: Sede Options Replaced')
