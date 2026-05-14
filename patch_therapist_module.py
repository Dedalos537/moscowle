import re

with open('edysync/src/app/features/therapist/therapist-module.ts', 'r', encoding='utf-8') as f:
    ts_content = f.read()

import_line = "import { TherapistDashboard } from './pages/dashboard/dashboard';\n"
ts_content = import_line + ts_content

ts_content = re.sub(r'declarations: \[\n', "declarations: [\n    TherapistDashboard,\n", ts_content)

with open('edysync/src/app/features/therapist/therapist-module.ts', 'w', encoding='utf-8') as f:
    f.write(ts_content)
