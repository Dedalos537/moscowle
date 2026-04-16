import sys

filepath = 'app/templates/admin/users.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''                 <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Base Salarial / Monto Total (S/)</label>
                        <input type="number" step="0.01" id="new-salary" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700" placeholder="0.00">
                    </div>
                     <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Horas Contratadas (Mensual)</label>
                        <input type="number" id="new-hours" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700" placeholder="e.g. 160">
                    </div>
                 </div>'''

new_block = '''                 <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    {{ inputs.text_input('new-salary', 'Base Salarial / Monto Total (S/)', '0.00', type='number', extra_attrs='step="0.01"') }}
                    {{ inputs.text_input('new-hours', 'Horas Contratadas (Mensual)', 'e.g. 160', type='number') }}
                 </div>'''

content = content.replace(old_block, new_block)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Therapist fields updated!")
