import sys

filepath = 'app/templates/admin/users.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix drawer close button for Edit Modal
old_close = '''                <button type="button" data-action="close-edit-modal" class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-200 dark:hover:bg-slate-800 text-gray-500 transition-colors">
                    <i class="fas fa-times"></i>
                </button>'''
new_close = '''                {{ btn.action_icon_btn('fas fa-times', '', 'w-8 h-8 rounded-full hover:bg-gray-200 dark:hover:bg-slate-800 text-gray-500 hover:text-gray-900 border-none shadow-none', 'close-edit-modal') }}'''
content = content.replace(old_close, new_close)

# Fix drawer close for User Reset Modal
old_close_reset = '''        <button id="closeResetDrawerBtn" class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-200 dark:hover:bg-slate-800 text-gray-500 transition-colors">
            <i class="fas fa-times"></i>
        </button>'''
new_close_reset = '''        {{ btn.action_icon_btn('fas fa-times', '', 'w-8 h-8 rounded-full hover:bg-gray-200 dark:hover:bg-slate-800 text-gray-500 hover:text-gray-900 border-none shadow-none', '') }}'''
content = content.replace(old_close_reset, new_close_reset.replace('action=""', 'id="closeResetDrawerBtn"'))

# Fix drawer close for Create
old_close_create = '''          <button data-action="close-create" class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-200 dark:hover:bg-slate-800 text-gray-500 transition-colors">
              <i class="fas fa-times"></i>
          </button>'''
new_close_create = '''          {{ btn.action_icon_btn('fas fa-times', '', 'w-8 h-8 rounded-full hover:bg-gray-200 dark:hover:bg-slate-800 text-gray-500 hover:text-gray-900 border-none shadow-none', 'close-create') }}'''
content = content.replace(old_close_create, new_close_create)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Headers updated")
