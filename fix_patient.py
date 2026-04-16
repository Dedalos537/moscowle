import sys

filepath = 'app/templates/admin/users.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_patient = '''                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Modalidad (Sesiones)</label>
                        <select id="new-modality" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700">
                            <option value="1">1x Semana (4 Sesiones/Pago)</option>
                            <option value="2">2x Semana (8 Sesiones/Pago)</option>
                            <option value="3">3x Semana (12 Sesiones/Pago)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Frecuencia de Pago</label>
                        <select id="new-frequency" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700">
                            <option value="monthly">Mensual</option>
                            <option value="biweekly">Quincenal</option>
                            <option value="weekly">Semanal</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Tipo de Plan</label>
                        <select id="new-plan-type" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700">
                            <option value="individual">Individual</option>
                            <option value="group">Grupal / Fijo</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Monto a Pagar (S/)</label>
                        <input type="number" step="0.01" id="new-amount" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700" placeholder="0.00">
                    </div>
                </div>'''

new_patient = '''                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    {{ inputs.select_input('new-modality', 'Modalidad (Sesiones)', [
                        {'value': '1', 'label': '1x Semana (4 Sesiones/Pago)'},
                        {'value': '2', 'label': '2x Semana (8 Sesiones/Pago)'},
                        {'value': '3', 'label': '3x Semana (12 Sesiones/Pago)'}
                    ], default_option='') }}
                    
                    {{ inputs.select_input('new-frequency', 'Frecuencia de Pago', [
                        {'value': 'monthly', 'label': 'Mensual'},
                        {'value': 'biweekly', 'label': 'Quincenal'},
                        {'value': 'weekly', 'label': 'Semanal'}
                    ], default_option='') }}
                    
                    {{ inputs.select_input('new-plan-type', 'Tipo de Plan', [
                        {'value': 'individual', 'label': 'Individual'},
                        {'value': 'group', 'label': 'Grupal / Fijo'}
                    ], default_option='') }}
                    
                    {{ inputs.text_input('new-amount', 'Monto a Pagar (S/)', '0.00', type='number', extra_attrs='step="0.01"') }}
                </div>'''

old_schedule = '''                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-3">
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Fecha Inicio</label>
                            <input type="date" id="start-date" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-white dark:bg-gray-700 dark:border-gray-600"> 
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Hora Inicio</label>
                            <input type="time" id="start-time" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-white dark:bg-gray-700 dark:border-gray-600">
                        </div>
                        <div class="md:col-span-2">
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Terapeuta Asignado</label>
                            <select id="schedule-therapist" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-white dark:bg-gray-700 dark:border-gray-600">
                                <option value="">-- Seleccionar --</option>
                                {% for t in therapists %}
                                <option value="{{ t.id }}">{{ t.username }} ({{ t.email }})</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>'''

new_schedule = '''                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-3">
                        {{ inputs.text_input('start-date', 'Fecha Inicio', type='date') }}
                        {{ inputs.text_input('start-time', 'Hora Inicio', type='time') }}
                        
                        {% set therapist_opts = [] %}
                        {% for t in therapists %}
                            {% set _ = therapist_opts.append({'value': t.id, 'label': t.username ~ ' (' ~ t.email ~ ')'}) %}
                        {% endfor %}
                        {{ inputs.select_input('schedule-therapist', 'Terapeuta Asignado', therapist_opts, default_option='-- Seleccionar --', wrapper_classes='md:col-span-2') }}
                    </div>'''

content = content.replace(old_patient, new_patient)
content = content.replace(old_schedule, new_schedule)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patient config and schedule inputs updated!")
