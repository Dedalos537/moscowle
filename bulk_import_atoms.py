import os

TEMPLATES_DIRS = ['app/templates/admin', 'app/templates/therapist', 'app/templates/patient']

imports = """
{% import 'components/atoms/badges.html' as atoms %}
{% import 'components/atoms/buttons.html' as btn %}
{% import 'components/atoms/inputs.html' as inputs %}
{% import 'components/molecules/cards.html' as cards %}
{% import 'components/organisms/tables.html' as tables %}
{% import 'components/molecules/forms.html' as forms %}
"""

for root_dir in TEMPLATES_DIRS:
    for filename in os.listdir(root_dir):
        if not filename.endswith('.html'): continue
        filepath = os.path.join(root_dir, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "{% import 'components/atoms/badges.html' as atoms %}" in content:
            continue # already processed
            
        # Try to inject after extends or active_page
        lines = content.split('\n')
        inject_idx = -1
        for i, line in enumerate(lines):
            if '{% block' in line:
                inject_idx = i - 1
                break
        
        if inject_idx == -1:
            for i, line in enumerate(lines):
                if '{% extends' in line or '{% set' in line:
                    inject_idx = i
        
        if inject_idx != -1:
            lines.insert(inject_idx + 1, imports)
            with open(filepath, 'w', encoding='utf-8') as f:
                 f.write('\n'.join(lines))
                 print(f"Injected imports into {filepath}")

