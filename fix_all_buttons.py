import os
import re

directories = ['app/templates/admin', 'app/templates/therapist', 'app/templates/patient']

# Regex pattern for exactly the large action_icon_btn that you fixed in users:
# '<button type="button" data-action="close-edit-modal" class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-200 dark:hover:bg-slate-800 text-gray-500 transition-colors">'
# We will do something simpler: Replace the ellipsis table row buttons.
ellipsis_pattern = re.compile(r'<button[^>]*data-action="toggle-[^>]*"\s+data-target="([^"]+)"[^>]*>\s*<i class="[^"]*fa-ellipsis-v[^"]*"></i>\s*</button>', re.DOTALL)

close_btn_pattern = re.compile(r'<button[^>]*data-action="close-[^>]*"[^>]*>\s*<i class="[^"]*fa-times[^"]*"></i>\s*</button>', re.DOTALL)

for root_dir in directories:
    for filename in os.listdir(root_dir):
        if not filename.endswith('.html'): continue
        filepath = os.path.join(root_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        new_content = content
        
        # Replace ellipsis buttons
        def elp_repl(m):
            target = m.group(1)
            # Find the original data action if possible, else default toggle-dropdown
            return f"{{{{ btn.action_icon_btn('fas fa-ellipsis-v', '{target}', 'pointer-events-auto cursor-pointer', 'toggle-user-menu') }}}}"
        
        new_content = ellipsis_pattern.sub(elp_repl, new_content)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated ellipsis in {filepath}")

