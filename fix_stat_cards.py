import sys

filepath = 'app/templates/admin/users.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''    <!-- Stat Cards -->
                <div class="mb-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
                    <div class="stat-card bg-white dark:bg-slate-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm hover:shadow-md transition-all duration-300 p-6 flex flex-col justify-center relative overflow-hidden group">
                        <div class="absolute right-0 top-0 w-24 h-24 bg-primary/5 rounded-bl-full z-0 group-hover:scale-110 transition-transform"></div>
                        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-1 z-10">Total Usuarios</div>
                        <div id="total_users" class="text-3xl font-extrabold text-charcoal dark:text-white z-10">0</div>
                    </div>
                    <div class="stat-card bg-white dark:bg-slate-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm hover:shadow-md transition-all duration-300 p-6 flex flex-col justify-center relative overflow-hidden group">
                        <div class="absolute right-0 top-0 w-24 h-24 bg-green-500/5 rounded-bl-full z-0 group-hover:scale-110 transition-transform"></div>
                        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-1 z-10">Activos</div>
                        <div id="active_users" class="text-3xl font-extrabold text-green-500 z-10">0</div>
                    </div>
                    <div class="stat-card bg-white dark:bg-slate-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm hover:shadow-md transition-all duration-300 p-6 flex flex-col justify-center relative overflow-hidden group">
                        <div class="absolute right-0 top-0 w-24 h-24 bg-indigo-500/5 rounded-bl-full z-0 group-hover:scale-110 transition-transform"></div>
                        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-1 z-10">Pacientes</div>
                        <div id="total_patients" class="text-3xl font-extrabold text-charcoal dark:text-white z-10">0</div>
                    </div>
                    <div class="stat-card bg-white dark:bg-slate-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm hover:shadow-md transition-all duration-300 p-6 flex flex-col justify-center relative overflow-hidden group">
                        <div class="absolute right-0 top-0 w-24 h-24 bg-purple-500/5 rounded-bl-full z-0 group-hover:scale-110 transition-transform"></div>
                        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-1 z-10">Terapeutas</div>
                        <div id="total_therapists" class="text-3xl font-extrabold text-charcoal dark:text-white z-10">0</div>
                    </div>
                </div>'''

new_block = '''    <!-- Stat Cards (Molecules) -->
                <div class="mb-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
                    {{ cards.stat_card('total_users', 'Total Usuarios', '0', 'bg-primary/5') }}
                    {{ cards.stat_card('active_users', 'Activos', '0', 'bg-green-500/5', 'text-green-500') }}
                    {{ cards.stat_card('total_patients', 'Pacientes', '0', 'bg-indigo-500/5') }}
                    {{ cards.stat_card('total_therapists', 'Terapeutas', '0', 'bg-purple-500/5') }}
                </div>'''

content = content.replace(old_block, new_block)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Stat Cards updated!")
