export interface McpToolMeta {
  label: string;
  icon?: string;
}

export const MCP_TOOL_META: Record<string, McpToolMeta> = {
  register_payment: { label: 'Registrar pago', icon: 'dollar-sign' },
  cancel_payment: { label: 'Eliminar pago', icon: 'trash' },
  edit_payment: { label: 'Modificar pago', icon: 'edit' },
  send_payment_reminder: { label: 'Enviar recordatorio de pago', icon: 'envelope' },
  pay_installment: { label: 'Registrar cuota', icon: 'dollar-sign' },
  create_session: { label: 'Crear sesión', icon: 'calendar-plus' },
  update_session: { label: 'Actualizar sesión', icon: 'edit' },
  cancel_session: { label: 'Cancelar sesión', icon: 'times' },
  complete_session: { label: 'Completar sesión', icon: 'check' },
  batch_create_sessions: { label: 'Crear sesiones en lote', icon: 'calendar-plus' },
  create_user: { label: 'Crear usuario', icon: 'user-plus' },
  update_user: { label: 'Actualizar usuario', icon: 'edit' },
  delete_user: { label: 'Eliminar usuario', icon: 'trash' },
  toggle_user_status: { label: 'Cambiar estado de usuario', icon: 'toggle-on' },
  assign_therapist: { label: 'Asignar terapeuta', icon: 'user-doctor' },
  create_incident: { label: 'Crear incidencia', icon: 'exclamation-triangle' },
  update_incident_status: { label: 'Actualizar incidencia', icon: 'edit' },
  assign_incident: { label: 'Asignar incidencia', icon: 'user' },
  create_patient_group: { label: 'Crear grupo de pacientes', icon: 'users' },
  create_expense: { label: 'Registrar gasto', icon: 'wallet' },
  send_direct_message: { label: 'Enviar mensaje', icon: 'paper-plane' },
  broadcast_message: { label: 'Enviar mensaje masivo', icon: 'envelope' },
  mark_notifications_read: { label: 'Marcar notificaciones como leídas', icon: 'check' },
  generate_weekly_report: { label: 'Generar reporte semanal', icon: 'file-alt' },
  create_contract: { label: 'Crear contrato', icon: 'file-contract' },
  update_contract: { label: 'Actualizar contrato', icon: 'edit' },
  cancel_contract: { label: 'Cancelar contrato', icon: 'times' },
  reactivate_contract: { label: 'Reactivar contrato', icon: 'check' },
  update_patient: { label: 'Actualizar paciente', icon: 'edit' },
  update_patient_details: { label: 'Actualizar paciente', icon: 'edit' },
};

export const MCP_PARAM_LABELS: Record<string, string> = {
  patient_id: 'Paciente',
  user_id: 'Usuario',
  therapist_id: 'Terapeuta',
  payment_id: 'Pago',
  session_id: 'Sesión',
  incident_id: 'Incidencia',
  contract_id: 'Contrato',
  amount: 'Monto (S/)',
  method: 'Método de pago',
  reference: 'Referencia / operación',
  payment_date: 'Fecha de pago',
  day: 'Fecha de sesión',
  time: 'Hora',
  hour: 'Hora',
  duration_minutes: 'Duración (min)',
  status: 'Estado',
  new_status: 'Nuevo estado',
  notes: 'Notas',
  titulo: 'Título',
  title: 'Título',
  descripcion: 'Descripción',
  description: 'Descripción',
  categoria: 'Categoría',
  impacto: 'Impacto',
  urgencia: 'Urgencia',
  username: 'Nombre',
  email: 'Email',
  password: 'Contraseña',
  role: 'Rol',
  sede_id: 'Sede',
  phone: 'Teléfono',
  is_active: 'Activo',
  subject: 'Asunto',
  body: 'Mensaje',
  target: 'Destinatarios',
  name: 'Nombre',
  group_name: 'Nombre del grupo',
  start: 'Inicio',
  end: 'Fin',
  days: 'Días',
  start_date: 'Fecha inicio',
  end_date: 'Fecha fin',
  weekly_frequency: 'Frecuencia semanal',
  months: 'Meses',
  installment: 'Cuota',
  assigned_to: 'Asignado a',
  comment: 'Comentario',
  amount_paid: 'Monto pagado',
  total: 'Total',
  category: 'Categoría',
  date: 'Fecha',
  date_YYYY_MM_DD: 'Fecha (YYYY-MM-DD)',
};

export function getToolLabel(name: string): string {
  return MCP_TOOL_META[name]?.label || name;
}

export function getToolIcon(name: string): string {
  return MCP_TOOL_META[name]?.icon || 'wrench';
}

export function getParamLabel(key: string): string {
  return MCP_PARAM_LABELS[key] || key;
}
