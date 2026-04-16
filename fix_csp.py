import re

filepath = 'app/templates/admin/csp_reports.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# I will just write a new template because the old one is completely Bootstrap and simple
new_template = """{% extends 'therapist/base.html' %}
{% set active_page = 'admin_reports' %}

{% import 'components/atoms/badges.html' as atoms %}
{% import 'components/atoms/buttons.html' as btn %}
{% import 'components/atoms/inputs.html' as inputs %}
{% import 'components/molecules/cards.html' as cards %}
{% import 'components/organisms/tables.html' as tables %}
{% import 'components/molecules/forms.html' as forms %}

{% block header_content %}
<div>
  <h2 class="text-2xl font-bold text-textDark">Informes CSP</h2>
  <p class="text-sm text-gray-500">Monitoreo de violaciones Content Security Policy</p>
</div>
{% endblock %}

{% block content %}
<div class="p-4 md:p-8 space-y-6">
  <div class="bg-surface rounded-soft shadow-soft p-6 border-l-4 border-indigo-500">
    <form method="get" class="flex flex-col md:flex-row gap-4 items-end mb-6">
      {{ inputs.text_input('directive', 'Directive', placeholder='violated directive', value=request.args.get('directive',''), wrapper_classes='w-full md:w-1/4') }}
      {{ inputs.text_input('blocked_uri', 'Blocked URI', placeholder='blocked URI', value=request.args.get('blocked_uri',''), wrapper_classes='w-full md:w-1/4') }}
      {{ inputs.text_input('since', 'Since', placeholder='YYYY-MM-DD', type='date', value=request.args.get('since',''), wrapper_classes='w-full md:w-1/4') }}
      {{ btn.primary_btn(text='Filtrar', extra_classes='w-full md:w-auto h-10', icon='fas fa-filter') }}
    </form>
    
    <div class="overflow-x-auto">
      <table class="w-full min-w-[800px]">
        {{ tables.table_header([
          {'label': 'ID'},
          {'label': 'Recibido'},
          {'label': 'Document URI'},
          {'label': 'Directive'},
          {'label': 'Blocked URI'},
          {'label': 'IP'}
        ]) }}
        <tbody class="divide-y divide-gray-100 dark:divide-gray-800">
          {% for r in pagination.items %}
          <tr class="hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-medium">#{{ r.id }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">{{ r.received_at }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-indigo-600 truncate max-w-[200px]"><a href="{{ r.document_uri }}" target="_blank" class="hover:underline">{{ r.document_uri }}</a></td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-charcoal">
                {{ atoms.pill_badge(r.violated_directive, 'bg-red-100 text-red-800 border border-red-200 uppercase text-[10px] font-bold') if r.violated_directive else '' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 truncate max-w-[200px]">{{ r.blocked_uri }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">{{ r.ip_address }}</td>
          </tr>
          {% else %}
          {{ tables.empty_state(col_count=6, title="No hay informes", description="No se han registrado violaciones de políticas de seguridad.", icon="fas fa-shield-alt text-green-500") }}
          {% endfor %}
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div class="mt-6 flex justify-between items-center bg-gray-50 dark:bg-slate-800 p-4 rounded-xl border border-gray-100 dark:border-gray-700">
      <div>
        <span class="text-sm text-gray-600 dark:text-gray-400">Página <span class="font-bold text-gray-900 dark:text-white">{{ pagination.page }}</span> de {{ pagination.pages or 1 }}</span>
      </div>
      <div class="flex gap-2">
        {% if pagination.has_prev %}
          <a href="?page={{ pagination.prev_num }}{% if request.args.get('directive') %}&directive={{ request.args.get('directive') }}{% endif %}{% if request.args.get('blocked_uri') %}&blocked_uri={{ request.args.get('blocked_uri') }}{% endif %}{% if request.args.get('since') %}&since={{ request.args.get('since') }}{% endif %}" class="px-4 py-2 bg-white dark:bg-slate-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 transition-colors">Anterior</a>
        {% else %}
          <button disabled class="px-4 py-2 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-medium text-gray-400 cursor-not-allowed">Anterior</button>
        {% endif %}

        {% if pagination.has_next %}
          <a href="?page={{ pagination.next_num }}{% if request.args.get('directive') %}&directive={{ request.args.get('directive') }}{% endif %}{% if request.args.get('blocked_uri') %}&blocked_uri={{ request.args.get('blocked_uri') }}{% endif %}{% if request.args.get('since') %}&since={{ request.args.get('since') }}{% endif %}" class="px-4 py-2 bg-white dark:bg-slate-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 transition-colors">Siguiente</a>
        {% else %}
          <button disabled class="px-4 py-2 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-medium text-gray-400 cursor-not-allowed">Siguiente</button>
        {% endif %}
      </div>
    </div>
  </div>
</div>
{% endblock %}
"""

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_template)
print("CSP Report refactored")
