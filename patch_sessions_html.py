import re

with open('edysync/src/app/features/admin/pages/sessions/sessions.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

upload_block = """    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>
      <select [(ngModel)]="editForm.status" class="w-full rounded-lg border-gray-300 focus:ring-primary focus:border-primary text-sm mb-4">
        <option value="scheduled">Programada</option>
        <option value="completed">Completada</option>
        <option value="cancelled">Cancelada</option>
      </select>
    </div>

    <!-- DOCUMENT UPLOAD SECTION -->
    <div class="mt-6 border-t pt-4">
      <label class="block text-sm font-medium text-gray-700 mb-2">Documento de Programación (.docx)</label>
      
      <!-- Existing Program state -->
      <div *ngIf="auditState" class="mt-2 p-3 rounded-lg text-sm flex items-start gap-2 bg-green-50 text-green-700 border border-green-200">
        <span class="material-symbols-outlined mt-0.5" style="font-family: 'Material Symbols Outlined'">check_circle</span>
        <div class="flex-1">
          <strong>Programación ya subida ✓</strong>
          <p class="text-xs mt-1 opacity-75">{{ auditState.planned_text_preview || 'Documento adjunto exitosamente' }}</p>
        </div>
        <button (click)="deleteProgram()" class="ml-2 text-red-500 hover:text-red-700 hover:bg-red-50 p-1.5 rounded-lg transition-all" title="Eliminar programación">
          <span class="material-symbols-outlined text-[20px]" style="font-family: 'Material Symbols Outlined'">delete</span>
        </button>
      </div>

      <!-- Upload Trigger (Empty state) -->
      <div *ngIf="!auditState" class="mt-2">
        <label for="programFileInput" class="block w-full border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-primary hover:bg-green-50 transition-all cursor-pointer">
            <span class="material-symbols-outlined text-gray-400 mb-2 text-[36px]" style="font-family: 'Material Symbols Outlined'">cloud_upload</span>
            <p class="text-sm text-gray-600">Haz clic para subir el documento Word</p>
            <p class="text-xs text-gray-400 mt-1">Solo archivos .docx</p>
        </label>
        <input type="file" id="programFileInput" class="hidden" accept=".docx" (change)="onFileSelected($event)">
      </div>

      <!-- Uploading / Messages -->
      <div *ngIf="programUploading" class="mt-2 p-2 rounded-lg text-sm flex items-center gap-2 bg-blue-50 text-blue-700">
          <span class="material-symbols-outlined fa-spin" style="font-family: 'Material Symbols Outlined'">refresh</span> Procesando documento Word...
      </div>
      <div *ngIf="programError" class="mt-2 p-2 rounded-lg text-sm flex items-center gap-2 bg-red-50 text-red-700">
          <span class="material-symbols-outlined" style="font-family: 'Material Symbols Outlined'">error</span> {{ programError }}
      </div>
      <div *ngIf="programSuccessMessage" class="mt-2 p-2 rounded-lg text-sm flex items-center gap-2 bg-green-50 text-green-700">
          <span class="material-symbols-outlined" style="font-family: 'Material Symbols Outlined'">check_circle</span> {{ programSuccessMessage }}
      </div>
    </div>
"""

# Replace the Status block and wrap it with the new blocks
old_status_block_pattern = r'    <div>\s*<label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>\s*<select \[\(ngModel\)\]="editForm\.status"[^>]+>\s*<option value="scheduled">Programada</option>\s*<option value="completed">Completada</option>\s*<option value="cancelled">Cancelada</option>\s*</select>\s*</div>'

html_content = re.sub(old_status_block_pattern, upload_block, html_content)

with open('edysync/src/app/features/admin/pages/sessions/sessions.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
