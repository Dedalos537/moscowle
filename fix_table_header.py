import sys

filepath = 'app/templates/admin/users.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_thead = '''        <thead class="bg-gray-50 dark:bg-slate-800">
          <tr>
            <th class="px-6 py-4 text-left text-xs font-extrabold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Usuario</th>
            <th class="px-6 py-4 text-left text-xs font-extrabold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Email</th>
            <th class="px-6 py-4 text-left text-xs font-extrabold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Rol</th>
            <th class="px-6 py-4 text-left text-xs font-extrabold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Sede</th>
            <th class="px-6 py-4 text-center text-xs font-extrabold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Estado</th>
            <th class="px-6 py-4 text-left text-xs font-extrabold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Terapeuta</th>
            <th class="px-6 py-4 text-right text-xs font-extrabold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Acciones</th>
          </tr>
        </thead>'''

new_thead = '''        {{ tables.table_header([
            {'label': 'Usuario', 'align': 'text-left'},
            {'label': 'Email', 'align': 'text-left'},
            {'label': 'Rol', 'align': 'text-left'},
            {'label': 'Sede', 'align': 'text-left'},
            {'label': 'Estado', 'align': 'text-center'},
            {'label': 'Terapeuta', 'align': 'text-left'},
            {'label': 'Acciones', 'align': 'text-right'}
        ]) }}'''

content = content.replace(old_thead, new_thead)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Table Header updated")
