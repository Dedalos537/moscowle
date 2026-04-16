import re

filepath = 'app/templates/therapist/reports.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_form = """        <form id="filters-form" method="get" class="bg-white rounded-soft p-4 shadow-soft mb-6">
            <div class="flex flex-col md:flex-row md:items-end md:space-x-4 space-y-3 md:space-y-0">
                <div>
                    <label for="start" class="block text-sm text-gray-600 mb-1">Desde</label>
                    <input type="date" id="start" name="start" value="{{ start if start else '' }}" class="px-3 py-2 border border-gray-200 rounded-xl focus:outline-none focus:border-olive">
                </div>
                <div>
                    <label for="end" class="block text-sm text-gray-600 mb-1">Hasta</label>
                    <input type="date" id="end" name="end" value="{{ end if end else '' }}" class="px-3 py-2 border border-gray-200 rounded-xl focus:outline-none focus:border-olive">
                </div>
                <div class="flex space-x-2">
                    <button type="submit" class="px-4 py-2 bg-olive text-white rounded-xl hover:bg-opacity-90 transition-all">
                        <i class="fas fa-filter mr-2"></i>Aplicar filtros
                    </button>
                    <a href="{{ url_for('therapist.reports') }}" class="px-4 py-2 bg-gray-100 text-charcoal rounded-xl hover:bg-gray-200 transition-all">
                        Limpiar
                    </a>
                </div>
            </div>
        </form>"""

new_form = """        <form id="filters-form" method="get" class="bg-white dark:bg-slate-900 border border-gray-100 dark:border-gray-800 rounded-2xl p-6 shadow-sm mb-6">
            <div class="flex flex-col md:flex-row md:items-end gap-4 space-y-3 md:space-y-0">
                <div class="w-full md:w-auto">
                    {{ inputs.text_input('start', 'Desde', type='date', value=start if start else '', input_classes='border-gray-200 dark:border-gray-700 bg-gray-50 focus:border-olive') }}
                </div>
                <div class="w-full md:w-auto">
                    {{ inputs.text_input('end', 'Hasta', type='date', value=end if end else '', input_classes='border-gray-200 dark:border-gray-700 bg-gray-50 focus:border-olive') }}
                </div>
                <div class="flex gap-2 pb-0.5">
                    {{ btn.primary_btn('submit-filters', 'Aplicar', icon='fas fa-filter text-xs', extra_classes='bg-olive hover:bg-olive/90 py-2') }}
                    <a href="{{ url_for('therapist.reports') }}" class="px-5 py-2.5 rounded-xl border border-gray-200 font-semibold text-gray-600 hover:bg-gray-100 transition-colors flex items-center gap-2">Limpiar</a>
                </div>
            </div>
        </form>"""

content = content.replace(old_form, new_form)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated therapist reports")
