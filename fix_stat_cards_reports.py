import re

filepath = 'app/templates/admin/reports.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Grid block
old_cards = """    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <!-- Real Income -->
        <div class="bg-green-50 p-4 rounded-xl border border-green-100">
            <span class="text-xs font-bold text-green-600 uppercase tracking-widest">Ingresos Reales</span>
            <div class="text-3xl font-bold text-charcoal mt-2">S/ {{ "%.2f"|format(financials.income_real) }}</div>
            <p class="text-xs text-gray-500 mt-1">Recaudado este mes</p>
        </div>
        
        <!-- Expected Income -->
        <div class="bg-blue-50 p-4 rounded-xl border border-blue-100">
            <span class="text-xs font-bold text-blue-600 uppercase tracking-widest">Proyección</span>
            <div class="text-3xl font-bold text-charcoal mt-2">S/ {{ "%.2f"|format(financials.income_expected) }}</div>
            <p class="text-xs text-gray-500 mt-1">Si todos pagaran a tiempo</p>
        </div>

        <!-- Overdue -->
        <div class="bg-red-50 p-4 rounded-xl border border-red-100">
            <span class="text-xs font-bold text-red-600 uppercase tracking-widest">Morosidad Acumulada</span>
            <div class="text-3xl font-bold text-red-600 mt-2">S/ {{ "%.2f"|format(financials.overdue_amount) }}</div>
            <p class="text-xs text-red-400 mt-1">{{ financials.overdue_users_count }} usuarios con deuda</p>
        </div>
        
        <!-- Completion Rate -->
        <div class="bg-gray-50 p-4 rounded-xl border border-gray-100 flex flex-col justify-center items-center">
             <!-- Circular Percent Placeholder or simple text -->
             {% set percent = (financials.income_real / financials.income_expected * 100) if financials.income_expected > 0 else 0 %}
             <div class="text-2xl font-bold text-charcoal">{{ "%.1f"|format(percent) }}%</div>
             <p class="text-xs text-gray-500 font-medium uppercase">Ejecución</p>
             <div class="w-full bg-gray-200 rounded-full h-1.5 mt-2">
                <div class="bg-olive h-1.5 rounded-full" style="width: {{ percent }}%"></div>
             </div>
        </div>
    </div>"""

new_cards = """    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <!-- Real Income -->
        {{ cards.stat_card(
            id='card-income-real', 
            title='Ingresos Reales', 
            initial_value='S/ ' ~ ("%.2f"|format(financials.income_real)), 
            subtext='Recaudado este mes', 
            bg_color_class='bg-green-500/10', 
            text_color_class='text-green-600'
        ) }}
        
        <!-- Expected Income -->
        {{ cards.stat_card(
            id='card-income-exp', 
            title='Proyección', 
            initial_value='S/ ' ~ ("%.2f"|format(financials.income_expected)), 
            subtext='Si todos pagaran a tiempo', 
            bg_color_class='bg-blue-500/10', 
            text_color_class='text-charcoal dark:text-white'
        ) }}

        <!-- Overdue -->
        {{ cards.stat_card(
            id='card-income-overdue', 
            title='Morosidad Acumulada', 
            initial_value='S/ ' ~ ("%.2f"|format(financials.overdue_amount)), 
            subtext=financials.overdue_users_count ~ ' usuarios con deuda', 
            bg_color_class='bg-red-500/10', 
            text_color_class='text-red-500'
        ) }}
        
        <!-- Completion Rate -->
        {% set percent = (financials.income_real / financials.income_expected * 100) if financials.income_expected > 0 else 0 %}
        {{ cards.stat_card(
            id='card-income-percent', 
            title='Ejecución', 
            initial_value=("%.1f"|format(percent)) ~ '%', 
            subtext='Progreso de cobro', 
            bg_color_class='bg-olive/10', 
            text_color_class='text-charcoal dark:text-white'
        ) }}
    </div>"""

content = content.replace(old_cards, new_cards)

old_expenses = """    <!-- Expenses and Net Row -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div class="bg-gray-50 p-4 rounded-xl border border-gray-200">
            <span class="text-xs font-bold text-gray-600 uppercase tracking-widest">Gastos Totales</span>
            <div class="text-3xl font-bold text-charcoal mt-2">S/ {{ "%.2f"|format(financials.expenses or 0) }}</div>
            <p class="text-xs text-gray-500 mt-1">Nómina + Operativos</p>
        </div>
        <div class="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
            <span class="text-xs font-bold text-indigo-600 uppercase tracking-widest">Utilidad Neta (Caja)</span>
            <div class="text-3xl font-bold text-indigo-700 mt-2">S/ {{ "%.2f"|format(financials.net_profit or 0) }}</div>
            <p class="text-xs text-indigo-400 mt-1">Ingresos Reales - Gastos</p>
        </div>
    </div>"""

new_expenses = """    <!-- Expenses and Net Row -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {{ cards.stat_card(
            id='card-expenses', 
            title='Gastos Totales', 
            initial_value='S/ ' ~ ("%.2f"|format(financials.expenses or 0)), 
            subtext='Nómina + Operativos', 
            bg_color_class='bg-gray-500/10', 
            text_color_class='text-charcoal dark:text-white'
        ) }}
        
        {{ cards.stat_card(
            id='card-net', 
            title='Utilidad Neta (Caja)', 
            initial_value='S/ ' ~ ("%.2f"|format(financials.net_profit or 0)), 
            subtext='Ingresos Reales - Gastos', 
            bg_color_class='bg-indigo-500/10', 
            text_color_class='text-indigo-600'
        ) }}
    </div>"""

content = content.replace(old_expenses, new_expenses)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated cards")
