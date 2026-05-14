import re

with open('edysync/src/app/features/admin/pages/reports/reports.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

audit_block = """
<!-- AI AUDIT SECTION -->
<div class="mt-8 mb-8 bg-surface rounded-lg shadow-soft p-6 border-l-4 border-indigo-500">
  <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 pb-4 border-b border-gray-100">
    <div>
      <h2 class="text-xl font-bold text-gray-800 flex items-center gap-2">
        <span class="material-symbols-outlined text-primary" style="font-family: 'Material Symbols Outlined'">psychiatry</span>
        Auditoría IA (Whisper + Llama)
      </h2>
      <p class="text-sm text-gray-500">Mide la fidelidad de las sesiones (Programación vs Grabación)</p>
    </div>
    <div class="mt-4 md:mt-0">
      <button (click)="generateReport()" class="bg-primary hover:bg-primary-dark text-white px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-sm flex items-center gap-2" [disabled]="aiGenerating">
        <span class="material-symbols-outlined" style="font-family: 'Material Symbols Outlined'" [class.fa-spin]="aiGenerating">{{ aiGenerating ? 'refresh' : 'auto_awesome' }}</span>
        {{ aiGenerating ? 'Generando Reporte...' : 'Generar Reporte Llama' }}
      </button>
    </div>
  </div>

  <!-- AI Generated Report View -->
  <div *ngIf="aiReport" class="mb-8 p-6 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl border border-indigo-100">
    <h3 class="text-lg font-bold text-indigo-900 mb-4 flex items-center">
      <span class="material-symbols-outlined mr-2" style="font-family: 'Material Symbols Outlined'">auto_awesome_mosaic</span> Informe Llama
    </h3>
    <div class="prose prose-indigo max-w-none prose-sm" [innerHTML]="aiReport"></div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Audit KPIs -->
    <div class="col-span-1 lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="flex items-center p-4 bg-indigo-500/10 rounded-lg border border-indigo-100">
        <div class="p-3 bg-indigo-100 text-indigo-600 rounded-full mr-4">
          <span class="material-symbols-outlined text-2xl" style="font-family: 'Material Symbols Outlined'">fact_check</span>
        </div>
        <div>
          <p class="text-xs uppercase tracking-widest text-indigo-600 font-bold">Auditorías Totales</p>
          <p class="text-2xl font-bold text-gray-800">{{ auditStats?.total || 0 }}</p>
        </div>
      </div>
      <div class="flex items-center p-4 bg-green-500/10 rounded-lg border border-green-100">
        <div class="p-3 bg-green-100 text-green-600 rounded-full mr-4">
          <span class="material-symbols-outlined text-2xl" style="font-family: 'Material Symbols Outlined'">insights</span>
        </div>
        <div>
          <p class="text-xs uppercase tracking-widest text-green-600 font-bold">Promedio Fidelidad (0-10)</p>
          <p class="text-2xl font-bold text-gray-800">{{ auditStats?.avg_score || 0 }} <span class="text-sm font-normal text-gray-500">/ 10</span></p>
        </div>
      </div>
    </div>

    <!-- Top Therapists -->
    <div class="col-span-1 bg-surface p-4 rounded-xl border border-gray-100 shadow-sm">
      <h3 class="text-md font-bold text-gray-800 mb-4">Desempeño por Terapista</h3>
      <div class="space-y-3">
        <div *ngFor="let t of auditStats?.by_therapist" class="flex items-center justify-between p-2 hover:bg-gray-50 rounded-lg">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-xs uppercase">{{ t.name[0] }}</div>
            <div>
              <p class="text-sm font-medium text-gray-800">{{ t.name }}</p>
              <p class="text-xs text-gray-500">{{ t.count }} evaluadas</p>
            </div>
          </div>
          <span class="px-2 py-1 rounded bg-green-100 text-green-800 font-bold text-xs">{{ t.avg_score }}/10</span>
        </div>
        <p *ngIf="!auditStats?.by_therapist?.length" class="text-sm text-gray-500 italic">No hay datos suficientes.</p>
      </div>
    </div>

    <!-- Recent Audits -->
    <div class="col-span-1 lg:col-span-2 bg-surface rounded-xl border border-gray-100 shadow-sm overflow-hidden">
      <div class="p-4 border-b border-gray-100">
        <h3 class="text-md font-bold text-gray-800">Últimas Evaluaciones AI</h3>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm text-left whitespace-nowrap">
          <thead class="bg-gray-50 text-gray-600 text-[10px] uppercase tracking-wider font-semibold">
            <tr>
              <th class="px-4 py-3">Score</th>
              <th class="px-4 py-3">Sesión / Paciente</th>
              <th class="px-4 py-3">Terapeuta</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr *ngFor="let r of auditStats?.recent" class="hover:bg-gray-50/50">
              <td class="px-4 py-3">
                <span class="inline-flex px-2 py-1 rounded-full text-xs font-bold" 
                      [ngClass]="{'bg-green-100 text-green-800': r.score >= 8, 'bg-yellow-100 text-yellow-800': r.score >= 5 && r.score < 8, 'bg-red-100 text-red-800': r.score < 5}">
                  {{ r.score }}/10
                </span>
              </td>
              <td class="px-4 py-3 font-medium text-gray-900">{{ r.title }}</td>
              <td class="px-4 py-3 text-gray-600">{{ r.therapist }}</td>
            </tr>
            <tr *ngIf="!auditStats?.recent?.length">
              <td colspan="3" class="px-4 py-6 text-center text-gray-500 text-sm">No hay auditorías recientes.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>
"""

# Append to the end of the content right before the closing `} }` or `  } \n</div>` 
# I will just write it after the first </div> that closes the Financial Section
# There are two inner grids, I'll put it before `<div class="grid grid-cols-1 md:grid-cols-2 gap-6">` (the one for therapist tables) or just append it before `</div>` at the end
html_content = html_content.replace("  } \n</div>", f"  }}\n\n  {audit_block}\n</div>")

with open('edysync/src/app/features/admin/pages/reports/reports.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
