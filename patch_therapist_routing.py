import re

with open('edysync/src/app/features/therapist/therapist-routing-module.ts', 'r', encoding='utf-8') as f:
    ts_content = f.read()

# Add import
import_line = "import { TherapistDashboard } from './pages/dashboard/dashboard';\n"
ts_content = import_line + ts_content

# Add route
route_line = "{ path: 'dashboard', component: TherapistDashboard },"
ts_content = re.sub(r'children: \[\n', f'children: [\n      {route_line}\n', ts_content)
ts_content = re.sub(r"\{ path: '', redirectTo: 'sessions'", "{ path: '', redirectTo: 'dashboard'", ts_content)

with open('edysync/src/app/features/therapist/therapist-routing-module.ts', 'w', encoding='utf-8') as f:
    f.write(ts_content)
