import re
import os

directories = ['app/templates/admin', 'app/templates/therapist', 'app/templates/patient']

# Find standard hardcoded status pills. For example:
# <span class="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full"...>Activo</span>
# We'll use a very careful regex for <span> classes that just render a text inside.

badge_pattern = re.compile(
    r'<span\s+class="([^"]*px-[0-9][^"]*py-[0-9][^"]*rounded-(?:full|md|lg|xl)[^"]*bg-[a-z]+-[0-9]+[^"]*text-[a-z]+-[0-9]+[^"]*)"[^>]*>\s*([a-zA-ZÁÉÍÓÚáéíóúÑñ0-9_\s]+)\s*</span>',
    re.IGNORECASE
)

def badge_repl(m):
    classes = m.group(1).strip()
    text = m.group(2).strip()
    return f"{{{{ atoms.pill_badge('{text}', '{classes}') }}}}"

for root_dir in directories:
    for filename in os.listdir(root_dir):
        if not filename.endswith('.html'): continue
        filepath = os.path.join(root_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = badge_pattern.sub(badge_repl, content)

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated badges in {filepath}")

