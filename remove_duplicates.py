import sys

filepath = 'app/templates/admin/users.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# This is the exact chunk we are removing
bad_chunk = """            <!-- Therapist Specific Fields (Hidden by default) -->
            <div id="therapist-fields" class="hidden space-y-4 mb-4">
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Sueldo Base (S/)</label>
                        <input type="number" step="0.01" id="new-salary" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700" placeholder="0.00">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Horas Mensuales</label>
                        <input type="number" id="new-hours" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700" placeholder="0">
                    </div>
                </div>
            </div>

            <!-- Patient Specific Fields (Default) -->
            <div id="patient-fields" class="space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Modalidad (Sesiones)</label>
                        <select id="new-modality" class="w-full px-3 py-2 border rounded-soft focus:ring-primary focus:border-primary bg-gray-50 dark:bg-gray-800 dark:border-gray-700">
                            <option value="0">Sesión Libre / Sin Paquete</option>
                            <option value="1">1x Semana (4 sesiones)</option>
                            <option value="2">2x Semana (8 sesiones)</option>
                            <option value="3">3x Semana (12 sesiones)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Frecuencia Pago</label>
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
                </div>

                <div class="mb-4">
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" id="check-generate" class="rounded text-primary focus:ring-primary" checked>
                        <span class="text-sm font-bold text-gray-700 dark:text-gray-300">Generar Horario Automático</span>
                    </label>
                </div>

                <div id="schedule-fields" class="bg-gray-50 dark:bg-gray-800 p-4 rounded-soft border border-gray-100 dark:border-gray-700">
                    <h4 class="text-sm font-bold text-gray-600 dark:text-gray-300 mb-3"><i class="far fa-calendar-alt mr-2"></i>Programación de Sesiones</h4>
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-3">
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
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1 mb-2">Días de Sesión (Seleccionar según modalidad)</label>
                        <div class="flex gap-4 flex-wrap">
                            <label class="inline-flex items-center gap-1 text-sm bg-white dark:bg-gray-700 dark:border-gray-600 px-3 py-1 rounded border hover:border-primary cursor-pointer"><input type="checkbox" name="days" value="0" class="text-primary rounded"> Lun</label>
                            <label class="inline-flex items-center gap-1 text-sm bg-white dark:bg-gray-700 dark:border-gray-600 px-3 py-1 rounded border hover:border-primary cursor-pointer"><input type="checkbox" name="days" value="1" class="text-primary rounded"> Mar</label>
                            <label class="inline-flex items-center gap-1 text-sm bg-white dark:bg-gray-700 dark:border-gray-600 px-3 py-1 rounded border hover:border-primary cursor-pointer"><input type="checkbox" name="days" value="2" class="text-primary rounded"> Mié</label>
                            <label class="inline-flex items-center gap-1 text-sm bg-white dark:bg-gray-700 dark:border-gray-600 px-3 py-1 rounded border hover:border-primary cursor-pointer"><input type="checkbox" name="days" value="3" class="text-primary rounded"> Jue</label>
                            <label class="inline-flex items-center gap-1 text-sm bg-white dark:bg-gray-700 dark:border-gray-600 px-3 py-1 rounded border hover:border-primary cursor-pointer"><input type="checkbox" name="days" value="4" class="text-primary rounded"> Vie</label>
                            <label class="inline-flex items-center gap-1 text-sm bg-white dark:bg-gray-700 dark:border-gray-600 px-3 py-1 rounded border hover:border-primary cursor-pointer"><input type="checkbox" name="days" value="5" class="text-primary rounded"> Sáb</label>
                        </div>
                    </div>
                </div>
            </div>"""

content = content.replace(bad_chunk, "")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Success: Duplicates removed')
