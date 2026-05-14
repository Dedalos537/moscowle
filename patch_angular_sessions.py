import re

with open('edysync/src/app/features/admin/pages/sessions/sessions.ts', 'r', encoding='utf-8') as f:
    ts_content = f.read()

# Add imports for HttpClient if not already there, but they are likely available or injected.
# We'll see how to add the logic inside the class.

with open('edysync/src/app/features/admin/pages/sessions/sessions.html', 'r', encoding='utf-8') as f:
    html_content = f.read()
print("Angular Session Files Read")
