import sys

filepath = 'app/templates/admin/users.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_edit_basic = '''            <div class="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Nombre</label>
                    <input type="text" id="edit-username" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700">
                </div>
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Email</label>
                    <input type="text" id="edit-email" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700" readonly disabled>
                </div>
            </div>
            
            <div class="mb-4">
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Rol</label>
                <select id="edit-role" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary">
                    <option value="terapista">Terapeuta</option>
                    <option value="jugador">Paciente</option>
                    <option value="admin">Administrador</option>
                </select>
            </div>'''
            
new_edit_basic = '''            <div class="grid grid-cols-2 gap-4 mb-4">
                {{ inputs.text_input('edit-username', 'Nombre') }}
                {{ inputs.text_input('edit-email', 'Email', readonly=true) }}
            </div>
            
            <div class="mb-4">
                {{ inputs.select_input('edit-role', 'Rol', [
                    {'value': 'terapista', 'label': 'Terapeuta'},
                    {'value': 'jugador', 'label': 'Paciente'},
                    {'value': 'admin', 'label': 'Administrador'}
                ], default_option='') }}
            </div>'''

old_edit_sede = '''            <div id="edit-patient-location" class="hidden mb-4 p-3 bg-white rounded border border-gray-100">
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Sede (Sucursal)</label>
                <select id="edit-sede" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary">
                    <option value="">-- Sin asignar --</option>
                    {% for s in sedes %}
                    <option value="{{ s.id }}">{{ s.name }}</option>
                    {% endfor %}
                </select>
                <p class="text-[10px] text-gray-400 mt-1">Ubicación principal de atención.</p>
            </div>'''

new_edit_sede = '''            <div id="edit-patient-location" class="hidden mb-4 p-3 bg-white rounded border border-gray-100">
                {{ inputs.select_input('edit-sede', 'Sede (Sucursal)', sede_opts, default_option='-- Sin asignar --') }}
                <p class="text-[10px] text-gray-400 mt-1">Ubicación principal de atención.</p>
            </div>'''

content = content.replace(old_edit_basic, new_edit_basic)
content = content.replace(old_edit_sede, new_edit_sede)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Edit user basic inputs updated!")
