import re

with open('app/templates/therapist/patients.html', 'r', encoding='utf-8') as f:
    content = f.read()

# We will just write a whole new content
new_content = """{% extends "therapist/base.html" %}

{% block header_content %}{% endblock %}
{% block header_action %}{% endblock %}

{% block extra_scripts %}
<script>
tail_config = {
    darkMode: "class",
    theme: {
        extend: {
            "colors": {
                "outline-variant": "#c7c9b7",
                "background": "#f8fbed",
                "surface-dim": "#d9dbce",
                "error-container": "#ffdad6",
                "error": "#ba1a1a",
                "on-tertiary-fixed-variant": "#005236",
                "on-primary-fixed-variant": "#1d2e00",
                "surface-container-high": "#e7e9db",
                "tertiary": "#00311f",
                "tertiary-fixed": "#6ffbbe",
                "surface": "#f8fbed",
                "primary-fixed": "#d3eeab",
                "surface-tint": "#75a83a",
                "on-secondary-fixed-variant": "#3f4c2a",
                "on-secondary-fixed": "#161e07",
                "surface-bright": "#f8fbed",
                "tertiary-fixed-dim": "#4edea3",
                "surface-container-low": "#f3f5e7",
                "on-background": "#1a1c16",
                "surface-container-lowest": "#ffffff",
                "on-secondary": "#ffffff",
                "secondary-container": "#75a83a",
                "on-primary-fixed": "#0a1300",
                "on-error": "#ffffff",
                "primary": "#75a83a",
                "on-error-container": "#93000a",
                "outline": "#75796a",
                "secondary-fixed": "#d3eeab",
                "primary-container": "#75a83a",
                "on-tertiary": "#ffffff",
                "on-secondary-container": "#ffffff",
                "on-primary": "#ffffff",
                "on-surface": "#1a1c16",
                "primary-fixed-dim": "#b7d191",
                "inverse-surface": "#2f312a",
                "tertiary-container": "#004a31",
                "secondary": "#57633f",
                "inverse-primary": "#b7d191",
                "surface-variant": "#e1e4d3",
                "surface-container": "#ecefdf",
                "on-tertiary-fixed": "#002113",
                "on-surface-variant": "#44483d",
                "on-primary-container": "#ffffff",
                "surface-container-highest": "#e1e4d3",
                "inverse-on-surface": "#f1f1e8",
                "secondary-fixed-dim": "#b7d191",
                "on-tertiary-container": "#27c38a"
            },
            "borderRadius": {
                "DEFAULT": "0.5rem",
                "lg": "0.75rem",
                "xl": "1rem",
                "full": "9999px"
            },
            "fontFamily": {
                "headline": ["Manrope", "sans-serif"],
                "body": ["Inter", "sans-serif"],
                "label": ["Inter", "sans-serif"]
            }
        }
    }
};

// Si tailwind.config ya existia, lo expandimos
if (window.tailwind) {
    if(!window.tailwind.config) window.tailwind.config = {};
    if(!window.tailwind.config.theme) window.tailwind.config.theme = {extend: {}};
    if(!window.tailwind.config.theme.extend) window.tailwind.config.theme.extend = {};
    window.tailwind.config.theme.extend = {...window.tailwind.config.theme.extend, ...tail_config.theme.extend};
} else {
    window.tailwind = { config: tail_config };
}
</script>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<style>
    .material-symbols-outlined {
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    }
</style>
{% endblock %}

{% block content %}
<!-- Flash Messages -->
{% with messages = get_flashed_messages(with_categories=true) %} 
{% if messages %}
<div class="px-8 py-4">
  {% for category, message in messages %}
  <div class="p-4 rounded-2xl mb-3 {% if category == 'error' %}bg-red-50 text-red-700 border border-red-200{% elif category == 'success' %}bg-green-50 text-green-700 border border-green-200{% else %}bg-yellow-50 text-yellow-700 border border-yellow-200{% endif %}">
    {{ message | safe }}
  </div>
  {% endfor %}
</div>
{% endif %} 
{% endwith %}

<!-- Content starts from the new design section -->
<section class="p-8 max-w-7xl mx-auto font-body bg-background text-on-surface">
    <!-- Page Header & Main Action -->
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div>
            <h1 class="text-[#75a83a] font-headline text-5xl font-bold tracking-tight mb-2">Gestión de Pacientes</h1>
            <p class="text-on-surface-variant text-lg">Supervisión integral y estado del tratamiento.</p>
        </div>
        <button id="add-patient-btn" class="flex items-center gap-3 bg-[#75a83a] text-white px-8 py-4 rounded-lg font-bold shadow-lg shadow-[#75a83a]/20 hover:scale-[1.02] active:scale-95 transition-all">
            <span class="material-symbols-outlined" data-icon="person_add">person_add</span>
            Registrar Nuevo Paciente
        </button>
    </div>

    <!-- Bento Filter Bar -->
    <div class="bg-surface-container-low p-6 rounded-lg mb-8 flex flex-col lg:flex-row gap-4 items-center shadow-sm">
        <div class="relative w-full lg:w-1/3">
            <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline" data-icon="search">search</span>
            <input id="searchInput" class="w-full bg-surface-container-lowest border-none rounded-full py-4 pl-12 pr-6 text-sm focus:ring-2 focus:ring-[#75a83a]/50 placeholder:text-outline transition-shadow" placeholder="Buscar por nombre o correo..." type="text"/>
        </div>
    </div>

    <!-- Student Data Table Container -->
    <div class="bg-surface-container-lowest rounded-lg overflow-hidden shadow-xl shadow-slate-200/50 hidden md:block">
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead class="bg-surface-container-low">
                    <tr>
                        <th class="px-8 py-5 text-[0.6875rem] font-bold uppercase tracking-widest text-on-surface-variant">ID</th>
                        <th class="px-8 py-5 text-[0.6875rem] font-bold uppercase tracking-widest text-on-surface-variant">Nombre del Paciente</th>
                        <th class="px-8 py-5 text-[0.6875rem] font-bold uppercase tracking-widest text-on-surface-variant">Correo Electrónico</th>
                        <th class="px-8 py-5 text-[0.6875rem] font-bold uppercase tracking-widest text-on-surface-variant">Estado</th>
                        <th class="px-8 py-5 text-[0.6875rem] font-bold uppercase tracking-widest text-on-surface-variant text-right">Acciones</th>
                    </tr>
                </thead>
                <tbody class="divide-y-0" id="patientsTableBody">
                    {% for item in patients %}
                    {% set p = item.user %}
                    <tr class="bg-surface hover:bg-surface-container-low transition-colors group cursor-pointer" onclick="window.location='{{ url_for('therapist.patient_detail',patient_id=p.id) }}';">
                        <td class="px-8 py-6 font-medium text-slate-500">#PAC-{{ p.id }}</td>
                        <td class="px-8 py-6">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-full bg-primary-fixed text-[#75a83a] flex items-center justify-center font-bold text-sm">
                                    {{ p.username[:2]|upper if p.username else '??' }}
                                </div>
                                <div>
                                    <p class="font-semibold text-on-surface patient-name">{{ p.username }}</p>
                                    <p class="text-xs text-on-surface-variant">Cuenta vinculada</p>
                                </div>
                            </div>
                        </td>
                        <td class="px-8 py-6">
                            <p class="text-sm patient-email">{{ p.email if p.email else 'Sin correo' }}</p>
                        </td>
                        <td class="px-8 py-6">
                            <span class="inline-flex items-center px-4 py-1.5 rounded-full text-xs font-bold {% if item.status_label == 'Activo' %}bg-[#75a83a]/10 text-[#75a83a]{% elif item.status_label == 'Deudor' %}bg-error-container text-on-error-container{% else %}bg-gray-100 text-gray-700{% endif %}">
                                <span class="w-1.5 h-1.5 rounded-full {% if item.status_label == 'Activo' %}bg-[#75a83a]{% elif item.status_label == 'Deudor' %}bg-error{% else %}bg-gray-500{% endif %} mr-2"></span>
                                {{ item.status_label }}
                            </span>
                        </td>
                        <td class="px-8 py-6 text-right">
                            <div class="flex items-center justify-end gap-2">
                                <button onclick="event.stopPropagation(); toggleStatus({{ p.id }})" class="p-2 text-on-surface-variant hover:text-[#75a83a] transition-colors bg-surface-container-lowest rounded-full shadow-sm" title="Cambiar Estado">
                                    <span class="material-symbols-outlined text-[18px]">power_settings_new</span>
                                </button>
                                <button onclick="event.stopPropagation(); deletePatient({{ p.id }})" class="p-2 text-on-surface-variant hover:text-error transition-colors bg-surface-container-lowest rounded-full shadow-sm" title="Eliminar">
                                    <span class="material-symbols-outlined text-[18px]">delete</span>
                                </button>
                                <a href="{{ url_for('therapist.patient_detail', patient_id=p.id) }}" class="p-2 text-on-surface-variant hover:text-[#75a83a] transition-colors bg-surface-container-lowest rounded-full shadow-sm flex items-center justify-center gap-1" onclick="event.stopPropagation()">
                                    <span class="material-symbols-outlined text-sm" data-icon="arrow_forward">arrow_forward</span>
                                </a>
                            </div>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="5" class="px-8 py-8 text-center text-on-surface-variant font-medium">No hay pacientes registrados.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <!-- Table Footer / Pagination -->
        <div class="px-8 py-6 flex items-center justify-between bg-surface-container-low border-t border-outline-variant/20">
            <p class="text-sm text-on-surface-variant">Mostrando <span class="font-bold text-on-surface">{{ patients|length }}</span> pacientes</p>
        </div>
    </div>

    <!-- Mobile View -->
    <div class="md:hidden space-y-4">
        {% for item in patients %}
        {% set p = item.user %}
        <div class="bg-surface border border-gray-100 rounded-lg p-5 shadow-sm cursor-pointer hover:bg-surface-container-low transition-colors" onclick="window.location='{{ url_for('therapist.patient_detail',patient_id=p.id) }}';">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-12 h-12 rounded-full bg-primary-fixed text-[#75a83a] flex items-center justify-center font-bold text-lg">
                    {{ p.username[:2]|upper if p.username else '??' }}
                </div>
                <div>
                    <h4 class="font-bold text-on-surface">{{ p.username }}</h4>
                    <p class="text-sm text-on-surface-variant">{{ p.email if p.email else 'Sin correo' }}</p>
                </div>
            </div>
            <div class="flex justify-between items-center">
                <span class="inline-flex items-center px-4 py-1.5 rounded-full text-xs font-bold {% if item.status_label == 'Activo' %}bg-[#75a83a]/10 text-[#75a83a]{% elif item.status_label == 'Deudor' %}bg-error-container text-on-error-container{% else %}bg-gray-100 text-gray-700{% endif %}">
                    <span class="w-1.5 h-1.5 rounded-full {% if item.status_label == 'Activo' %}bg-[#75a83a]{% elif item.status_label == 'Deudor' %}bg-error{% else %}bg-gray-500{% endif %} mr-2"></span>
                    {{ item.status_label }}
                </span>
                <div class="flex items-center gap-2">
                    <button onclick="event.stopPropagation(); toggleStatus({{ p.id }})" class="p-2 text-on-surface-variant hover:text-[#75a83a] transition-colors rounded-full bg-surface-container-lowest shadow-sm" title="Cambiar Estado">
                        <span class="material-symbols-outlined text-[18px]">power_settings_new</span>
                    </button>
                    <button onclick="event.stopPropagation(); deletePatient({{ p.id }})" class="p-2 text-on-surface-variant hover:text-error transition-colors rounded-full bg-surface-container-lowest shadow-sm" title="Eliminar">
                        <span class="material-symbols-outlined text-[18px]">delete</span>
                    </button>
                </div>
            </div>
        </div>
        {% else %}
        <div class="text-center p-8 text-on-surface-variant font-medium bg-surface rounded-lg">No hay pacientes registrados.</div>
        {% endfor %}
    </div>

    <!-- Dashboard Insight Overlay -->
    <div class="mt-12 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-[#75a83a] p-8 rounded-lg text-white relative overflow-hidden group">
            <div class="relative z-10">
                <p class="label-sm uppercase tracking-widest font-bold opacity-80 mb-2">Total Pacientes</p>
                <h3 class="text-4xl font-bold mb-4">{{ patients|length }}</h3>
                <div class="flex items-center gap-2 text-surface-container-low">
                    <span class="material-symbols-outlined text-sm" data-icon="trending_up">trending_up</span>
                    <span class="text-xs font-bold">Activos en el sistema</span>
                </div>
            </div>
            <span class="material-symbols-outlined absolute -right-4 -bottom-4 text-9xl opacity-10 group-hover:scale-110 transition-transform duration-500" data-icon="groups">groups</span>
        </div>
        <div class="bg-surface-container-lowest p-8 rounded-lg shadow-sm border border-outline-variant/20">
            <p class="label-sm uppercase tracking-widest font-bold text-on-surface-variant mb-2">Estados de Atención</p>
            <h3 class="text-4xl font-bold text-error mb-4">
                {% set count_inactive = 0 %}
                {% for item in patients %}
                    {% if item.status_label != 'Activo' %}
                        {% set count_inactive = count_inactive + 1 %}
                    {% endif %}
                {% endfor %}
                {{ count_inactive }}
            </h3>
            <div class="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                {% set perc = (count_inactive / [patients|length, 1]|max) * 100 %}
                <div class="bg-error h-full" style="width: {{ perc|int }}%"></div>
            </div>
            <p class="text-[0.6875rem] mt-3 font-medium text-on-surface-variant">Con status de deuda o retirado</p>
        </div>
    </div>
</section>

<!-- Add Patient Modal -->
<div id="add-patient-modal" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 hidden flex items-center justify-center font-body">
    <div class="bg-surface-container-lowest rounded-xl shadow-2xl w-full max-w-lg mx-4 p-6 md:p-8">
        <div class="flex justify-between items-center mb-6">
            <h3 class="text-2xl font-bold text-on-surface font-headline">Nuevo Paciente</h3>
            <button id="close-modal-btn" class="text-on-surface-variant hover:text-error bg-surface-container-low p-2 rounded-full transition-colors">
                <span class="material-symbols-outlined text-[20px]">close</span>
            </button>
        </div>
        <form method="POST" action="{{ url_for('therapist.add_patient') }}" class="flex flex-col gap-5">
            <div>
                <label class="block text-sm font-bold text-on-surface-variant mb-2">Nombre Completo</label>
                <input type="text" name="username" class="w-full px-5 py-4 bg-surface border-none rounded-lg focus:ring-2 focus:ring-[#75a83a]/50 text-sm font-medium" placeholder="Ejem: Alejandro Mendoza" required />
            </div>
            <div>
                <label class="block text-sm font-bold text-on-surface-variant mb-2">Correo Electrónico <span class="font-normal opacity-70">(Opcional)</span></label>
                <input type="email" name="email" class="w-full px-5 py-4 bg-surface border-none rounded-lg focus:ring-2 focus:ring-[#75a83a]/50 text-sm font-medium" placeholder="Dejar vacío si no requiere acceso online" />
            </div>
            <button type="submit" class="w-full mt-4 bg-[#75a83a] text-white font-bold py-4 rounded-lg hover:opacity-90 active:scale-[0.98] transition-all shadow-md flex items-center justify-center gap-2">
                <span class="material-symbols-outlined text-sm">person_add</span> Registrar Paciente
            </button>
        </form>
    </div>
</div>

<!-- Confirmation Modal -->
<div id="confirm-modal" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 hidden items-center justify-center font-body">
    <div class="bg-surface-container-lowest rounded-xl shadow-2xl w-full max-w-md mx-4 p-6 md:p-8 text-center">
        <div class="w-16 h-16 bg-[#75a83a]/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <span class="material-symbols-outlined text-3xl text-[#75a83a]">help_center</span>
        </div>
        <h3 class="text-xl font-bold text-on-surface font-headline mb-2">Confirmar Acción</h3>
        <p id="confirm-message" class="text-on-surface-variant text-sm mb-8">¿Estás seguro de realizar esta acción?</p>
        <div class="flex gap-4">
            <button id="confirm-cancel" class="flex-1 py-3 rounded-lg bg-surface-container-low text-on-surface font-bold hover:bg-surface-container-high transition-colors">Cancelar</button>
            <button id="confirm-accept" class="flex-1 py-3 rounded-lg bg-[#75a83a] text-white font-bold hover:opacity-90 transition-colors shadow-md">Confirmar</button>
        </div>
    </div>
</div>

<script>
    // Search frontend behavior
    const searchInput = document.getElementById('searchInput');
    if(searchInput) {
        searchInput.addEventListener('input', function(e) {
            const term = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#patientsTableBody tr.group');
            rows.forEach(row => {
                const name = row.querySelector('.patient-name')?.textContent.toLowerCase() || '';
                const email = row.querySelector('.patient-email')?.textContent.toLowerCase() || '';
                if(name.includes(term) || email.includes(term)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    document.getElementById("add-patient-btn").addEventListener("click", () => {
        document.getElementById("add-patient-modal").classList.remove("hidden");
        document.getElementById("add-patient-modal").classList.add("flex");
    });
    document.getElementById("close-modal-btn").addEventListener("click", () => {
        document.getElementById("add-patient-modal").classList.add("hidden");
        document.getElementById("add-patient-modal").classList.remove("flex");
    });

    // Reusable Confirmation Modal Logic
    const confirmModal = document.getElementById("confirm-modal");
    const confirmMsg = document.getElementById("confirm-message");
    const confirmAccept = document.getElementById("confirm-accept");
    const confirmCancel = document.getElementById("confirm-cancel");

    function openConfirm(message, onAccept) {
        confirmMsg.textContent = message;
        confirmModal.classList.remove("hidden");
        confirmModal.classList.add("flex");
        const handler = async () => {
            try {
                await onAccept();
            } finally {
                closeConfirm();
            }
        };
        // Ensure old listeners are removed
        confirmAccept.replaceWith(confirmAccept.cloneNode(true));
        const newAccept = document.getElementById("confirm-accept");
        newAccept.addEventListener("click", handler);
    }

    function closeConfirm() {
        confirmModal.classList.add("hidden");
        confirmModal.classList.remove("flex");
    }

    confirmCancel.addEventListener("click", closeConfirm);

    async function toggleStatus(id) {
        openConfirm(
            "¿Estás seguro de cambiar el estado de este paciente?",
            async () => {
                const response = await fetch(`{{ url_for('therapist.toggle_patient_status', patient_id=0) }}`.replace('0', id), {
                    method: "POST",
                });
                const data = await response.json();
                if (data.success) {
                    location.reload();
                } else {
                    alert("Error: " + (data.message || "No se pudo cambiar el estado"));
                }
            }
        );
    }

    async function deletePatient(id) {
        openConfirm(
            "¿Estás seguro de eliminar permanentemente a este paciente? Esta acción no se puede deshacer.",
            async () => {
                const response = await fetch(`{{ url_for('therapist.delete_patient', patient_id=0) }}`.replace('0', id), {
                    method: "POST",
                });
                const data = await response.json();
                if (data.success) {
                    location.reload();
                } else {
                    alert("Error: " + (data.message || "No se pudo eliminar el paciente"));
                }
            }
        );
    }
</script>
{% endblock %}
"""

with open('app/templates/therapist/patients.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Updated template safely.")
