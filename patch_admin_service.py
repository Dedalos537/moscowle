import re

with open('edysync/src/app/core/services/admin.service.ts', 'r', encoding='utf-8') as f:
    ts_content = f.read()

new_method = """  getAuditStats(): Observable<any> {
    return this.http.get(`${this.apiUrl}/admin/audit-stats`, { headers: this.getHeaders() });
  }

  generateIAReport(): Observable<any> {
    return this.http.post(`${this.apiUrl}/admin/generate-ia-report`, {}, { headers: this.getHeaders() });
  }
"""

ts_content = re.sub(r'}\s*$', new_method + '\n}', ts_content)

with open('edysync/src/app/core/services/admin.service.ts', 'w', encoding='utf-8') as f:
    f.write(ts_content)
