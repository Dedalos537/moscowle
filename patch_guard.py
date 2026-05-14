import re

with open('edysync/src/app/core/guards/role.guard.ts', 'r', encoding='utf-8') as f:
    ts_content = f.read()

ts_content = ts_content.replace("this.router.navigate(['/admin/dashboard']);", "this.router.navigate(['/auth/login']);")

with open('edysync/src/app/core/guards/role.guard.ts', 'w', encoding='utf-8') as f:
    f.write(ts_content)
