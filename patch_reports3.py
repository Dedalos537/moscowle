import re

with open('edysync/src/app/features/admin/pages/reports/reports.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

audit_block = """
  <!-- AI AUDIT SECTION -->
  <div class="bg-surface rounded-lg shadow-soft p-6 border-l-4 border-indigo-500 mt-6 lg:col-span-2">
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 pb-4 border-b border-gray-100">
      <div>
        <h2 class="text-xl font-bold text-gray-800 flex items-center gap-2">
          <span class="material-symbols-outlined text-primary" style="font-family: 'Material Symbols Outlined'">psychiatry</span>
          Auditoría IA (Whisper + Llama)
        </h2>
        <p class="text-sm text-gray-500">Mide la fidelidad de las sesiones (Programación vs Grabación)</p>
      </div>
      <div class="mt-4 md:mt-0">
        <button (click)="generateReport()" class="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-sm flex items-center gap-2" [disabled]="aiGenerating">
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
      <div class="col-span-1 lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="flex items-center p-4 bg-indigo-50 rounded-lg border border-indigo-100">
          <div class="p-3 bg-indigo-100 text-indigo-600 rounded-full mr-4">
            <span class="material-symbols-outlined text-2xl" style="font-family: 'Material Symbols Outlined'">fact_check</span>
          </div>
          <div>
            <p class="text-[10px] uppercase tracking-widest text-indigo-600 font-bold mb-1">Auditorías Totales</p>
            <p class="text-2xl font-black text-gray-800">{{ auditStats?.total || 0 }}</p>
          </div>
        </div>
        <div class="flex items-center p-4 bg-green-50 rounded-lg border border-green-100">
          <div class="p-3 bg-green-100 text-green-600 rounded-full mr-4">
            <span class="material-symbols-outlined text-2xl" style="font-family: 'Material Symbols Outlined'">insights</span>
          </div>
          <div>
            <p class="text-[10px] uppercase tracking-widest text-green-600 font-bold mb-1">Promedio Fidelidad</p>
            <p class="text-2xl font-black text-gray-800">{{ auditStats?.avg_score || 0 }} <span class="text-sm font-normal text-gray-500">/ 10</span></p>
          </div>
        </div>
      </div>

      <div class="col-span-1 bg-white p-4 rounded-xl border border-gray-100">
        <h3 class="text-sm font-bold text-gray-800 mb-3 border-b pb-2">Top Terapistas</h3>
        <div class="space-y-2">
          <div *ngFor="let t of auditStats?.by_therapist" class="flex justify-between items-center text-sm p-2 hover:bg-gray-50 rounded">
            <span class="font-medium text-gray-700">{{ t.name }}</span>
            <span class="bg-green-100 text-green-800 font-bold px-2 py-0.5 rounded text-xs">{{ t.avg_score }}/10</span>
          </div>
          <p *ngIf="!auditStats?.by_therapist?.length" class="text-xs text-center text-gray-400 py-4">No data</p>
        </div>
      </div>

      <div class="col-span-1 lg:col-span-2 bg-white rounded-xl border border-gray-100 overflow-hidden">
        <h3 class="text-sm font-bold text-gray-800 p-3 border-b bg-gray-50">Últimas Auditorías</h3>
        <table class="w-full text-left text-sm">
          <tbody>
            <tr *ngFor="let r of auditStats?.recent" class="border-b last:border-b-0">
              <td class="p-3 font-medium">{{ r.title }}</td>
              <td class="p-3 text-gray-500 text-xs">{{ r.therapist }}</td>
              <td class="p-3 text-right">
                <span class="px-2 py-1 rounded text-xs font-bold bg-gray-100">{{ r.score }}/10</span>
              </td>
            </tr>
            <tr *ngIf="!auditStats?.recent?.length">
              <td colspan="3" class="p-6 text-center text-gray-400 text-xs">Aún no hay auditorías.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
"""

# Try to insert it before the last `  }` and `</div>` of the main container.
# Currently it ends with:
#               }
#             </tbody>
#           </table>
#         </div>
#       </div>
#     </div>
#   }
# </div>

html_content = re.sub(r'    </div>\n  }\n</div>', r'    </div>\n' + audit_block + r'\n  }\n</div>', html_content)

with open('edysync/src/app/features/admin/pages/reports/reports.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
