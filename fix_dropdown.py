import sys

filepath = 'app/templates/admin/users.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_dropdown_btn = '''                <button data-action="toggle-user-menu" data-target="dropdown-{{ u.id }}" class="w-10 h-10 flex items-center justify-center text-gray-400 hover:text-charcoal bg-gray-50 border border-gray-200 dark:border-gray-700 dark:bg-slate-800 dark:text-gray-300 dark:hover:text-white rounded-full hover:bg-gray-100 dark:hover:bg-slate-700 transition-all shadow-sm pointer-events-auto cursor-pointer focus:ring-2 focus:ring-primary/20">
                  <i class="fas fa-ellipsis-v pointer-events-none"></i>
                </button>'''

new_dropdown_btn = '''                {{ btn.action_icon_btn('fas fa-ellipsis-v', 'dropdown-' ~ u.id, 'pointer-events-auto cursor-pointer', 'toggle-user-menu') }}'''

content = content.replace(old_dropdown_btn, new_dropdown_btn)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Dropdown buttons replaced")
