import sys

filepath = 'app/templates/admin/users.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_basic_info = '''            <!-- Basic Info -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
              <div>
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Email</label>
                <input id="new-email" class="px-3 py-2 border rounded-soft w-full focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700" placeholder="email@ejemplo.com" />
              </div>
              <div>
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Nombre</label>
                <input id="new-username" class="px-3 py-2 border rounded-soft w-full focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700" placeholder="Nombre completo" />
              </div>
              <div>
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Rol</label>
                <select id="new-role" class="px-3 py-2 border rounded-soft w-full focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700">
                  <option value="terapista">Terapeuta</option>
                  <option value="jugador">Paciente</option>
                  <option value="admin">Administrador</option>
                </select>
              </div>
            </div>'''
            
new_basic_info = '''            <!-- Basic Info -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
              {{ inputs.text_input('new-email', 'Email', 'email@ejemplo.com') }}
              {{ inputs.text_input('new-username', 'Nombre', 'Nombre completo') }}
              {{ inputs.select_input('new-role', 'Rol', [
                  {'value': 'terapista', 'label': 'Terapeuta'},
                  {'value': 'jugador', 'label': 'Paciente'},
                  {'value': 'admin', 'label': 'Administrador'}
              ], default_option='') }}
            </div>'''

content = content.replace(old_basic_info, new_basic_info)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Success: Basic Info Replaced')
