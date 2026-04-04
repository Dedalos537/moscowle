import re
with open('app/templates/admin/sessions.html', 'r') as f:
    text = f.read()

# 1. Add CSS
css_styles = """
{% block head %}
{{ super() }}
<style>
/* Botones redondeados tipo sidebar */
.fc .fc-button {
    border-radius: 9999px !important;
}
.fc .fc-button-primary {
    background-color: var(--color-primary, #75a83a) !important;
    border-color: var(--color-primary, #75a83a) !important;
    text-transform: capitalize;
}
.fc .fc-button-primary:hover {
    background-color: var(--color-primary-hover, #628f2e) !important;
    border-color: var(--color-primary-hover, #628f2e) !important;
}
.fc .fc-button-primary:not(:disabled):active,
.fc .fc-button-primary:not(:disabled).fc-button-active {
    background-color: var(--color-primary-hover, #628f2e) !important;
    border-color: var(--color-primary-hover, #628f2e) !important;
}
.fc-direction-ltr .fc-button-group > .fc-button:not(:first-child) {
    border-top-l    border-top-l    border-top-l    border-top-l    border !important;
    margin-left: 1px;
}
.fc-direction-ltr .fc-button-group > .fc-button:not(:last-child) {
    border-top-right-radius: 0 !important;
    border-bottom-right-radius: 0 !important;
}

/* Spinner animado Tailwind */
@keyframes spin {
  to { transform: rotate(360deg); }
}
.animate-spin-slow {
  animation: spin 1s linear infinite;
}
</style>
{% endblock %}
"""

if "{% block head %}" not in text:
    text = text.replace("{% block content %}", css_styles + "\n{% block content %}")

# 2. Add loading div and relative class
container_regex = r'<div class="bg-surface p-4 md:p-6 rounded-soft shadow-soft border border-gray-100 min-h-\[600px\]">'
new_container = """<div class="bg-surface p-4 md:p-6 rounded-soft shadow-soft border border-gray-100 min-h-[600px] relative">
        <!-- Overlay Cargando -->
        <div id="calendar-loading" class="absolute inset-0 bg-white/70 z-50 flex flex-col items-center justify-center rounded-soft backdrop-blur-sm" style="display: none;">
            <i class="fa-solid fa-spinner animate-spin-slow text-4xl text-primary mb-3"></i>
            <span class="text-gray-600 font-medium animate-pulse">Cargando calendario...</span>
        </div>"""
text = re.sub(r'<div class="bg-surface p-4 md:p-6 rounded-soft shadow-soft border border-gray-100 min-h-\[600px\]">', new_container, text)

# 3. Add loading callback to fullcalendar
js_target = r"events: {"
js_replacement = """loading: function(isLoading) {
                const spinner = document.getElementById('calendar-loading');
                if (spinner) {
                    spinner.style.display = isLoading ? 'flex' : 'none';
                }
            },
            events: {"""
text = text.replace(js_target, js_replacement)

# Make sure "Nueva programacion en bloque" is rounded-full
text = text.replace('rounded-soft hover:bg-opacity-90', 'rounded-full hover:bg-opacity-90')

with open('app/templates/admin/sessions.html', 'w') as f:
    f.write(text)

