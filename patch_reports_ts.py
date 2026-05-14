import re

with open('edysync/src/app/features/admin/pages/reports/reports.ts', 'r', encoding='utf-8') as f:
    ts_content = f.read()

new_props = """  // --- AUDITORIA IA ---
  auditStats: any = { total: 0, avg_score: 0, recent: [], by_therapist: [] };
"""
ts_content = re.sub(r'  loading = true;', new_props + '\n  loading = true;', ts_content)

load_audit_call = """
    this.adminService.getAuditStats().subscribe({
      next: (res: any) => {
        if (res.success && res.data) {
          this.auditStats = res.data;
        }
      },
      error: (err) => console.error("Error cargando Stats Auditoria", err)
    });
"""

ts_content = re.sub(r'this\.adminService\.getFinancialSummary\(\)\.subscribe', load_audit_call + '\n    this.adminService.getFinancialSummary().subscribe', ts_content)

ia_report_methods = """
  generateReport() {
    if (!confirm('Esta operación tomará 1-2 minutos y analizará las últimas notas transcritas. ¿Continuar?')) {
      return;
    }
    
    this.aiGenerating = true;
    this.aiReport = null;
    
    this.adminService.generateIAReport().subscribe({
      next: (res: any) => {
        this.aiGenerating = false;
        if (res.success) {
          this.aiReport = res.report;
        } else {
          alert('Error: ' + res.error);
        }
      },
      error: (err) => {
        this.aiGenerating = false;
        alert('Error de conexión al generar el reporte.');
        console.error(err);
      }
    })
  }
"""

ts_content = re.sub(r'}\s*$', ia_report_methods + '\n}', ts_content)

with open('edysync/src/app/features/admin/pages/reports/reports.ts', 'w', encoding='utf-8') as f:
    f.write(ts_content)
