import sys

filepath = 'app/templates/admin/users.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_filters = '''             <!-- Sede Filter -->
             <div class="relative w-full md:w-48">
                <select id="sedeFilter" class="w-full pl-4 pr-10 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 appearance-none bg-gray-50 dark:bg-slate-800 focus:bg-white dark:focus:bg-slate-900 text-gray-700 dark:text-gray-300 transition-all shadow-sm">
                    <option value="all">Todas las Sedes</option>
                    {% for s in sedes %}
                    <option value="{{ s.id }}">{{ s.name }}</option>
                    {% endfor %}
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-gray-400">
                    <i class="fas fa-chevron-down text-xs"></i>
                </div>
             </div>

             <!-- Therapist Filter -->
             <div class="relative w-full md:w-48">
                <select id="therapistFilter" class="w-full pl-4 pr-10 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 appearance-none bg-gray-50 dark:bg-slate-800 focus:bg-white dark:focus:bg-slate-900 text-gray-700 dark:text-gray-300 transition-all shadow-sm">
                    <option value="all">Filtro Terapeuta</option>
                    <!-- Populated by JS -->
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-gray-400">
                    <i class="fas fa-chevron-down text-xs"></i>
                </div>
             </div>

             <!-- Search Bar -->
             <div class="relative w-full md:w-64">
                <input type="text" id="userHelperSearch" placeholder="Buscar usuario o email..." class="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all bg-gray-50 dark:bg-slate-800 focus:bg-white dark:focus:bg-slate-900 text-gray-700 dark:text-gray-300 shadow-sm">
                <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <i class="fas fa-search text-gray-400 text-sm"></i>
                </div>
            </div>'''

new_filters = '''             <!-- Sede Filter -->
             {{ forms.filter_select('sedeFilter', 'Todas las Sedes', sede_opts) }}

             <!-- Therapist Filter -->
             {{ forms.filter_select('therapistFilter', 'Filtro Terapeuta', []) }}

             <!-- Search Bar -->
             {{ forms.search_input('userHelperSearch', 'Buscar usuario o email...') }}'''

content = content.replace(old_filters, new_filters)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Top filters replaced")
