import sys

def process(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Reset Password Buttons
    old_reset_btns = '''<div class="flex justify-end gap-3">
            <button id="cancelResetBtn" class="px-5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 font-semibold text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors">Cancelar</button>
            <button id="confirmResetBtn" class="px-6 py-2.5 rounded-xl bg-amber-500 text-white font-bold hover:bg-amber-600 hover:shadow-lg hover:shadow-amber-500/25 hover:-translate-y-0.5 transition-all flex items-center gap-2">
                <i class="fas fa-exchange-alt"></i>
                <span>Confirmar Reseteo</span>
            </button>
        </div>'''
    
    new_reset_btns = '''<div class="flex justify-end gap-3">
            {{ btn.secondary_btn('cancelResetBtn', 'Cancelar') }}
            {{ btn.primary_btn('confirmResetBtn', 'Confirmar Reseteo', 'fas fa-exchange-alt', 'bg-amber-500 hover:bg-amber-600 hover:shadow-amber-500/25') }}
        </div>'''
        
    # Create User Buttons
    old_create_btns = '''<div class="flex justify-end gap-3">
              <button data-action="close-create" class="px-5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 font-semibold text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors">Cancelar</button>
              <button id="create-user" class="px-6 py-2.5 rounded-xl bg-primary text-white font-bold hover:shadow-lg hover:-translate-y-0.5 transition-all flex items-center gap-2">
                  <i class="fas fa-save"></i>
                  Crear Usuario
              </button>
          </div>'''
          
    new_create_btns = '''<div class="flex justify-end gap-3">
              {{ btn.secondary_btn('', 'Cancelar', '', '', 'close-create') }}
              {{ btn.primary_btn('create-user', 'Crear Usuario', 'fas fa-save') }}
          </div>'''
          
    # Edit User Buttons
    old_edit_btns = '''<div class="flex-none p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-slate-900 z-10 flex justify-end gap-3">
            <button type="button" data-action="close-edit-modal" class="px-5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 font-semibold text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors">Cancelar</button>
            <button type="submit" class="px-6 py-2.5 rounded-xl bg-primary text-white font-bold hover:shadow-lg hover:-translate-y-0.5 transition-all flex items-center gap-2">
                <i class="fas fa-save"></i> Guardar Cambios
            </button>
        </div>'''
        
    new_edit_btns = '''<div class="flex-none p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-slate-900 z-10 flex justify-end gap-3">
            {{ btn.secondary_btn('', 'Cancelar', '', '', 'close-edit-modal') }}
            {{ btn.primary_btn('', 'Guardar Cambios', 'fas fa-save') }}
        </div>'''

    content = content.replace(old_reset_btns, new_reset_btns)
    content = content.replace(old_create_btns, new_create_btns)
    content = content.replace(old_edit_btns, new_edit_btns)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Success!")

process('app/templates/admin/users.html')
