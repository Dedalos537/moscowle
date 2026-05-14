import re

with open('edysync/src/app/features/admin/pages/sessions/sessions.ts', 'r', encoding='utf-8') as f:
    ts_content = f.read()

new_props = """  submitting = false;

  // --- PROGRAM UPLOADS / AUDITS ---
  auditState: any = null;
  programUploading = false;
  programError: string | null = null;
  programSuccessMessage: string | null = null;
"""
ts_content = re.sub(r'  submitting = false;', new_props, ts_content)

handle_event_click_replacement = """  private handleEventClick(arg: EventClickArg) {
    const ext = arg.event.extendedProps;
    this.editForm = {
      id: parseInt(arg.event.id),
      title: arg.event.title,
      date: arg.event.start?.toISOString().split('T')[0] || '',
      start_time: arg.event.start?.toTimeString().substring(0, 5) || '',
      end_time: arg.event.end?.toTimeString().substring(0, 5) || '',
      status: (ext['status'] as string) || 'scheduled',
      therapist: (ext['therapist'] as string) || '',
      patient: (ext['patient'] as string) || '',
    };
    
    // Reset states
    this.auditState = null;
    this.programError = null;
    this.programSuccessMessage = null;
    
    // Load audit state
    this.adminService.getSessionAudit(this.editForm.id).subscribe({
      next: (data: any) => {
        if (data && data.success && data.exists && data.audit.has_program) {
            this.auditState = data.audit;
        }
      },
      error: () => {}
    });

    this.showEditModal = true;
  }"""
ts_content = re.sub(r'  private handleEventClick.*?this\.showEditModal = true;\n  }', handle_event_click_replacement, ts_content, flags=re.DOTALL)

close_edit_replacement = """  closeEditModal() {
    this.showEditModal = false;
    this.auditState = null;
    this.programError = null;
    this.programSuccessMessage = null;
  }"""
ts_content = re.sub(r'  closeEditModal\(\) \{.*?\}', close_edit_replacement, ts_content, flags=re.DOTALL)

upload_methods = """  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file && this.editForm.id) {
      this.programUploading = true;
      this.programError = null;
      this.programSuccessMessage = null;
      
      this.adminService.uploadSessionProgram(this.editForm.id, file).subscribe({
        next: (res: any) => {
          this.programUploading = false;
          if (res.success) {
            this.programSuccessMessage = 'Programación subida correctamente.';
            this.auditState = { has_program: true, planned_text_preview: res.planned_text_preview };
          } else {
            this.programError = res.error || 'Error desconocido';
          }
          event.target.value = null;
        },
        error: (err) => {
          this.programUploading = false;
          this.programError = 'Error de conexión al subir.';
          event.target.value = null;
        }
      });
    }
  }

  deleteProgram() {
    if (confirm('¿Eliminar la programación de esta sesión?')) {
      this.adminService.deleteSessionProgram(this.editForm.id).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.auditState = null;
            this.programSuccessMessage = 'Programación eliminada.';
          } else {
            this.programError = res.error || 'Error al eliminar';
          }
        },
        error: () => {
          this.programError = 'Error de conexión al eliminar.';
        }
      });
    }
  }"""

# Insert before end of class
ts_content = re.sub(r'}\s*$', upload_methods + '\n}', ts_content)

with open('edysync/src/app/features/admin/pages/sessions/sessions.ts', 'w', encoding='utf-8') as f:
    f.write(ts_content)

