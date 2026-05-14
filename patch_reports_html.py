import re

with open('edysync/src/app/features/admin/pages/reports/reports.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

audit_block = """
<!-- AI AUDIT SECTION -->
<div class="mt-8 mb-8" *ngIf="!loading">
  <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 border-b border-gray-200 pb-4">
    <div>
      <h2 class="text-xl font-bold text-gray-800 flex items-center gap-2">
        <span class="material-symbols-outlined text-primary" style="font-family: 'Material Symbols Outlined'">psychiatry</span>
        Auditoría IA (Whisper + Llama)
      </h2>
      <p class="text-sm text-gray-500">Mide la fidelidad de las sesiones (Programación vs Grabación)</p>
    </div>
    <div class="mt-4 md:mt-0 space-x-2">
      <button (click)="generateReport()" class="bg-primary hover:bg-primary-dark text-white px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-sm flex items-center" [disabled]="aiGenerating">
        <span class="material-symbols-outlined mr-2" style="font-family: 'Material Symbols Outlined'" [class.fa-spin]="aiGenerating">{{ aiGenerating ? 'refresh' : 'auto_awesome' }}</span>
        {{ aiGenerating ? 'Generando Reporte Mágico...' : 'Generar Reporte IA' }}
      </button>
    </div>
  </div>

  <!-- AI Generated Report View -->
  <div *ngIf="aiReport" class="mb-8 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-100 shadow-inner">
    <h3 class="text-lg font-bold text-blue-900 mb-4 flex items-center">
      <span class="material-symbols-outlined mr-2" style="font-family: 'Material Symbols Outlined'">auto_awesome</span> Informe Llama
    </h3>
    <div class="prose prose-blue max-w-none prose-sm" [innerHTML]="aiReport"></div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Audit KPIs -->
    <div class="col-span-1 lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-6 bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
      <div class="flex items-center p-4 bg-gray-50 rounded-lg">
        <div class="p-3 bg-indigo-100 text-indigo-600 rounded-full mr-4">
          <span class="material-symbols-outlined text-2xl" style="font-family: 'Material Symbols Outlined'">fact_check</span>
        </div>
        <div>
          <p class="text-sm text-gray-500 font-medium">Auditorías Totales</p>
          <p class="text-2xl font-bold text-gray-800">{{ auditStats.total }}</p>
        </div>
      </div>
      <div class="flex items-center p-4 bg-gray-50 rounded-lg">
        <div class="p-3 bg-green-100 text-green-600 rounded-full mr-4">
          <span class="material-symbols-outlined text-2xl" style="font-family: 'Material Symbols Outlined'">insights</span>
        </div>
        <div>
          <p class="text-sm text-gray-500 font-medium">Promedio Fidelidad (0-10)</p>
          <p class="text-2xl font-bold text-gray-800">{{ auditStats.avg_score }} <span class="text-sm font-normal text-gray-500">/ 10</span></p>
        </div>
      </div>
    </div>

    <!-- Top Therapists -->
    <div class="col-span-1 lg:col-span-1 bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
      <h3 class="text-lg font-bold text-gray-800 border-b pb-3 mb-4">Desempeño por Terapista</h3>
      <div class="space-y-4">
        <div *ngFor="let t of auditStats.by_therapist" class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-xs uppercase">{{ t.name[0] }}</div>
            <div>
              <p class="text-sm font-medium text-gray-800">{{ t.name }}</p>
              <p class="text-xs text-gray-500">{{ t.count }} evaluadas</p>
            </div>
          </div>
          <div class="text-right">
            <span class="inline-block px-2 py-1 rounded bg-green-50 text-green-700 font-bold text-xs">{{ t.avg_score }}/10</span>
          </div>
        </div>
        <p *ngIf="!auditStats.by_therapist || auditStats.by_therapist.length === 0" class="text-sm text-gray-500 italic">No hay datos suficientes.</p>
      </div>
    </div>

    <!-- Recent Audits -->
    <div class="col-span-1 lg:col-span-2 bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
      <div class="p-6 border-b border-gray-100 flex justify-between items-center">
        <h3 class="text-lg font-bold text-gray-800">Últimas Evaluaciones AI</h3>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm text-left align-middle whitespace-nowrap overflow-hidden">
          <thead class="bg-gray-50 text-gray-600 text-xs uppercase font-semibold">
            <tr>
              <th scope="col" class="px-6 py-3">Score</th>
              <th scope="col" class="px-6 py-3">Fecha</th>
              <th scope="col" class="px-6 py-3">Sesión / Paciente</th>
              <th scope="col" class="px-6 py-3">Terapeuta</th>
              <th scope="col" class="px-6 py-3 text-right">Acción</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 border-t border-gray-100 bg-white">
            <tr *ngFor="let r of auditStats.recent" class="hover:bg-gray-50/50 transition-colors">
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" 
                      [ngClass]="{'bg-green-100 text-green-800': r.score >= 8, 'bg-yellow-100 text-yellow-800': r.score >= 5 && r.score < 8, 'bg-red-100 text-red-800': r.score < 5}">
                  {{ r.score }}/10
                </span>
              </td>
              <td class="px-6 py-4 text-gray-600">{{ r.date | date:'short' }}</td>
              <td class="px-6 py-4 font-medium text-gray-900">{{ r.title }}</td>
              <td class="px-6 py-4 text-gray-600">{{ r.therapist }}</td>
              <td class="px-6 py-4 text-right">
                <button [routerLink]="['/admin/sessions']" class="text-primary hover:text-primary-dark font-medium text-xs">Ver Sesión</button>
              </td>
            </tr>
            <tr *ngIf="!auditStats.recent || auditStats.recent.length === 0">
              <td colspan="5" class="px-6 py-8 text-center text-gray-500">No hay auditorías recientes.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>
"""

# Insert the audit_block right after the top summary cards (before the main grid)
pattern = r'(<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">)'
html_content = re.sub(pattern, audit_block + r'\n\1', html_content, count=1)

with open('edysync/src/app/features/admin/pages/reports/reports.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
