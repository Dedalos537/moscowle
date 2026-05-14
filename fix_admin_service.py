import re

with open('edysync/src/app/core/services/admin.service.ts', 'r', encoding='utf-8') as f:
    ts_content = f.read()

ts_content = ts_content.replace('`${this.apiUrl}/admin/audit-stats`', "'/api/admin/audit-stats'")
ts_content = ts_content.replace('`${this.apiUrl}/admin/generate-ia-report`', "'/admin/generate-ia-report'") # Note this hits the flask route directly, since it's in admin_routes.py

# Wait, `this.getHeaders()` probably does not exist either? Let's check:
ts_content = ts_content.replace(', { headers: this.getHeaders() }', '')

with open('edysync/src/app/core/services/admin.service.ts', 'w', encoding='utf-8') as f:
    f.write(ts_content)
